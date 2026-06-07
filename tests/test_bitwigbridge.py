"""Smoke- und Logik-Tests für das bitwigbridge-Paket.

Reine Python-Tests ohne laufendes Bitwig — prüfen Paket-Integrität,
die CircuitBreaker-State-Machine und die Executor-Typkonstanten.
"""
from __future__ import annotations

import pytest


# ── Import-Smoke ─────────────────────────────────────────────────────────────

def test_package_public_api_importable():
    import bitwigbridge

    for name in bitwigbridge.__all__:
        assert hasattr(bitwigbridge, name), f"{name} fehlt im Paket-Namespace"


def test_executor_reexports_importable():
    from bitwigbridge.executor import (
        execute_setup, compose_notes, execute_result,
        _SETUP_TYPES, _NOTE_TYPES, _exec_step_and_wait,
    )

    assert callable(execute_setup)
    assert callable(compose_notes)
    assert callable(execute_result)
    assert callable(_exec_step_and_wait)


def test_connection_importable():
    from bitwigbridge.connection import BitwigConnection

    assert BitwigConnection is not None


# ── Executor-Typkonstanten ───────────────────────────────────────────────────

def test_setup_and_note_types_are_disjoint_sets():
    from bitwigbridge.executor import _SETUP_TYPES, _NOTE_TYPES

    assert isinstance(_SETUP_TYPES, set)
    assert isinstance(_NOTE_TYPES, set)
    assert _SETUP_TYPES.isdisjoint(_NOTE_TYPES)


def test_known_step_types_present():
    from bitwigbridge.executor import _SETUP_TYPES, _NOTE_TYPES

    assert {"set_tempo", "add_track", "load_instrument"} <= _SETUP_TYPES
    assert {"set_send", "setup_drum_machine"} <= _SETUP_TYPES
    assert {"write_notes", "write_drum_pattern"} <= _NOTE_TYPES


# ── CircuitBreaker-State-Machine ─────────────────────────────────────────────

def test_circuit_starts_closed_and_passes_calls_through():
    from bitwigbridge.osc.circuit_breaker import CircuitBreaker, State

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    assert cb.state == State.CLOSED
    assert cb.call(lambda: 42) == 42
    assert cb.state == State.CLOSED


def test_circuit_opens_after_threshold_failures():
    from bitwigbridge.osc.circuit_breaker import CircuitBreaker, State

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

    def boom():
        raise ValueError("fail")

    for _ in range(3):
        with pytest.raises(ValueError):
            cb.call(boom)

    assert cb.state == State.OPEN


def test_open_circuit_rejects_calls_fast():
    from bitwigbridge.osc.circuit_breaker import (
        CircuitBreaker, CircuitOpenError,
    )

    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))

    with pytest.raises(CircuitOpenError):
        cb.call(lambda: 1)


def test_circuit_transitions_to_half_open_after_timeout():
    from bitwigbridge.osc.circuit_breaker import CircuitBreaker, State

    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))

    # recovery_timeout=0 → sofort HALF_OPEN beim nächsten state-Read
    assert cb.state == State.HALF_OPEN


def test_success_resets_failures_and_closes():
    from bitwigbridge.osc.circuit_breaker import CircuitBreaker, State

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

    def boom():
        raise ValueError("fail")

    for _ in range(2):  # noch unter Threshold
        with pytest.raises(ValueError):
            cb.call(boom)

    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == State.CLOSED

    # nach Reset der Failures braucht es wieder volle threshold-Fehler
    with pytest.raises(ValueError):
        cb.call(boom)
    assert cb.state == State.CLOSED


def test_reset_returns_to_closed():
    from bitwigbridge.osc.circuit_breaker import CircuitBreaker, State

    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    assert cb.state == State.OPEN

    cb.reset()
    assert cb.state == State.CLOSED


def test_get_circuit_returns_singleton():
    from bitwigbridge.osc.circuit_breaker import get_circuit

    assert get_circuit() is get_circuit()
