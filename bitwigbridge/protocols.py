"""
Interface-Definitionen für bitwigbridge.
Alle Interfaces sind optional — das Package funktioniert auch standalone.
"""
from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class EventEmitter(Protocol):
    """Optionaler Event-Callback — z.B. LangGraph Event Bus."""
    def emit(self, event: str, data: dict) -> None: ...


@runtime_checkable
class DrumPatternResolver(Protocol):
    """Löst write_drum_pattern Steps auf (z.B. via Neo4j oder Hardcode)."""
    def resolve(self, step: dict) -> dict: ...


@runtime_checkable
class DeviceNameResolver(Protocol):
    """Übersetzt Instrument-Namen in Bitwig-UUIDs."""
    def lookup(self, name: str) -> Optional[str]: ...


@runtime_checkable
class TrackStateProvider(Protocol):
    """Liefert Projekt-Zustand für precondition-Checks."""
    def missing_tracks_for(self, track_index: int) -> int: ...
    def apply_step(self, step: dict) -> None: ...
