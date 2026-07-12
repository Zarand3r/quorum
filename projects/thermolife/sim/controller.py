"""Thread-safe control state machine around a single stepping engine.

Engine protocol: ``step()`` · ``tick`` (int) · ``residual()`` (float) ·
``snapshot(status) -> dict``. HTTP handlers only ever call controller methods —
they never touch the engine (keeps the control surface the sole mutator entry).
Transitions: ``IDLE → RUNNING ⇄ PAUSED``, ``restart → fresh engine (same seed)``,
``stop → IDLE``. A single background thread does the stepping; pause/resume just
gate whether it calls ``engine.step()``, so the state at tick N depends only on
(seed, N), never on when a pause happened.

``autostart_thread=False`` skips the thread so tests can drive stepping
synchronously via :meth:`_tick_now`.
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable


class SimStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class ControllerError(RuntimeError):
    """Raised on an illegal control transition (e.g. pause while IDLE)."""


class SimController:
    def __init__(
        self,
        engine_factory: Callable[[int], object],
        default_seed: int = 0,
        step_hz: float = 30.0,
        autostart_thread: bool = True,
    ) -> None:
        # engine_factory(seed) -> engine with .step()/.tick/.residual()/.snapshot()
        self._engine_factory = engine_factory
        self._default_seed = default_seed
        self._step_period = 1.0 / step_hz if step_hz > 0 else 0.0
        self._lock = threading.Lock()
        self._resume = threading.Event()  # set ⇒ thread may step
        self._shutdown = False
        self._status = SimStatus.IDLE
        self._engine = None
        self._seed = default_seed
        self._thread: threading.Thread | None = None
        if autostart_thread:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # --- control transitions -------------------------------------------------
    def start(self, seed: int | None = None) -> None:
        with self._lock:
            self._seed = self._default_seed if seed is None else seed
            self._engine = self._engine_factory(self._seed)
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
            self._engine = self._engine_factory(self._seed)  # same seed → tick 0
            self._status = SimStatus.RUNNING
        self._resume.set()

    def next_scene(self) -> None:
        """Advance a gallery engine to its next scene (explicit, user-gated).
        No-op-safe: raises if the engine has no scenes or the sim isn't started."""
        with self._lock:
            if self._engine is None:
                raise ControllerError("cannot advance scene before start")
            advance = getattr(self._engine, "next_scene", None)
            if advance is None:
                raise ControllerError("this engine has no gallery scenes")
            advance()
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
                # No engine yet (IDLE / post-stop). Emit a MODE-NEUTRAL empty
                # snapshot: only the keys both viewers tolerate. Emitting fold-only
                # keys here (fold_step/max_attn) leaked the fold schema into the eco
                # viewer and left `fold` undefined, which flashed a bogus
                # "scene undefined" toast on Stop. Empty tokens/edges render as a
                # blank scene in either viewer.
                return {"status": self._status.value, "tick": 0, "n": 0,
                        "tokens": [], "edges": []}
            return self._engine.snapshot(self._status)

    # --- stepping ------------------------------------------------------------
    def _tick_now(self) -> None:
        """One synchronous step iff RUNNING. Used by the thread and by tests."""
        with self._lock:
            if self._status == SimStatus.RUNNING and self._engine is not None:
                self._engine.step()

    def _run(self) -> None:
        while not self._shutdown:
            self._resume.wait()
            if self._shutdown:
                break
            self._tick_now()
            if self._step_period:
                time.sleep(self._step_period)
