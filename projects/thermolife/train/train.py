"""M2 training: teach the fold to dock (lock-and-key matching).

Minimizes −log A_final[i, partner(i)] over scenes sampled from the vocabulary,
by Adam on (W_c, W_v, MLP, e_types) through the unrolled fold. The
complementarity metric M stays FIXED (π-rotation) so a high score keeps meaning
*complementary shapes*, and the render projection P is display-only.

Run:  bazel run //projects/thermolife:train -- --out /tmp/trained_fold.npz
Eval: accuracy = fraction of tokens whose argmax final attention is their
      partner, on freshly sampled held-out scenes (unseen shuffles + noise).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from autograd import grad

from fold.config import FoldConfig, load_fold_config
from fold.transformer import block_step
from fold.vocab import VocabConfig, init_type_embeddings, sample_scene, scene_embed
from fold.weights import FoldWeights
from train.diff_fold import batch_loss, params_from_weights

_HERE = Path(__file__).resolve().parent
_DEFAULT_CONFIG = _HERE.parent / "configs" / "fold.yaml"


def evaluate(params: dict, w_template: FoldWeights, vc: VocabConfig,
             cfg: FoldConfig, t_steps: int, n_scenes: int, seed: int) -> float:
    """Held-out matching accuracy, computed with the *mechanism* fold (parity-
    gated), so what we score is exactly what the viewer will run."""
    w = weights_with_params(w_template, params)
    rng = np.random.default_rng(seed)
    correct = total = 0
    for _ in range(n_scenes):
        types, partner, noise = sample_scene(vc, rng)
        x = scene_embed(np.asarray(params["e_types"]), types, noise, vc.noise_sigma)
        a = None
        for _ in range(t_steps):
            x, _, a = block_step(x, w, cfg)
        correct += int((np.argmax(a, axis=1) == partner).sum())
        total += len(partner)
    return correct / total


def weights_with_params(w: FoldWeights, params: dict) -> FoldWeights:
    return FoldWeights(
        W_c=np.asarray(params["W_c"]), M=w.M, W_v=np.asarray(params["W_v"]),
        W1=np.asarray(params["W1"]), b1=np.asarray(params["b1"]),
        W2=np.asarray(params["W2"]), b2=np.asarray(params["b2"]), P=w.P,
    )


def train(cfg: FoldConfig, vc: VocabConfig, *, t_steps: int, iters: int,
          batch: int, lr: float, seed: int, log=print) -> tuple[dict, FoldWeights, list]:
    w0 = FoldWeights.random(cfg, seed)
    params = params_from_weights(w0, init_type_embeddings(vc, seed))
    rng = np.random.default_rng(seed + 1)
    loss_grad = grad(
        lambda p, scenes: batch_loss(p, scenes, vc.noise_sigma, w0.M, cfg, t_steps)
    )
    # Adam
    m = {k: np.zeros_like(v) for k, v in params.items()}
    v = {k: np.zeros_like(x) for k, x in params.items()}
    b1, b2, eps = 0.9, 0.999, 1e-8
    history = []
    for it in range(1, iters + 1):
        scenes = [sample_scene(vc, rng) for _ in range(batch)]
        g = loss_grad(params, scenes)
        for k in params:
            m[k] = b1 * m[k] + (1 - b1) * g[k]
            v[k] = b2 * v[k] + (1 - b2) * g[k] ** 2
            mh = m[k] / (1 - b1**it)
            vh = v[k] / (1 - b2**it)
            params[k] = params[k] - lr * mh / (np.sqrt(vh) + eps)
        if it % 50 == 0 or it == 1:
            loss = float(batch_loss(params, scenes, vc.noise_sigma, w0.M, cfg, t_steps))
            acc = evaluate(params, w0, vc, cfg, t_steps, n_scenes=50, seed=99_000 + it)
            history.append((it, loss, acc))
            log(f"iter {it:5d}  loss {loss:.4f}  held-out acc {acc:.3f}")
    return params, w0, history


def save(path: Path, params: dict, w: FoldWeights, vc: VocabConfig, t_steps: int) -> None:
    np.savez(
        path,
        W_c=params["W_c"], W_v=params["W_v"], W1=params["W1"], b1=params["b1"],
        W2=params["W2"], b2=params["b2"], e_types=params["e_types"],
        M=w.M, P=w.P,
        n_pairs=vc.n_pairs, noise_sigma=vc.noise_sigma, t_steps=t_steps,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="train the fold to dock")
    p.add_argument("--config", default=str(_DEFAULT_CONFIG))
    p.add_argument("--out", default="/tmp/trained_fold.npz")
    p.add_argument("--iters", type=int, default=1500)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--t-steps", type=int, default=12)
    p.add_argument("--lr", type=float, default=3e-3)
    p.add_argument("--noise-sigma", type=float, default=0.6)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    cfg = load_fold_config(args.config)
    vc = VocabConfig(
        n_pairs=cfg.n_tokens // 2, d=cfg.d,
        noise_sigma=args.noise_sigma, init_scale=cfg.init_scale,
    )
    params, w0, history = train(
        cfg, vc, t_steps=args.t_steps, iters=args.iters,
        batch=args.batch, lr=args.lr, seed=args.seed,
    )
    final_acc = evaluate(params, w0, vc, cfg, args.t_steps, n_scenes=200, seed=123_456)
    print(f"FINAL held-out accuracy (200 scenes): {final_acc:.4f}")
    save(Path(args.out), params, w0, vc, args.t_steps)
    print(f"saved weights -> {args.out}")
    return 0 if final_acc > 0.95 else 1


if __name__ == "__main__":
    sys.exit(main())
