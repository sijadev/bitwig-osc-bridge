"""
LangChain/LangGraph Tool-Wrapper für bitwigbridge.
Nur verfügbar mit: pip install bitwigbridge[langchain]
"""
from __future__ import annotations

try:
    from langchain_core.tools import tool as _tool
except ImportError as exc:
    raise ImportError(
        "LangChain nicht installiert. "
        "Bitte: pip install bitwigbridge[langchain]"
    ) from exc

from bitwigbridge.executor import execute_setup as _execute_setup
from bitwigbridge.executor import compose_notes as _compose_notes


@_tool
def execute_setup(result: dict) -> str:
    """Phase 1: Tracks, Instrumente, FX, Tempo anlegen. Keine Noten.

    Verwendet BITWIG_HOST env-Variable für Verbindung.
    """
    return _execute_setup(result)


@_tool
def compose_notes(result: dict) -> str:
    """Phase 2: Noten für EINEN Track schreiben.

    Mehrere Tracks → mehrere compose_notes-Calls.
    Verwendet BITWIG_HOST env-Variable für Verbindung.
    """
    return _compose_notes(result)
