"""Simulation engine + thread-safe control state machine (Step 6, gate P8).

``SimEngine`` owns the world + ledger and steps it deterministically.
``SimController`` wraps one engine behind a bounded state machine
(``IDLE → RUNNING ⇄ PAUSED``, ``restart → tick 0``, ``stop → IDLE``) driven by a
*single* background stepping thread. HTTP handlers only ever call controller
methods — they never touch the world (P8). Because pause/resume merely gate
whether the thread calls ``engine.step()``, the trajectory at tick N depends only
on (seed, scenario, N), never on when a pause happened.
"""

from __future__ import annotations

import threading
from enum import Enum

import numpy as np

from env.config import WorldConfig
from env.fields import Field, from_config
from env.invariants import conserved_total
from env.transactions import TransactionLedger
from sim.forager import forager_position
from sim.tick import tick


class SimStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class ControllerError(RuntimeError):
    """Raised on an illegal control transition (e.g. pause while IDLE)."""


class SimEngine:
    """Deterministic single-world stepper + JSON snapshot."""

    def __init__(self, cfg: WorldConfig, seed: int) -> None:
        self.cfg = cfg
        self.seed = seed
        self.world = from_config(cfg, seed)
        self.ledger = TransactionLedger()
        self._t0 = conserved_total(self.world)

    def step(self) -> None:
        tick(self.world, self.cfg, self.ledger)

    @property
    def tick(self) -> int:
        return self.world.tick

    def residual(self) -> float:
        return abs(conserved_total(self.world) - self.ledger.expected_total(self._t0))

    def snapshot(self, status: SimStatus) -> dict:
        nutrient = self.world.fields[:, :, Field.NUTRIENT]
        pos = forager_position(self.world)
        alive = int((self.world.alive >= self.cfg.lifecycle.alive_threshold).sum())
        return {
            "status": status.value,
            "tick": int(self.world.tick),
            "height": self.world.height,
            "width": self.world.width,
            "residual": self.residual(),
            "nutrient_max": float(nutrient.max()),
            "nutrient": np.round(nutrient, 4).tolist(),
            "forager": [pos[0], pos[1]] if pos is not None else None,
            "alive": alive,
            "energy_total": float(self.world.energy.sum()),
        }


class SimController:
    """Owns the stepping thread + the control state machine.

    ``autostart_thread=False`` skips the background thread so tests can drive
    stepping synchronously via :meth:`_tick_now` (deterministic, no wall-clock).
    """

    def __init__(
        self,
        cfg: WorldConfig,
        default_seed: int = 42,
        step_hz: float = 50.0,
        autostart_thread: bool = True,
    ) -> None:
        self._cfg = cfg
        self._default_seed = default_seed
        self._step_period = 1.0 / step_hz if step_hz > 0 else 0.0
        self._lock = threading.Lock()
        self._resume = threading.Event()  # set ⇒ thread may step
        self._shutdown = False
        self._status = SimStatus.IDLE
        self._engine: SimEngine | None = None
        self._seed = default_seed
        self._scenario = cfg.scenario.name
        self._thread: threading.Thread | None = None
        if autostart_thread:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # --- control transitions -------------------------------------------------
    def start(self, seed: int | None = None) -> None:
        with self._lock:
            self._seed = self._default_seed if seed is None else seed
            self._engine = SimEngine(self._cfg, self._seed)
            self._status = SimStatus.RUNNING
        self._resume.set()

    def pause(self) -> None:
        with self._lock:
            if self._status != SimStatus.RUNNING:
                raise ControllerError(f"cannot pause while {self._status.value}")
            self._status = SimStatus.PAUSED
        self._resume.clear()

    def resume(self) -> None:
        with self._lock:
            if self._status != SimStatus.PAUSED:
                raise ControllerError(f"cannot resume while {self._status.value}")
            self._status = SimStatus.RUNNING
        self._resume.set()

    def restart(self) -> None:
        with self._lock:
            if self._status == SimStatus.IDLE:
                raise ControllerError("cannot restart before start")
            self._engine = SimEngine(self._cfg, self._seed)  # same seed → tick 0
            self._status = SimStatus.RUNNING
        self._resume.set()

    def stop(self) -> None:
        with self._lock:
            self._status = SimStatus.IDLE
            self._engine = None
        self._resume.clear()

    def shutdown(self) -> None:
        self._shutdown = True
        self._resume.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    # --- observation ---------------------------------------------------------
    def status(self) -> SimStatus:
        with self._lock:
            return self._status

    def snapshot(self) -> dict:
        with self._lock:
            if self._engine is None:
                return {
                    "status": self._status.value,
                    "tick": 0,
                    "height": self._cfg.height,
                    "width": self._cfg.width,
                    "residual": 0.0,
                    "nutrient_max": 0.0,
                    "nutrient": None,
                    "forager": None,
                    "alive": 0,
                    "energy_total": 0.0,
                }
            return self._engine.snapshot(self._status)

    # --- stepping ------------------------------------------------------------
    def _tick_now(self) -> None:
        """One synchronous step iff RUNNING. Used by the thread and by tests."""
        with self._lock:
            if self._status == SimStatus.RUNNING and self._engine is not None:
                self._engine.step()

    def _run(self) -> None:
        import time

        while not self._shutdown:
            self._resume.wait()
            if self._shutdown:
                break
            self._tick_now()
            if self._step_period:
                time.sleep(self._step_period)
