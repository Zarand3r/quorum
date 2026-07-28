# quorum

A Bazel workspace for three related experiments in **emergence** — the question of when collective
behaviour is genuinely computed rather than merely described.

| project | one line | status |
|---|---|---|
| [**`projects/vivarium/`**](projects/vivarium/) | A molecular simulator in which **every force is a transformer operation** — each molecule is a token, each step a forward pass. Can a lipid bilayer assemble itself out of nothing but attention? | active; hydrophobic effect and aggregation emerge, radial order does not |
| [`projects/thermolife/`](projects/thermolife/) | **Embedding folding as ligand–receptor docking.** Token embeddings fold through iterated attention and are drawn as *grounded* contour blobs — the drawn shape **is** the query/key, so `Q·K` is literally contour overlap (Parseval). | S0 mechanism built; training is M2 |
| [`projects/quorum/`](projects/quorum/) | Single-pass LLM population simulator, aiming at **computed** (irreducible) emergence, validated against Boids/Schelling baselines. | design only |

The three share one thread: **the representation is the physics.** A token's channels are not an
opaque latent — they are read as position, shape, and charge, and the forces act on exactly those
readings. That is what makes the emergent behaviour falsifiable rather than decorative.

## Start here

**[`projects/vivarium/`](projects/vivarium/)** is the most developed. Its
[`docs/BILAYER_REVIEW.md`](projects/vivarium/docs/BILAYER_REVIEW.md) is the honest research
narrative — twelve findings, most of them negative, each with the measurement that killed it.

## Quick start

Install bazel via [bazelisk](https://github.com/bazelbuild/bazelisk) (it reads `.bazelversion` and
fetches the right version automatically).

```bash
git clone https://github.com/Zarand3r/quorum.git && cd quorum
bazel test //...                                   # hermetic Python + deps, builds, runs every test

# the live 3-D molecular dish, in a browser
bazel run //projects/vivarium:serve -- --polar --dim3 --port 8082
```

Per project:

```bash
bazel test //projects/vivarium:test_suite          # 82 tests incl. the transformer-only audit
bazel run  //projects/vivarium:bilayer3d           # 3-D lipid self-assembly experiment
bazel test //projects/thermolife:test_suite        # the embedding-fold J1–J6 gate
bazel run  //projects/thermolife:serve -- --port 8787
```

## Layout

```
projects/
├── vivarium/     transformer-only molecular dynamics   (engine, benchmarks, live viewer, research log)
├── thermolife/   embedding folding as docking          (fold mechanism, viewer, J1–J6 gate)
└── quorum/       LLM population simulator              (design)
```

## Tooling

- **Bazel** — one workspace at the root (`MODULE.bazel`, Bzlmod). Commands work from anywhere in the
  tree. `.bazelrc.user` (gitignored) holds per-user overrides.
- **Python via `rules_python`** — a hermetic CPython 3.12 toolchain and a **per-project `pip.parse`
  hub** reading a pinned `requirements_lock.txt` next to each project, so dependency sets are
  isolated by construction. There is no Python at the repo root. To change a project's dependencies,
  edit its `requirements_lock.txt` and re-run `bazel test //...`.

## License

MIT.
