"""M0 — validate the aggregation metrics on hand-made fixtures, then measure the real engine.

The metric must correctly distinguish a GAS (fills the box) from a DROPLET (compact, box-
independent) BEFORE we trust it to judge the sim — the RD-over-claim lesson.
"""

from __future__ import annotations

import numpy as np

from metrics_pack import measure


def test_gas_vs_droplet_fixtures() -> None:
    # Torus-appropriate discriminators: OCCUPANCY (fills box?) + LARGEST-CLUSTER FRACTION
    # (one blob vs fragmented). Rg-on-a-torus is only meaningful for a formed droplet.
    L, radius = 12.0, 1.0
    rng = np.random.default_rng(0)

    gas = rng.uniform(-L / 2, L / 2, (64, 2))     # fills the box
    g = measure(gas, L, radius)
    drop = rng.normal(0, 0.8, (64, 2))            # compact cluster near origin
    d = measure(drop, L, radius)

    assert g["occupancy"] > 0.7, "gas should fill most of the box"
    assert d["occupancy"] < 0.3, "droplet should leave empty space"
    assert d["largest_frac"] > 0.9, "a droplet is (almost) one cluster"
    assert g["largest_frac"] < 0.5, "a gas fragments into many small clusters"
    assert d["occupancy"] < 0.5 * g["occupancy"], "at the same box, droplet leaves far more empty space"


def test_box_independence_is_the_discriminator() -> None:
    # THE decisive test for MATTER vs GAS: a droplet is box-INDEPENDENT (occupancy drops as the
    # box grows around the same compact blob); a gas stays ~full regardless of box.
    rng = np.random.default_rng(1)
    drop = rng.normal(0, 0.8, (64, 2))
    occ_1x = measure(drop, 12.0, 1.0)["occupancy"]
    occ_2x = measure(drop, 24.0, 1.0)["occupancy"]   # same droplet, 4× the area
    assert occ_2x < 0.5 * occ_1x, "a droplet's occupancy must drop as the box grows (compact, bounded)"
    # and it stays ONE cluster regardless of box — the signature of matter, not gas.
    assert measure(drop, 24.0, 1.0)["largest_frac"] > 0.9, "a droplet stays one cluster in a bigger box"


def test_measure_current_pack_engine() -> None:
    # Baseline reading of the real engine (not an assertion of success — just that it runs and
    # produces finite metrics we can track as M1 adds cohesion).
    from config import DEFAULTS, VivariumConfig
    from pack import PackEngine

    e = PackEngine(VivariumConfig(**DEFAULTS), seed=0)
    for _ in range(300):
        e.step()
    m = measure(e.X[:, :2], e.L, radius=e.cfg.dist_lambda ** -0.5 if e.cfg.dist_lambda else 1.0)
    for k in ("rg", "rg_over_box", "occupancy", "n_clusters", "conservation"):
        assert np.isfinite(m[k])
