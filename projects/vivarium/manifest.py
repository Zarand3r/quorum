"""THE SINGLE SOURCE OF TRUTH for what this project runs, and what it merely keeps.

Companion: `SUMMARY.md` "How success is measured" is the single source of truth for what COUNTS as
a result. This file says which code is live; that section says which number is real.

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
    "_lumen3d",   # 3-D enclosure detector; archived with the 3-D scope 2026-09-14
    "_cgrad", "_flat2", "_geom", "_pairing",
    "_ring_sweep", "_viv_hunt", "_viv_morph", "_viv_vacuum",
    "aliveness", "bench_emergence", "bench_emergence3d", "bicelle2d",
    "bilayer3d", "block", "engine", "fig2d",
    "pack", "polar_pack", "pure", "render",
    "ring_assay", "rung0", "rung1c", "structures",
    "substrate", "toy2d",
}

SUPPORT = {
    "emerge_gate2",
    "vesicle_gate",
    "_curl_cal", "_cvcontrol", "_cvdegenerate", "_disk_closure",
    "_emerge2d", "_eos_check", "_fluidity", "_kappa",
    "_linetension", "_lumen", "_lumen_field",
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

# ---------------------------------------------------------------------------------------------
# SCOPE: TWO DIMENSIONS ONLY.
#
# Decision 2026-09-14. 3-D is ARCHIVED -- kept readable and re-enablable, not developed, not tested.
# The reasons, all already on record:
#   * its foundation is retracted: the "bending fix" was measured to STRETCH molecules 67% rather
#     than stiffen them, so everything downstream of it needs re-deriving (ROADMAP 9 item 9);
#   * ~29x the 2-D cost per run, against a 2-D emergence rate of 1-2 in 20 that is itself not yet
#     understood -- spending 29x on an unsolved question is the wrong order;
#   * every open question that matters (does a patch bend? what selects a size? which gate defines a
#     vesicle?) is answerable in 2-D and unanswered there.
#
# Flip this to True to re-enable. Tests that exercise 3-D skip on it rather than being deleted, so
# the coverage is visible and comes back with the flag -- deleting a failing test to make a suite
# green is the exact move `docs/MEASUREMENT_DISCIPLINE.md` exists to prevent.
THREE_D = False

TIERS = {"ACTIVE": ACTIVE, "ORACLE": ORACLE, "ARCHIVED": ARCHIVED, "SUPPORT": SUPPORT}
