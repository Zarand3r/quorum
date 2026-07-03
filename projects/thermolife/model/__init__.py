"""thermolife.model — the shared learned cell rule (PLAN.md §5, §9, §12).

Reads observations/messages; emits action *intents* and transfer *requests*.
Never mutates fields directly — hands intents to env.transactions. Base weights
frozen within an episode (I9); only h/z/interface-expression change online.

Planned modules (PLAN.md §12): cell_core (F_theta), interfaces (f_l/f_rho),
binding (kappa/alpha), predictor, plasticity (G_phi). Deferred past Slice 0
(§15.3); enters at M2. No implementation yet.
"""
