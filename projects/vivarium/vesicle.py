"""The dish that actually emerges vesicles, served live through the transformer path.

WHY THIS EXISTS

The hosted viewer served `polar_pack` under `--lipid2d`: the micelle configuration from `fig2d.py`
(63 lipids, 250 water, N = 439). Every vesicle result in `docs/PAPER.md` came from a different stack
entirely -- `_mixture.build` for the topology, `field.Field` for the energy, and `_mixture`'s
transformer engine for the step -- at 160 lipids in L = 65 (2,959 beads). `server.py` did not import
one of those modules, so the page could not have shown the vesicle system no matter which flag was
passed. This module is the missing path.

WHAT IT RUNS

The production configuration, taken from the state tag the results were saved under:

    mix2d_random_N160_L65_exp_kT0.45_fs0.0_ht-0.25_ww0.50

so `n_lip = 160`, `frac_short = 0` (all four-tail lipids, branched), `L = 65`, `kT = 0.45`,
`phi = 0.55` (explicit water), `chi_HT = -0.25` and `chi_WW = 0.50`. Those last two are NOT the
`field.default_chi` defaults of +0.20 and +1.00 -- they are `chemistry.AMPHIPHILE`, and a dish run at
the bare defaults is not an amphiphile at all (at `chi_HT = 0.20` a head is indifferent between a head
and a tail neighbour, and the ordered bilayer is not even a local minimum). `assert_production_chemistry`
pins this so the viewer cannot quietly drift off the validated system the way the last one did.

The step is `_mixture.make_step_engine(..., engine="transformer")` -- the same call the research runs
make, not a copy of it.

WHAT IT DOES NOT CLAIM

Formation is rare and slow: 2 of 18 fresh seeds, over 6e5 to 1e6 steps. At ~5 ms/step a dispersed
start is hours of wall clock and will usually show nothing. That is the state of the science, not a
defect in the viewer, so `dispersed` is the DEFAULT.

`start="formed"` loads the best surviving saved aggregate and reports the gate's verdict on it
verbatim in `snapshot()["gate"]`. It does NOT ship a certified vesicle, because none is available:
every saved 2-D production state was checked on 2026-08-27 and **not one passes `vesicle_call`**.

    docs/controls/stable_vesicle_sd9302.npz   n_enclosed 1 at bead 1.0-3.0; lumen ratio 0.070 (< 0.10)
    docs/controls/snap25_sd8801.npz           lumen ratio 0.021
    docs/controls/snap_sd8203.npz             lumen ratio 0.022
    docs/states_protected/former_sd45015_*    n_enclosed [2, 2, 2, 0] -- unstable across dilation
    docs/states_protected/former_sd45007_*    n_enclosed [0, 0, 0, 0] -- no lumen at all

The last one is worth its own line. Its name says step 960,000 but the file reports `steps` =
1,600,000: a relaunch overwrote the protected state in place, which is exactly the `_save_state`
hazard PAPER.md section 16 documents ("this name carries no STEP and no RUN identity"). The vesicle
that existed at 960k is gone from disk.

Two caveats on those verdicts, flagged and NOT worked around here. `vesicle_call` sizes the expected
lumen from `len(mols)` -- the whole system's 160 lipids -- and its calibration cases are all
aggregates that ARE the whole system. sd9302's cluster is 84 of 160, so the clause is being applied
outside the regime it was calibrated on, and rescaling by (84/160)^2 would put it at 0.25, well
inside. Whether that rescaling is legitimate is a question for the gate's author, not for a viewer.
Loading a state also cannot verify the chemistry it was produced under: `chemistry.chemistry_of`
reads VIVARIUM_* tags out of the filename, and none of these filenames carries one.
"""

from __future__ import annotations

import pathlib

import numpy as np

import _mixture
from _lumen_field import vesicle_call
from chemistry import AMPHIPHILE
from field import Field, HEAD, TAIL, WATER, default_chi

# The production numbers. Changing one silently is how the last viewer stopped representing the runs,
# so they live here as named constants and the chemistry is asserted at construction.
N_LIP = 160
L_BOX = 65.0
KT = 0.45
PHI = 0.55
DT = 8e-3                      # the validated timestep (same energy + ensemble as overdamped)
C_D = _mixture.C_D             # bead-count-per-unit-volume table, shared with the research path

_HERE = pathlib.Path(__file__).resolve().parent
FORMED_STATE = _HERE / "docs" / "controls" / "stable_vesicle_sd9302.npz"

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

    def __init__(self, seed=0, start="dispersed", n_lip=N_LIP, L=L_BOX, kT=KT, phi=PHI,
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
        if self.start == "formed":
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

    def _load_formed(self, X):
        """Load the emergent vesicle. Bead counts must match, or the shell is not this system."""
        if not FORMED_STATE.exists():
            raise FileNotFoundError(
                f"{FORMED_STATE} is missing -- it is gitignored run data, not source. "
                "Use start='dispersed', or restore docs/states_protected/.")
        z = np.load(FORMED_STATE, allow_pickle=True)
        saved = z["X"]
        if saved.shape != X.shape:
            raise ValueError(
                f"state has {saved.shape} beads, this dish builds {X.shape}. The saved shell belongs "
                "to a different box or composition; transplanting it would show a system nothing was "
                "measured on.")
        self.formed_steps = int(z["steps"])
        # Report the project's own verdict rather than asserting one. No saved 2-D production state
        # passes this gate (see the module docstring), so the honest thing a viewer can do is show
        # what the gate says instead of implying a vesicle.
        mols = np.array([np.asarray(m, dtype=np.int64) for m in z["mols"]], dtype=np.int64)
        ok, reason = vesicle_call(saved, mols, float(z["L"]))
        self.gate = {"source": FORMED_STATE.name, "steps": self.formed_steps,
                     "vesicle_call": bool(ok), "reason": str(reason),
                     "largest": int(_mixture.largest_cluster(saved, mols, float(z["L"]))),
                     "n_mol": int(len(mols))}
        return saved.copy()

    # ---- dynamics ----

    def step(self) -> None:
        self.X = self.ig.step(self.X)
        self.t += 1

    def rebuild(self) -> None:
        """Re-create field + engine after a chemistry change, keeping the tick count honest."""
        t = self.t
        self._build()
        self.t = t

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

    def snapshot(self, with_edges=True) -> dict:
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
            "gate": self.gate,      # None for a dispersed start; the verdict for a loaded state
            "start": self.start,
        }
