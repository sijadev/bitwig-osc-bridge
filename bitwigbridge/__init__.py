"""
bitwigbridge — Bitwig Studio OSC Bridge

Standalone Python-Package zur Steuerung von Bitwig Studio via OSC.
Kompatibel mit jedem Python-Framework — kein LangChain/Agent nötig.

Schnellstart:
    from bitwigbridge import BitwigConnection, execute_setup
    from bitwigbridge.extensions import install_extensions

    # Extensions einmalig installieren
    install_extensions()

    # Verbindung herstellen
    bridge = BitwigConnection(host="127.0.0.1")
    if bridge.is_connected():
        execute_setup(bridge, {
            "steps": [
                {"type": "add_track",      "args": {"track_type": "instrument"}},
                {"type": "load_instrument","args": {"track_index": 1, "name": "Phase-4"}},
            ]
        })
"""
__version__ = "0.1.0"

from bitwigbridge.connection import BitwigConnection
from bitwigbridge.executor import execute_setup, compose_notes, execute_result
from bitwigbridge.launchpad.controller import LaunchpadController
from bitwigbridge.extensions import install_extensions, list_extensions
from bitwigbridge.protocols import EventEmitter, DrumPatternResolver, DeviceNameResolver

__all__ = [
    "BitwigConnection",
    "execute_setup",
    "compose_notes",
    "execute_result",
    "LaunchpadController",
    "install_extensions",
    "list_extensions",
    "EventEmitter",
    "DrumPatternResolver",
    "DeviceNameResolver",
]
