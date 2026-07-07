"""EcoEngine — one tick of the conserved economy (IMPLEMENTATION_PLAN.md Steps 1–5).

Pipeline per tick (all vectorized, P5):
  inject → harvest (energy in) → move → metabolism → pay/death (energy out) →
  reproduction (heredity) → drift the source.

Every step books its energy movement between the three ledger books so the residual
is ~0 to machine precision (P1). Death is a boolean-index compaction; birth is a
batched append bounded by ``n_max`` (P6). No per-token Python loop.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from eco.config import EcoConfig
from eco.ledger import book_total, ledger_residual
from eco.policies import hand_forager
from eco.resource import access_weight, harvest
from eco.state import EcoState, init_state, source_at

Policy = Callable[[EcoState, EcoConfig], "tuple[np.ndarray, np.ndarray]"]


class EcoEngine:
    def __init__(
        self,
        cfg: EcoConfig,
        policy: Policy | None = None,
        state: EcoState | None = None,
    ) -> None:
        self.cfg = cfg
        self.policy = policy if policy is not None else hand_forager
        self.state = state if state is not None else init_state(cfg)
        self.last_residual: float = 0.0

    def tick(self) -> float:
        """Advance one tick. Returns the ledger residual (P1); |residual| < 1e-9."""
        cfg, s = self.cfg, self.state
        total_before = book_total(s.pool, s.e, s.dissipated)

        # 1. inject resource into the pool
        injected = cfg.inject
        s.pool += injected

        # 2. policy decides actions
        dx, gate = self.policy(s, cfg)

        # 3. harvest — energy in (η credited, 1-η dissipated, pool depleted)
        delta_e, drawn, diss_harvest = harvest(s.x, s.mu, s.pool, gate, cfg)
        s.pool -= drawn
        s.e = s.e + delta_e
        s.dissipated += diss_harvest

        # 4. move — apply displacement; kinetic cost accrues into total cost below
        s.x = s.x + dx
        move_cost = cfg.c_move * np.sum(dx * dx, axis=1)          # [N]

        # 5. total energy-out this tick = metabolism + motion
        cost = cfg.c_base + move_cost                            # [N]

        # 6. death: tokens that cannot afford the tick spend their last energy as heat
        dead = cost >= s.e                                       # [N] bool
        s.dissipated += float(np.sum(s.e[dead]))                 # e[dead] ≥ 0 → valid heat
        alive = ~dead
        s.dissipated += float(np.sum(cost[alive]))              # survivors pay in full
        # compact to survivors (vectorized rebuild, not a loop)
        s.x = s.x[alive]
        s.g = s.g[alive]
        s.e = s.e[alive] - cost[alive]

        # 7. reproduction — split on e ≥ e_div; energy conserved, gene mutated (heredity)
        self._reproduce()

        # 8. drift the source (no energy change)
        s.t += 1
        s.mu = source_at(s.t, cfg)

        total_after = book_total(s.pool, s.e, s.dissipated)
        self.last_residual = ledger_residual(total_before, total_after, injected)
        return self.last_residual

    def _reproduce(self) -> None:
        cfg, s = self.cfg, self.state
        eligible = np.nonzero(s.e >= cfg.e_div)[0]              # stable order
        room = cfg.n_max - s.n
        if room <= 0 or eligible.size == 0:
            return
        idx = eligible[:room]                                   # refuse past the cap (P6)
        child_e = s.e[idx] / 2.0                                # energy split, conserved
        s.e[idx] -= child_e
        pos_noise = cfg.repro_pos_noise * s.rng.standard_normal((idx.size, cfg.d))
        gene_noise = cfg.sigma_g * s.rng.standard_normal((idx.size, cfg.d_g))
        child_x = s.x[idx] + pos_noise
        child_g = s.g[idx] + gene_noise
        s.x = np.concatenate([s.x, child_x], axis=0)
        s.g = np.concatenate([s.g, child_g], axis=0)
        s.e = np.concatenate([s.e, child_e], axis=0)

    # ---- observation (read-only; never feeds back into dynamics — P2) ----

    def snapshot(self) -> dict:
        st = self.state
        w = access_weight(st.x, st.mu, self.cfg.sigma_r) if st.n else np.zeros(0)
        return {
            "t": st.t,
            "n": st.n,
            "pool": st.pool,
            "dissipated": st.dissipated,
            "energy": float(np.sum(st.e)),
            "mu": st.mu.tolist(),
            "mean_access": float(np.mean(w)) if st.n else 0.0,
            "residual": self.last_residual,
        }


def run(cfg: EcoConfig, ticks: int, policy: Policy | None = None) -> dict:
    """Headless rollout. Returns the observable trajectory (read-only)."""
    eng = EcoEngine(cfg, policy=policy)
    max_abs_residual = 0.0
    survived = ticks
    pop = [eng.state.n]
    for _ in range(ticks):
        r = eng.tick()
        max_abs_residual = max(max_abs_residual, abs(r))
        pop.append(eng.state.n)
        if eng.state.n == 0:
            survived = eng.state.t
            break
    return {
        "survived": survived,
        "final_n": eng.state.n,
        "max_abs_residual": max_abs_residual,
        "pop": pop,
    }
