"""
BitwigConnection — zentrale Verbindungsklasse zu Bitwig Studio via OSC.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from bitwigbridge.protocols import DeviceNameResolver, EventEmitter, DrumPatternResolver
from bitwigbridge.osc.circuit_breaker import CircuitBreaker, get_circuit

log = logging.getLogger("bitwigbridge")


class BitwigConnection:
    """Verbindung zu Bitwig Studio via BitwigStepPlugin (OSC Port 8002).

    Beispiel (standalone):
        bridge = BitwigConnection(host="192.168.0.4")
        if bridge.is_connected():
            print(bridge.get_track_names())

    Beispiel (mit Agent-Integration):
        bridge = BitwigConnection(
            host="192.168.0.4",
            event_emitter=get_event_bus(),          # optional
            device_resolver=DrumPatternRepository(), # optional
        )
    """

    def __init__(
        self,
        host: Optional[str]                        = None,
        step_port: int                             = 8002,
        step_reply_port: int                       = 9002,
        bridge_port: int                           = 8001,
        bridge_reply_port: int                     = 9001,
        timeout: float                             = 20.0,
        event_emitter: Optional[EventEmitter]      = None,
        device_resolver: Optional[DeviceNameResolver] = None,
        drum_resolver: Optional[DrumPatternResolver]  = None,
        circuit: Optional[CircuitBreaker]          = None,
    ) -> None:
        self.host              = host or os.getenv("BITWIG_HOST", "127.0.0.1")
        self.step_port         = step_port
        self.step_reply_port   = step_reply_port
        self.bridge_port       = bridge_port
        self.bridge_reply_port = bridge_reply_port
        self.timeout           = timeout
        self.event_emitter     = event_emitter
        self.device_resolver   = device_resolver
        self.drum_resolver     = drum_resolver
        self.circuit           = circuit or get_circuit()

    # ── Connectivity ──────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        """True wenn BitwigStepPlugin auf step_port antwortet."""
        import socket
        from pythonosc import udp_client
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError: pass
        sock.settimeout(2.0)
        try:
            sock.bind(("", self.step_reply_port))
        except OSError:
            pass
        try:
            udp_client.SimpleUDPClient(self.host, self.step_port).send_message("/ping", 1)
            sock.recvfrom(64)
            return True
        except (socket.timeout, OSError):
            return False
        finally:
            try: sock.close()
            except Exception: pass

    # ── Track State ───────────────────────────────────────────────────────────

    def get_track_count(self) -> int:
        from bitwigbridge.osc.track_state import _get_current_track_count as _fn
        # Temporär Host/Port setzen
        import bitwigbridge.osc.track_state as ts
        _orig_host, _orig_port, _orig_reply = ts.OSC_HOST, ts.OSC_STEP_PORT, ts.OSC_STEP_REPLY_PORT
        ts.OSC_HOST, ts.OSC_STEP_PORT, ts.OSC_STEP_REPLY_PORT = self.host, self.step_port, self.step_reply_port
        try:
            return _fn()
        finally:
            ts.OSC_HOST, ts.OSC_STEP_PORT, ts.OSC_STEP_REPLY_PORT = _orig_host, _orig_port, _orig_reply

    def get_track_names(self) -> list[str]:
        from bitwigbridge.osc.track_state import _get_track_names as _fn
        import bitwigbridge.osc.track_state as ts
        _orig = ts.OSC_HOST, ts.OSC_STEP_PORT, ts.OSC_STEP_REPLY_PORT
        ts.OSC_HOST, ts.OSC_STEP_PORT, ts.OSC_STEP_REPLY_PORT = self.host, self.step_port, self.step_reply_port
        try:
            return _fn()
        finally:
            ts.OSC_HOST, ts.OSC_STEP_PORT, ts.OSC_STEP_REPLY_PORT = _orig

    def clear_tracks(self, timeout: float = 5.0) -> int:
        from bitwigbridge.osc.track_state import _clear_all_tracks as _fn
        import bitwigbridge.osc.track_state as ts
        _orig = ts.OSC_HOST, ts.OSC_PORT, ts.OSC_REPLY_PORT
        ts.OSC_HOST, ts.OSC_PORT, ts.OSC_REPLY_PORT = self.host, self.step_port, self.step_reply_port
        try:
            return _fn(timeout=timeout)
        finally:
            ts.OSC_HOST, ts.OSC_PORT, ts.OSC_REPLY_PORT = _orig

    # ── Event Emission (optional) ─────────────────────────────────────────────

    def emit(self, event: str, data: dict) -> None:
        """Leitet Events an optionalen EventEmitter weiter."""
        if self.event_emitter is not None:
            try:
                self.event_emitter.emit(event, data)
            except Exception as exc:
                log.debug("EventEmitter.emit fehlgeschlagen: %s", exc)

    # ── Device Name → UUID ────────────────────────────────────────────────────

    def resolve_device_uuid(self, name: str) -> str | None:
        """UUID via eigenem Resolver oder Built-in Lookup."""
        if self.device_resolver is not None:
            result = self.device_resolver.lookup(name)
            if result:
                return result
        # Fallback: Built-in UUID-Lookup
        from bitwigbridge.osc.device_uuid import _lookup_device_uuid
        return _lookup_device_uuid(name)

    def __repr__(self) -> str:
        return f"BitwigConnection(host={self.host!r}, step_port={self.step_port})"
