# Reproducing ASAL Boids on this repo

The commands below reproduce ASAL's Boids-flocking experiment on the vendored
sources at `projects/quorum/asal/`. Verified on this host (RTX PRO 6000
Blackwell, 97 GB VRAM) with JAX 0.4.38 + jaxlib 0.4.38 + CUDA 12 wheels.

## One-time setup

The Bazel-committed lock is CPU-only (portable across hosts). For the GPU
reproduction, install the `[gpu]` extra via `uv`, which pulls the
`jax[cuda12]` wheels into a project-local venv:

```bash
cd projects/quorum/asal
uv sync --extra gpu
uv run python -c "import jax; print(jax.default_backend(), jax.devices())"
# expected: gpu [CudaDevice(id=0)]
```

## Quick smoke (~10 s post-JIT)

```bash
cd projects/quorum/asal
uv run python main_opt.py \
    --substrate boids \
    --prompts "a flock of birds" \
    --n_iters 20 --pop_size 4
```

Loss should tick down from around −0.28 (CLIP similarity 0.28 to "a flock of
birds") into the −0.29 range. `n_iters < 10` triggers a pre-existing
`ZeroDivisionError` in upstream's every-10%-save logic — keep n_iters ≥ 10.

## Full reproduction (~30 s post-JIT)

```bash
cd projects/quorum/asal
mkdir -p /tmp/asal-boids-flock
uv run python main_opt.py \
    --substrate boids \
    --prompts "a flock of birds" \
    --n_iters 500 --pop_size 16 --sigma 0.1 \
    --save_dir /tmp/asal-boids-flock
```

`--save_dir` writes:

- `best.pkl` — `(best_member_params, best_fitness)` tuple; `best_member_params`
  is a flat `float32[193]` (the flattened `BoidNetwork` weights).
- `data.pkl` — `{best_loss: float32[n_iters], loss_dict: ...}`.

Result on this host (seed=0, 500 iters, pop_size=16, sigma=0.1):

- start loss: −0.285   (CLIP similarity 0.285)
- final loss: **−0.314**  (CLIP similarity 0.314)
- CMA-ES plateau: iter ~141

See `artifacts/boids_flock_500iters/loss_curve.png` and `final_frame.png` for
the run's outputs. ASAL's paper uses `n_iters=1000` upstream; going longer
should push CLIP similarity higher.

## Rendering the final frame from `best.pkl`

```python
import pickle, jax, jax.numpy as jnp, numpy as np
from functools import partial
from PIL import Image
import substrates, foundation_models
from rollout import rollout_simulation

with open("/tmp/asal-boids-flock/best.pkl", "rb") as f:
    best_params, best_fitness = pickle.load(f)      # note: params first

substrate = substrates.create_substrate("boids")
substrate = substrates.FlattenSubstrateParameters(substrate)
fm = foundation_models.create_foundation_model("clip")
rollout_fn = partial(
    rollout_simulation, s0=None, substrate=substrate, fm=fm,
    rollout_steps=1000, time_sampling=(1, True), img_size=224,
    return_state=False,
)
rollout_fn = jax.jit(rollout_fn)
data = rollout_fn(jax.random.PRNGKey(0), best_params)
img = np.clip(np.asarray(data["rgb"])[-1], 0, 1)
Image.fromarray((img * 255).astype(np.uint8)).save("final_frame.png")
```

## Bazel path (once we lock CUDA wheels into `requirements_lock.txt`)

Not wired yet. The CPU-only lock supports:

```bash
bazel build //projects/quorum/asal:asal
bazel test  //projects/quorum/asal:test_suite
bazel run   //projects/quorum/asal:main_opt -- --help
```

Wiring CUDA-13 nvidia-\* wheels into `asal_deps` (mirroring the pattern in
[the slice0 branch's BUILD.bazel](../../../projects/quorum/slice0/BUILD.bazel)
where torch's `_load_global_deps` needed each variant-suffix wheel listed
explicitly) lands in a follow-up commit — the `uv sync --extra gpu` path
above is sufficient for reproduction.

## Other substrates and objectives

The vendored `main_opt.py` and `main_illuminate.py` accept `--substrate`
∈ {`boids`, `lenia`, `plife`, `plife_plus`, `plenia`, `dnca`, `nca_d1`,
`gol`}. See `substrates/__init__.py` for the exact hyperparameters each
one carries. Multi-prompt temporal targets (`--prompts "a;b;c"` +
`--time_sampling 3`) and open-endedness search (`--coef_oe 1`) are the two
other ASAL modes worth exercising after the Boids run works.
