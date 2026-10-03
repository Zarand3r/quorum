"""Benchmark and profile the exact production vesicle step path."""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import time

import numpy as np

from field import Field
from field import _core, _well
from transformer import VivariumTransformer
from vesicle import VesicleEngine


class LegacyTransformer(VivariumTransformer):
    """Pre-2026-09-22 hot path, retained only for exact audit comparisons."""

    def _nonbonded_pairs(self, X):
        sep, dist, pairs = self.f._pairs(X)
        return np.asarray(pairs), sep, dist

    def _score_nonbonded(self, r, pairs):
        field = self.f
        sigma, chi, extra = field._env(r, pairs)
        scaled = r / sigma
        _, core_derivative = _core(scaled, field.core_height)
        well, well_derivative = _well(scaled, field.rc)
        self._mb = (extra, well, scaled, sigma, r, pairs) if extra is not None else None
        derivative = field.eps * (core_derivative + well_derivative * chi) / sigma
        derivative = np.where(r < field.rc * sigma, derivative, 0.0)
        return -derivative / np.maximum(r, 1e-12)


def compare_legacy(steps: int) -> None:
    """Require combined optimized and former production paths to stay bit-identical."""
    old = VesicleEngine(seed=509, start="dispersed")
    new = VesicleEngine(seed=509, start="dispersed")
    old.field.SKIN = 0.6
    old.ig.tf = LegacyTransformer(old.field)
    old.ig.F = old.ig.tf.attention(old.X)
    for step in range(steps):
        old.step()
        new.step()
        for name, left, right in (("X", old.X, new.X), ("v", old.ig.v, new.ig.v),
                                  ("F", old.ig.F, new.ig.F)):
            if not np.array_equal(left, right):
                raise AssertionError(
                    f"legacy mismatch at step {step + 1} in {name}: "
                    f"max={np.max(np.abs(left - right))}")
    print(f"legacy comparison: {steps} production steps bit-identical")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--skin", type=float, default=Field.SKIN)
    parser.add_argument("--compare-legacy", type=int, default=0, metavar="STEPS")
    args = parser.parse_args()
    if args.compare_legacy:
        compare_legacy(args.compare_legacy)
        return
    Field.SKIN = args.skin
    engine = VesicleEngine(seed=509, start="dispersed")
    for _ in range(args.warmup):
        engine.step()
    profiler = cProfile.Profile()
    if args.profile:
        profiler.enable()
    started = time.perf_counter()
    for _ in range(args.steps):
        engine.step()
    elapsed = time.perf_counter() - started
    if args.profile:
        profiler.disable()
    print(f"{1000 * elapsed / args.steps:.4f} ms/step; {args.steps / elapsed:.1f} steps/s")
    if args.profile:
        output = io.StringIO()
        pstats.Stats(profiler, stream=output).strip_dirs().sort_stats("tottime").print_stats(30)
        print(output.getvalue())


if __name__ == "__main__":
    main()
