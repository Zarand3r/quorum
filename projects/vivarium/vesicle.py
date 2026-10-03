"""The active 2-D molecular dish, served through the production transformer path.

Each bead is a token; each branched lipid has a head and four tail beads. The topology, force
law and step engine are shared with the research harness, not reimplemented for the viewer.

The default and both restart controls start dispersed. `--vesicle-start formed` loads
seed 509 at step 500,000. Only positions are saved, so loading is not an exact continuation of the
historical trajectory: velocities and thermostat RNG are freshly initialized. Source evidence is
reported separately from the periodically evaluated current `vesicle_gate` verdict.

Current scope, results and architectural limitations: SUMMARY.md and docs/ROADMAP.md. The older
pack/polar engines are archived and are not the simulation this module serves.
"""

from __future__ import annotations

import pathlib
import threading

import numpy as np

import _mixture
import vesicle_gate
from chemistry import AMPHIPHILE
from field import Field, HEAD, TAIL, WATER, default_chi

# The production numbers. Changing one silently is how the last viewer stopped representing the runs,
# so they live here as named constants and the chemistry is asserted at construction.
N_LIP = 160
L_BOX = 65.0
KT = 0.45
PHI = 0.55
DT = 8e-3                      # the validated timestep (same energy + ensemble as overdamped)
GATE_INTERVAL = 5_000          # observational only; ~10 s at full hosted throughput
C_D = _mixture.C_D             # bead-count-per-unit-volume table, shared with the research path

_HERE = pathlib.Path(__file__).resolve().parent
# Tracked positional evidence of the seed-509 emergent vesicle. Its source seed and step are
# read from the file, rather than inferred from the seed chosen for fresh thermal velocities.
FORMED_STATE = _HERE / "docs" / "controls" / "emergent_vesicle_sd509_s500000.npz"
DEFAULT_SEED = 509

# viewer.html species codes: 5 = lipid head (blue), 6 = lipid tail (orange), 0 = solvent (dim).
# field.py uses HEAD=0, TAIL=1, WATER=2, and 0 collides across the two schemes, so the mapping is
# explicit rather than an offset.
_VIEWER_SPECIES = {HEAD: 5, TAIL: 6, WATER: 0}


def production_chi(chi_ht=None, chi_ww=None, chi_hh=None, chi_tw=None):
    """The chi table the vesicle runs use, with the four swept terms overridable.

    Built by mutating `default_chi()` rather than by setting VIVARIUM_CHI_* in the environment: the
    env is process-global, and a live viewer changing a knob would silently retune every other engine
    in the process.
    """
    chi = default_chi()
    chi[HEAD, TAIL] = chi[TAIL, HEAD] = AMPHIPHILE["ht"] if chi_ht is None else float(chi_ht)
    chi[WATER, WATER] = AMPHIPHILE["ww"] if chi_ww is None else float(chi_ww)
    if chi_hh is not None:
        chi[HEAD, HEAD] = float(chi_hh)
    if chi_tw is not None:
        chi[TAIL, WATER] = chi[WATER, TAIL] = float(chi_tw)
    return chi


def assert_production_chemistry(chi) -> None:
    """Fail loudly if the amphiphile terms are not the ones every result was measured under."""
    bad = []
    if chi[HEAD, TAIL] != AMPHIPHILE["ht"]:
        bad.append(f"chi_HT {chi[HEAD, TAIL]:+.3f} != {AMPHIPHILE['ht']:+.3f}")
    if chi[WATER, WATER] != AMPHIPHILE["ww"]:
        bad.append(f"chi_WW {chi[WATER, WATER]:+.3f} != {AMPHIPHILE['ww']:+.3f}")
    if bad:
        raise ValueError("not the production chemistry: " + ", ".join(bad))


class VesicleEngine:
    """The 2-D production lipid dish, stepped through the transformer path.

    Exposes the surface `server.Sim` needs: `.X`, `.t`, `.L`, `.step()`, `.snapshot()`.
    """

    def __init__(self, seed=DEFAULT_SEED, start="dispersed", n_lip=N_LIP, L=L_BOX, kT=KT, phi=PHI,
                 chi_ht=None, chi_ww=None, chi_hh=None, chi_tw=None, engine="transformer"):
        self.seed = int(seed)
        self.start = start
        self.n_lip, self.L, self.phi = int(n_lip), float(L), float(phi)
        self.kT = float(kT)
        self.engine_kind = engine
        self._chi_knobs = dict(chi_ht=chi_ht, chi_ww=chi_ww, chi_hh=chi_hh, chi_tw=chi_tw)
        self.t = 0
        self._build()

    # ---- construction ----

    def _build(self) -> None:
        d = 2
        # All four-tail lipids (frac_short = 0), branched, matching fs0.0 in the production tag.
        n_short, n_long = 0, self.n_lip
        lip_beads = n_short * 3 + n_long * 5
        n_water = 0 if self.phi <= 0.0 else (
            int(round(self.phi * self.L ** d / C_D[d] * (2 ** d))) - lip_beads)
        if n_water < 0:
            raise ValueError(f"L={self.L} too small for {self.n_lip} lipids at phi={self.phi}")

        X, species, bonds, mols, wi, chains = _mixture.build(
            n_short, n_long, n_water, self.L, d, plant="random", branched=True, seed=self.seed)

        self.gate = None
        self.source_gate = None
        if self.start == "formed":
            self._formed_species, self._formed_mols = species, mols
            X = self._load_formed(X)
        elif self.start != "dispersed":
            raise ValueError(f"start must be 'formed' or 'dispersed'; got {self.start!r}")

        self.species, self.mols, self.chains = species, mols, chains
        self.bonds = np.asarray(bonds, dtype=np.int64).reshape(-1, 2)
        chi = production_chi(**self._chi_knobs)
        if all(v is None for v in self._chi_knobs.values()):
            assert_production_chemistry(chi)
        self.chi = chi
        self.field = Field(species, bonds, self.L, chi=chi)
        self.X = np.ascontiguousarray(X, dtype=np.float64)
        # noise_seed mirrors the research call site (`1 + seed` on the transformer branch).
        self.ig = _mixture.make_step_engine(self.field, self.X, self.kT, DT, 1 + self.seed,
                                            engine=self.engine_kind)
        self._gate_pending = False
        # The gate is observational and costs far more than construction. The first snapshot starts
        # it from copied geometry in the background; restart must not hold the simulation/UI lock for
        # a classification that has no effect on dynamics.

    def _load_formed(self, X):
        """Load the emergent vesicle. Bead counts must match, or the shell is not this system."""
        if not FORMED_STATE.exists():
            raise FileNotFoundError(
                f"{FORMED_STATE} is missing. Restore the tracked state or use start='dispersed'.")
        with np.load(FORMED_STATE, allow_pickle=True) as z:
            saved = z["X"].copy()
            saved_L = float(z["L"])
            saved_species = z["species"].copy()
            mols = np.asarray(z["mols"], dtype=np.int64)
            self.formed_steps = int(z["steps"])
            self.source_seed = int(z["seed"])
        if saved_L != self.L or not np.array_equal(saved_species, self._formed_species):
            raise ValueError("saved vesicle box or species differ from this system")
        if saved.shape != X.shape:
            raise ValueError(
                f"state has {saved.shape} beads, this dish builds {X.shape}. The saved shell belongs "
                "to a different box or composition; transplanting it would show a system nothing was "
                "measured on.")
        if not np.array_equal(mols, np.asarray(self._formed_mols, dtype=np.int64)):
            raise ValueError("saved vesicle molecule topology differs from this system")
        ok, value, _ = vesicle_gate.vesicle(saved, saved_species, mols, saved_L)
        self.source_gate = {"source": FORMED_STATE.name, "steps": self.formed_steps,
                            "seed": self.source_seed, "criterion": "vesicle_gate",
                            "vesicle": bool(ok), "score": float(value)}
        return saved.copy()

    # ---- dynamics ----

    def new_run(self, seed):
        """Restart from dispersed molecules, preserving the current physical parameters."""
        return type(self)(seed=seed, start="dispersed", n_lip=self.n_lip, L=self.L,
                          kT=self.kT, phi=self.phi, engine=self.engine_kind,
                          **self._chi_knobs)

    def step(self) -> None:
        self.X = self.ig.step(self.X)
        self.t += 1

    def rebuild(self) -> None:
        """Change the law at the current positions, retaining velocity and thermostat RNG."""
        self.chi = production_chi(**self._chi_knobs)
        self.field = Field(self.species, self.bonds, self.L, chi=self.chi)
        if self.engine_kind == "transformer":
            from transformer import VivariumTransformer
            self.ig.tf = VivariumTransformer(self.field)
            if self.ig.v is not None:
                self.ig.F = self.ig.tf.attention(self.X)
        else:
            self.ig.f = self.field
            if self.ig.v is not None:
                self.ig._F = self.field.forces(self.X)
        self.gate = None

    # ---- knobs ----

    def _chi_knob(self, name):
        """(getter, setter) for one chi term. Setting rebuilds: the transformer factors Wq/Wk out of
        chi at construction, so mutating the matrix in place would desync the heads from the field."""
        def get():
            return float(self._chi_knobs[name]) if self._chi_knobs[name] is not None else {
                "chi_ht": AMPHIPHILE["ht"], "chi_ww": AMPHIPHILE["ww"],
                "chi_hh": float(default_chi()[HEAD, HEAD]),
                "chi_tw": float(default_chi()[TAIL, WATER]),
            }[name]

        def setr(v):
            self._chi_knobs[name] = float(v)
            self.rebuild()

        return get, setr

    def kT_knob(self):
        """Temperature is live: the thermostat reads kT every step, so no rebuild is needed."""
        def get():
            return float(self.kT)

        def setr(v):
            self.kT = max(1e-4, float(v))
            self.ig.kT = self.kT

        return get, setr

    def pseudo_knobs(self) -> dict:
        return {
            "chi_HT": self._chi_knob("chi_ht"),
            "chi_TW": self._chi_knob("chi_tw"),
            "chi_HH": self._chi_knob("chi_hh"),
            "chi_WW": self._chi_knob("chi_ww"),
            "kT": self.kT_knob(),
        }

    # ---- observation ----

    def _evaluate_gate(self, X, tick) -> None:
        """Evaluate copied geometry, so periodic classification never stalls dynamics or streaming."""
        try:
            ok, value, _ = vesicle_gate.vesicle(X, self.species, self.mols, self.L)
            # A slower, older evaluation must not overwrite a newer verdict.
            if self.gate is None or tick >= self.gate["tick"]:
                self.gate = {"criterion": "vesicle_gate", "vesicle": bool(ok),
                             "score": float(value), "tick": tick}
        finally:
            self._gate_pending = False

    def snapshot(self, with_edges=True) -> dict:
        if self.gate is None or self.t - self.gate["tick"] >= GATE_INTERVAL:
            if not self._gate_pending:
                self._gate_pending = True
                threading.Thread(target=self._evaluate_gate, args=(self.X.copy(), self.t),
                                 daemon=True).start()
        pr = np.round(self.X, 3).tolist()
        # Every token needs a contour for the viewer's paint path; a flat one draws a true circle at
        # the species radius, which is what a bead is.
        flat = [0.0, 0.0]
        tokens = [{"x": pr[i][0], "y": pr[i][1], "c": flat} for i in range(len(pr))]
        return {
            "status": "running",
            "tick": self.t,
            "n": len(pr),
            "tokens": tokens,
            "species": [_VIEWER_SPECIES[int(s)] for s in self.species],
            "bonds": [[int(a), int(b)] for a, b in self.bonds],
            "pos_dim": 2,
            "pos_bound": self.L / 2.0,   # integrate.py wraps to [-L/2, L/2)
            "edges": None,
            "length": float(self.L),
            "gate": self.gate,      # current geometry, with its evaluation tick
            "source_gate": self.source_gate,
            "start": self.start,
            "mode": "vesicle",
            "sim_time": self.t * DT,
            "radii": (0.5 * self.field.sigma_species[self.species]).tolist(),
            "physics": {"dt": DT, "k_bond": self.field.k_bond,
                        "bend_frac": self.field.bend_frac, "bend_r0": self.field.bend_r0,
                        "k_theta": self.field.k_theta, "rc": self.field.rc,
                        "core_height": self.field.core_height, "electrostatics": False,
                        "live_token_mlp": False},
        }
