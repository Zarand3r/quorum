"""thermolife.sim — the operational Slice-0 loop and web control surface.

Distinct from ``train/`` (the future TBPTT meta-training loop, M2+): ``sim/``
runs the substrate forward and exposes start/pause/restart control. Modules:
``forager`` (hand-coded baseline policy), ``tick`` (the PLAN.md §10.1 pipeline),
``runner`` (headless loop + metrics), ``controller`` + ``server`` (Step 6 web
control). No learned components — those are M1+ (out of Slice 0 scope).
"""
