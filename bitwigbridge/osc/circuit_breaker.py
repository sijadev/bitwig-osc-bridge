"""Circuit Breaker für OSC-Kommunikation mit Bitwig."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Callable, TypeVar

log = logging.getLogger("bitwigbridge")

T = TypeVar("T")


class State(Enum):
    CLOSED    = auto()
    OPEN      = auto()
    HALF_OPEN = auto()


class CircuitOpenError(RuntimeError):
    """Bitwig nicht erreichbar — Circuit ist offen."""


@dataclass
class CircuitBreaker:
    failure_threshold: int   = 3
    recovery_timeout:  float = 30.0

    _failures:  int   = field(default=0, init=False, repr=False)
    _opened:    float = field(default=0.0, init=False, repr=False)
    _state:     State = field(default=State.CLOSED, init=False, repr=False)

    @property
    def state(self) -> State:
        if self._state == State.OPEN:
            if time.monotonic() - self._opened >= self.recovery_timeout:
                log.info("Circuit → HALF_OPEN (recovery_timeout abgelaufen)")
                self._state = State.HALF_OPEN
        return self._state

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state  = State.OPEN
            self._opened = time.monotonic()
            log.warning("Circuit → OPEN nach %d Fehlern (threshold=%d)",
                        self._failures, self.failure_threshold)

    def _on_success(self) -> None:
        self._failures = 0
        self._state    = State.CLOSED

    def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        if self.state == State.OPEN:
            raise CircuitOpenError(
                f"Bitwig nicht erreichbar. "
                f"Automatische Erholung in {self.recovery_timeout:.0f}s."
            )
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def reset(self) -> None:
        self._failures = 0
        self._state    = State.CLOSED
        self._opened   = 0.0


_bitwig_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)


def get_circuit() -> CircuitBreaker:
    return _bitwig_circuit
