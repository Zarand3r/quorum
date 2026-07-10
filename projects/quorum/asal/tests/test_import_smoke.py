"""Import + surface-area smoke tests for the vendored ASAL sources.

These deliberately avoid running a full CLIP forward or a Sep-CMA-ES loop
(both need model weights + significant compute). They just confirm that the
Bazel-wired sys.path is correct and the top-level entry points can be
imported without side-effects, which catches most vendoring / packaging
mistakes cheaply.
"""

from __future__ import annotations


def test_substrates_package_importable() -> None:
    import substrates  # noqa: F401
    assert hasattr(substrates, "create_substrate")


def test_boids_substrate_constructible() -> None:
    from substrates.boids import Boids
    b = Boids()  # defaults: n_boids=64 in the class ctor
    assert b.n_boids > 0
    assert b.n_nbrs > 0


def test_foundation_models_package_importable() -> None:
    import foundation_models  # noqa: F401
    assert hasattr(foundation_models, "create_foundation_model")


def test_rollout_module_importable() -> None:
    import rollout  # noqa: F401
    assert callable(rollout.rollout_simulation)


def test_asal_metrics_importable() -> None:
    import asal_metrics
    assert callable(asal_metrics.calc_supervised_target_score)
    assert callable(asal_metrics.calc_open_endedness_score)
