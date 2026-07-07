"""E0 substrate — properties P1, P3–P6 + the energy pathways (IMPLEMENTATION_PLAN.md
Steps 1–4). Conservation, determinism, grid-freeness, vectorization, bounded
population, harvest/locality, move+death, reproduction+heredity.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from eco.config import load_eco_config
from eco.engine import EcoEngine, run
from eco.policies import frozen, hand_forager
from eco.resource import harvest
from eco.state import EcoState, init_state, source_at

_CFG = Path(__file__).resolve().parent.parent / "configs" / "eco.yaml"


def _cfg(**over):
    cfg = load_eco_config(_CFG)
    return cfg if not over else __import__("dataclasses").replace(cfg, **over)


def _state(x, e, g, cfg, mu=None, pool=10.0, seed=0):
    return EcoState(
        x=np.asarray(x, float), e=np.asarray(e, float), g=np.asarray(g, float),
        mu=source_at(0, cfg) if mu is None else np.asarray(mu, float),
        pool=pool, dissipated=0.0, t=0, rng=np.random.Generator(np.random.PCG64(seed)),
    )


# ---- P1 conservation ---------------------------------------------------------

def test_conservation_longrun() -> None:
    """P1: the ledger closes to machine precision over a long run with births/deaths."""
    res = run(_cfg(), ticks=3000, policy=hand_forager)
    assert res["max_abs_residual"] < 1e-9, res["max_abs_residual"]
    assert res["final_n"] > 0  # default config is viable (sanity)


def test_harvest_conserves() -> None:
    """P1: harvested energy splits exactly into credited (η) + dissipated (1-η)."""
    cfg = _cfg()
    x = np.array([[0.0, 0.0, 0.0, 0.0], [0.3, 0.1, 0.0, 0.0]])
    delta_e, drawn, diss = harvest(x, mu=np.zeros(4), pool=5.0,
                                   gate=np.ones(2), cfg=cfg)
    assert abs(drawn - (float(delta_e.sum()) + diss)) < 1e-12


def test_harvest_is_local() -> None:
    """Near the source harvests a lot; far away harvests ≈0 (the driver of P8)."""
    cfg = _cfg()
    x = np.array([[0.0, 0.0, 0.0, 0.0], [8.0, 0.0, 0.0, 0.0]])
    delta_e, _, _ = harvest(x, mu=np.zeros(4), pool=100.0, gate=np.ones(2), cfg=cfg)
    assert delta_e[0] > 0.1
    assert delta_e[1] < 1e-6


def test_harvest_depletes_pool() -> None:
    """Competition: total uptake can never exceed the available pool."""
    cfg = _cfg()
    x = np.zeros((50, cfg.d))  # 50 tokens all on the source
    _, drawn, _ = harvest(x, mu=np.zeros(cfg.d), pool=1.0, gate=np.ones(50), cfg=cfg)
    assert drawn <= 1.0 + 1e-12


# ---- P4 determinism ----------------------------------------------------------

def test_determinism() -> None:
    """P4: same seed + config ⇒ identical state-history hash (through births/deaths)."""
    a, b = EcoEngine(_cfg()), EcoEngine(_cfg())
    for _ in range(400):
        a.tick(); b.tick()
    assert a.state.state_hash() == b.state.state_hash()
    assert a.state.n == b.state.n


# ---- P3 grid-free ------------------------------------------------------------

def test_grid_free() -> None:
    """P3: positions are continuous floats in R^d; no lattice/cell vocabulary."""
    st = init_state(_cfg())
    assert st.x.dtype == np.float64 and st.x.ndim == 2
    import eco
    src = ""
    for mod in ("config", "state", "resource", "engine", "policies"):
        src += Path(eco.__file__).parent.joinpath(f"{mod}.py").read_text().lower()
    # code patterns of a lattice substrate (not prose — the docs say "no lattice")
    for banned in ("np.meshgrid", "grid[", "cell_index", "np.indices"):
        assert banned not in src, banned


# ---- P5 vectorized -----------------------------------------------------------

def test_vectorized_no_per_token_loop() -> None:
    """P5: the per-tick paths use array ops, not per-token Python loops."""
    for fn in (EcoEngine.tick, EcoEngine._reproduce, harvest, hand_forager):
        assert "for " not in inspect.getsource(fn), fn.__name__


# ---- P6 bounded population ---------------------------------------------------

def test_population_bounded() -> None:
    """P6: N never exceeds n_max across a growth run."""
    res = run(_cfg(), ticks=1500, policy=hand_forager)
    assert max(res["pop"]) <= _cfg().n_max


def test_reproduction_refused_at_cap() -> None:
    """P6: at the cap, reproduction is refused (energy stays with parent), no overflow."""
    cfg = _cfg(n_max=10)
    n = 10
    st = _state(np.zeros((n, cfg.d)), np.full(n, 5.0), np.zeros((n, cfg.d_g)), cfg)
    eng = EcoEngine(cfg, policy=frozen, state=st)
    before = float(st.e.sum()) + st.pool + st.dissipated
    eng.tick()
    assert st.n == 10  # no room → no births
    after = float(st.e.sum()) + st.pool + st.dissipated
    assert abs((after - before) - cfg.inject) < 1e-9  # still conserves


# ---- move + metabolism + death ----------------------------------------------

def test_move_and_death_conserve() -> None:
    """A far, low-energy token cannot afford metabolism → dies; ledger closes."""
    cfg = _cfg()
    # one token far from the source (no harvest), energy below c_base → must die
    st = _state([[9.0, 0.0, 0.0, 0.0]], [0.5 * cfg.c_base], [[0.0, 0.0]], cfg,
                mu=source_at(0, cfg), pool=0.0)
    eng = EcoEngine(cfg, policy=frozen, state=st)
    before = float(st.e.sum()) + st.pool + st.dissipated
    eng.tick()
    assert st.n == 0  # died
    after = float(st.e.sum()) + st.pool + st.dissipated
    assert abs((after - before) - cfg.inject) < 1e-9


def test_move_costs_energy() -> None:
    """Motion debits c_move·||dx||² and books it to dissipation (ledger closes)."""
    cfg = _cfg()
    st = _state([[3.0, 0.0, 0.0, 0.0]], [10.0], [[0.0, 0.0]], cfg, pool=0.0)
    eng = EcoEngine(cfg, policy=hand_forager, state=st)
    e0 = float(st.e[0])
    before = float(st.e.sum()) + st.pool + st.dissipated
    eng.tick()
    assert st.e[0] < e0  # paid to move (and metabolize)
    after = float(st.e.sum()) + st.pool + st.dissipated
    assert abs((after - before) - cfg.inject) < 1e-9


# ---- reproduction + heredity -------------------------------------------------

def test_reproduction_conserves_and_mutates() -> None:
    """Split conserves energy; child gene = parent + mutation; child near parent."""
    cfg = _cfg()
    st = _state([[0.0, 0.0, 0.0, 0.0]], [4.0], [[1.0, -2.0]], cfg, pool=0.0)
    eng = EcoEngine(cfg, policy=frozen, state=st)
    before = float(st.e.sum()) + st.pool + st.dissipated
    eng.tick()
    assert st.n == 2  # split
    after = float(st.e.sum()) + st.pool + st.dissipated
    assert abs((after - before) - cfg.inject) < 1e-9
    parent_g = np.array([1.0, -2.0])
    child_g = st.g[1]
    assert not np.allclose(child_g, parent_g)             # mutated
    assert np.linalg.norm(child_g - parent_g) < 0.5       # but near the parent
    assert np.linalg.norm(st.x[1] - st.x[0]) < 0.5        # offspring placed nearby


def test_gene_mutation_deterministic() -> None:
    """Heredity is reproducible: same seed → same child gene."""
    cfg = _cfg()
    def child():
        st = _state([[0.0, 0.0, 0.0, 0.0]], [4.0], [[1.0, -2.0]], cfg, pool=0.0, seed=7)
        EcoEngine(cfg, policy=frozen, state=st).tick()
        return st.g[1].copy()
    assert np.array_equal(child(), child())
