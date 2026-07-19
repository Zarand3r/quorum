"""E2 — evolve the economy's chemistry θ so the population *learns* to forage.

The E1 attention operator (eco/interaction.py) drives the population with a FIXED
random θ; under drift a random θ starves near the hand-forager's floor. E2 makes
θ the thing selection acts on, but through a *gradient-free* channel: the fitness
(population viability under drift) routes through death/reproduction/compaction —
non-differentiable by construction — so we optimise it with **Evolution Strategies**
(OpenAI-ES: antithetic sampling + rank-normalised gradient estimate) rather than
backprop.

Fitness = population-ticks Σ_t n_t over a rollout under the E0-gate drift, averaged
over several init seeds (a viable chemistry keeps N alive; an unviable one decays to
0 and scores near its extinction tick). NO order/coordination term is optimised — any
interaction structure that appears is *emergent*, not rewarded (P2). The metric M
(π-rotation complementarity) is FIXED and NOT evolved; θ = every other matrix.

Run:   bazel run //projects/thermolife:train_es -- --out configs/eco_theta.npz \
           --iters 60 --pop 40 --ticks 200
Eval:  compares evolved θ against random-θ and the hand-forager on held-out seeds.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

import numpy as np

from eco.config import EcoConfig, load_eco_config
from eco.engine import EcoEngine
from eco.interaction import EcoWeights, attention_policy
from eco.policies import hand_forager
from eco.state import init_state

_HERE = Path(__file__).resolve().parent
_DEFAULT_CONFIG = _HERE.parent / "configs" / "eco.yaml"

# θ = every matrix the ES evolves. M (the fixed π-rotation metric) is excluded on
# purpose: a high dock score must keep meaning "complementary shapes" (P7), so the
# metric is chemistry we hold fixed while selection reshapes the readout and head.
_EVOLVED = ("W_c", "G_c", "W_v", "W1", "b1", "W2", "b2")


# --- θ ↔ flat vector -------------------------------------------------------------

def flatten(w: EcoWeights) -> np.ndarray:
    """Pack the evolved matrices into one contiguous vector (M excluded)."""
    return np.concatenate([np.asarray(getattr(w, k)).ravel() for k in _EVOLVED])


def unflatten(vec: np.ndarray, template: EcoWeights) -> EcoWeights:
    """Rebuild an EcoWeights from a flat vector, borrowing shapes + fixed M."""
    out, off = {}, 0
    for k in _EVOLVED:
        ref = np.asarray(getattr(template, k))
        size = ref.size
        out[k] = vec[off:off + size].reshape(ref.shape)
        off += size
    if off != vec.size:
        raise ValueError(f"vector length {vec.size} != θ size {off}")
    return dataclasses.replace(template, **out)


def theta_size(template: EcoWeights) -> int:
    return sum(int(np.asarray(getattr(template, k)).size) for k in _EVOLVED)


# --- fitness ---------------------------------------------------------------------

def _rollout_population_ticks(policy, cfg: EcoConfig, seed: int, ticks: int) -> float:
    """One rollout; return Σ_t n_t (population-ticks). Extinction ends the sum
    early — a chemistry that keeps N alive integrates far more area than one that
    decays to 0. Read-only over θ (the policy closure never mutates its weights)."""
    state = init_state(dataclasses.replace(cfg, seed=seed))
    eng = EcoEngine(cfg, policy=policy, state=state)
    total = float(eng.state.n)
    for _ in range(ticks):
        eng.tick()
        total += float(eng.state.n)
        if eng.state.n == 0:
            break
    return total


def fitness(vec: np.ndarray, template: EcoWeights, cfg: EcoConfig,
            seeds: tuple[int, ...], ticks: int, mode: str = "dist") -> float:
    """Mean population-ticks of θ=``vec`` across ``seeds`` under the E0-gate drift."""
    w = unflatten(vec, template)
    policy = attention_policy(w, cfg, mode=mode)
    return float(np.mean([_rollout_population_ticks(policy, cfg, s, ticks)
                          for s in seeds]))


def forager_baseline(cfg: EcoConfig, seeds: tuple[int, ...], ticks: int) -> float:
    return float(np.mean([_rollout_population_ticks(hand_forager, cfg, s, ticks)
                          for s in seeds]))


# --- OpenAI-ES -------------------------------------------------------------------

def _rank_normalise(f: np.ndarray) -> np.ndarray:
    """Map fitnesses to centred ranks in [-0.5, 0.5] (scale-free, outlier-robust)
    — the standard OpenAI-ES utility transform, so a few runaway rollouts can't
    dominate the update direction.

    Ties get the AVERAGE (fractional) rank, not distinct argsort ranks. This
    matters on this landscape: early on, most perturbations drive the population
    extinct at the same tick, so Σ_t n_t ties exactly across many rollouts.
    Distinct ranks would then hand an antithetic pair (+ε, −ε) with equal fitness
    a nonzero rank difference — a phantom gradient pointing in a direction set by
    array order, not signal. Average ranks make tied pairs cancel (u+ − u− = 0)."""
    n = f.size
    order = np.argsort(f, kind="stable")
    sorted_ranks = np.arange(n, dtype=np.float64)
    fs = f[order]
    i = 0
    while i < n:                                   # average each run of equal values
        j = i
        while j + 1 < n and fs[j + 1] == fs[i]:
            j += 1
        if j > i:
            sorted_ranks[i:j + 1] = (i + j) / 2.0
        i = j + 1
    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = sorted_ranks
    return ranks / (n - 1) - 0.5


def train_es(
    cfg: EcoConfig,
    *,
    iters: int,
    pop: int,
    ticks: int,
    sigma: float,
    lr: float,
    n_seeds: int,
    seed: int,
    k_harmonics: int = 4,
    hidden: int = 16,
    mode: str = "dist",
    log=print,
) -> tuple[EcoWeights, dict]:
    """Optimise θ by antithetic-sampled, rank-normalised Evolution Strategies.

    Returns (best θ as EcoWeights, history). Each iteration draws ``pop`` antithetic
    perturbation pairs, scores each on a rotating set of ``n_seeds`` init seeds, and
    steps θ along the rank-weighted perturbation average. The eval seeds ROTATE per
    iteration (seed = base + iter) so θ can't overfit one initial population.

    Best-θ is crowned on a SEPARATE, FIXED validation seed set — never the rotating
    training seeds. Comparing θ across iterations on different seeds is comparing
    different tasks: an easy init-population set flatters a mediocre θ. A fixed
    val set puts every iteration's θ on one common scale, so the θ we persist is
    genuinely the best chemistry found, not the luckiest-scored one."""
    template = EcoWeights.random(cfg, k_harmonics, hidden, seed)
    theta = flatten(template)
    dim = theta.size
    rng = np.random.Generator(np.random.PCG64(seed + 4242))
    # fixed validation seeds — disjoint from the rotating training seeds
    # (which live in [seed+1, seed+iters·n_seeds]) and from the caller's held-out set.
    val_seeds = tuple(int(seed + 5000 + j) for j in range(n_seeds))

    history = {"mean_fitness": [], "val_fitness": []}
    best_theta, best_score = theta.copy(), fitness(theta, template, cfg, val_seeds, ticks, mode)

    for it in range(iters):
        eval_seeds = tuple(int(seed + 1 + it * n_seeds + j) for j in range(n_seeds))
        eps = rng.standard_normal((pop, dim))
        # antithetic pairs: +eps and -eps share variance reduction (common seeds)
        scores = np.empty(2 * pop)
        for i in range(pop):
            scores[i] = fitness(theta + sigma * eps[i], template, cfg, eval_seeds, ticks, mode)
            scores[pop + i] = fitness(theta - sigma * eps[i], template, cfg, eval_seeds, ticks, mode)
        u = _rank_normalise(scores)
        grad = (u[:pop] - u[pop:])[:, None] * eps         # antithetic gradient estimate
        # N = 2·pop perturbations → the OpenAI-ES estimator normalizes by 2·pop·σ
        step = lr / (2 * pop * sigma) * grad.sum(axis=0)
        theta = theta + step

        val_fit = fitness(theta, template, cfg, val_seeds, ticks, mode)   # fixed scale
        history["mean_fitness"].append(float(scores.mean()))
        history["val_fitness"].append(val_fit)
        if val_fit > best_score:
            best_theta, best_score = theta.copy(), val_fit
        log(f"[es] iter {it:3d}  pop_mean={scores.mean():9.1f}  "
            f"val={val_fit:9.1f}  best={best_score:9.1f}")

    return unflatten(best_theta, template), history


# --- persistence -----------------------------------------------------------------

def save_theta(path: str | Path, w: EcoWeights, cfg: EcoConfig,
               k_harmonics: int, hidden: int) -> None:
    """Persist evolved θ + the shape metadata needed to rebuild it (M is fixed,
    so it is reconstructed from k_harmonics, not stored)."""
    np.savez(
        path,
        W_c=w.W_c, G_c=w.G_c, W_v=w.W_v, W1=w.W1, b1=w.b1, W2=w.W2, b2=w.b2,
        k_harmonics=np.int64(k_harmonics), hidden=np.int64(hidden), d=np.int64(cfg.d),
    )


def load_theta(path: str | Path, cfg: EcoConfig) -> EcoWeights:
    """Rebuild evolved θ; M is the fixed π-rotation from the stored k_harmonics."""
    z = np.load(path)
    k = int(z["k_harmonics"])
    signs = np.array([(-1.0) ** i for i in range(1, k + 1)])
    return EcoWeights(
        W_c=z["W_c"], G_c=z["G_c"], M=np.diag(np.repeat(signs, 2)),
        W_v=z["W_v"], W1=z["W1"], b1=z["b1"], W2=z["W2"], b2=z["b2"],
    )


# --- CLI -------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="E2: evolve eco chemistry θ (ES)")
    p.add_argument("--config", default=str(_DEFAULT_CONFIG))
    p.add_argument("--out", default=str(_HERE.parent / "configs" / "eco_theta.npz"))
    p.add_argument("--iters", type=int, default=60)
    p.add_argument("--pop", type=int, default=40, help="antithetic pairs per iter")
    p.add_argument("--ticks", type=int, default=200, help="rollout horizon")
    p.add_argument("--sigma", type=float, default=0.1, help="perturbation std")
    p.add_argument("--lr", type=float, default=0.1)
    p.add_argument("--n-seeds", type=int, default=3, help="init seeds per fitness eval")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--k-harmonics", type=int, default=4)
    p.add_argument("--hidden", type=int, default=16)
    args = p.parse_args(argv)

    cfg = load_eco_config(args.config)
    w, _ = train_es(
        cfg, iters=args.iters, pop=args.pop, ticks=args.ticks, sigma=args.sigma,
        lr=args.lr, n_seeds=args.n_seeds, seed=args.seed,
        k_harmonics=args.k_harmonics, hidden=args.hidden,
    )

    # held-out report: evolved θ vs random-θ vs hand-forager on UNSEEN seeds
    hold = tuple(range(9000, 9000 + 8))
    evolved = fitness(flatten(w), w, cfg, hold, args.ticks)
    rand_template = EcoWeights.random(cfg, args.k_harmonics, args.hidden, args.seed)
    random_fit = fitness(flatten(rand_template), rand_template, cfg, hold, args.ticks)
    forager = forager_baseline(cfg, hold, args.ticks)
    print(f"\n[es] HELD-OUT (seeds {hold[0]}..{hold[-1]}, {args.ticks} ticks):")
    print(f"      evolved θ    : {evolved:9.1f} pop-ticks")
    print(f"      random  θ    : {random_fit:9.1f} pop-ticks")
    print(f"      hand-forager : {forager:9.1f} pop-ticks")
    print(f"      evolved/random = {evolved / max(random_fit, 1.0):.2f}×,  "
          f"evolved/forager = {evolved / max(forager, 1.0):.2f}×")

    save_theta(args.out, w, cfg, args.k_harmonics, args.hidden)
    print(f"[es] saved evolved θ → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
