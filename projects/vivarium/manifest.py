"""THE SINGLE SOURCE OF TRUTH for what this project runs, and what it merely keeps.

Every `.py` at the top level belongs to exactly one tier. `tests/test_manifest.py` enforces that, so
a new file cannot appear unclassified and the ACTIVE stack cannot quietly grow a dependency on an
archived one. The tiers exist because this directory has, at various times, held eleven things that
could be called "the simulation", and results were once scored against the wrong one.

  ACTIVE    the one vivarium under development. Every current result comes from here.
  ORACLE    reference physics from the literature, deliberately OUTSIDE the transformer constraint.
            Their job is to be the known-answer case the ACTIVE stack is checked against. ACTIVE must
            NOT import them -- an oracle that leaks into production stops being an independent check.
  ARCHIVED  earlier simulations, kept so their results can be traced. ACTIVE must NOT import them.
  SUPPORT   instruments, harnesses, builders, renderers, viewer. Not simulations.

WHY AN ORACLE IS NOT A TARGET. `docs/WHY_THE_ORACLE_DOES_NOT_TRANSFER.md` measured it: the oracle's
vesicle is bought, not emergent. Same N, L, seed, integrator, 1.5M steps, only `beta` (the spontaneous
curvature) differing -- beta=0.15 gives 3-4 sustained vesicles, beta=0.00 gives flat sheets at every
checkpoint. Porting the oracle's angular term into ACTIVE would import the answer, not the physics.
"""
from __future__ import annotations

ACTIVE = {
    "_mixture", "_scatter", "config", "field",
    "integrate", "manybody", "rng", "transformer",
}

ORACLE = {
    "_sl_model", "attention_ylz", "bilipid", "cooke_deserno",
    "dpd_reference", "ylz",
}

ARCHIVED = {
    "_cgrad", "_flat2", "_geom", "_pairing",
    "_ring_sweep", "_viv_hunt", "_viv_morph", "_viv_vacuum",
    "aliveness", "bench_emergence", "bench_emergence3d", "bicelle2d",
    "bilayer3d", "block", "engine", "fig2d",
    "pack", "polar_pack", "pure", "render",
    "ring_assay", "rung0", "rung1c", "structures",
    "substrate", "toy2d",
}

SUPPORT = {
    "_curl_cal", "_cvcontrol", "_cvdegenerate", "_disk_closure",
    "_emerge2d", "_eos_check", "_fluidity", "_kappa",
    "_linetension", "_lumen", "_lumen3d", "_lumen_field",
    "_lumen_overlay", "_micelle_pole", "_sasa", "_shot",
    "_sizing3d", "_solvent_gate", "_thermal_ref", "_vesicle_calib",
    "_ylz_run", "bench_step", "bilayer_metrics", "chemistry",
    "cluster_shot", "curl", "curl_witness", "emerge_reduced",
    "fig_state", "gap_closure", "gap_shot", "harness",
    "inspect_raw", "make_figures", "metrics_membrane", "metrics_pack",
    "micelle_probe", "null_control", "pathway", "phase",
    "phase_diagram", "references", "render_state", "server",
    "sweep_head_area", "vesicle", "vesicle_assembly", "xsection",
}

TIERS = {"ACTIVE": ACTIVE, "ORACLE": ORACLE, "ARCHIVED": ARCHIVED, "SUPPORT": SUPPORT}
