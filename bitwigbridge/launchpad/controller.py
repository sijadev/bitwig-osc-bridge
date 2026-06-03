"""
LaunchpadController — Klasse statt globaler State.
Steuert den Novation Launchpad MK2 über den LaunchpadAgent (Port 8003).
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Optional

log = logging.getLogger("bitwigbridge")


class LaunchpadController:
    """Steuert den Launchpad MK2 via OSC (LaunchpadAgent Extension).

    Beispiel:
        lp = LaunchpadController(host="192.168.0.4")
        lp.set_mode("drum")
        lp.suggest_notes([36, 38, 42], r=0, g=50, b=63)
        lp.arm_track(True)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int            = 8003,
        reply_port: int      = 9005,
    ) -> None:
        self.host       = host or os.getenv("BITWIG_HOST", "127.0.0.1")
        self.port       = port
        self.reply_port = reply_port
        self._mode      = "UNKNOWN"
        self._suggested_pads: list[int] = []

    def _send(self, address: str, *args) -> None:
        from pythonosc import udp_client
        try:
            udp_client.SimpleUDPClient(self.host, self.port).send_message(address, list(args) if args else 1)
        except Exception as exc:
            log.debug("Launchpad OSC send fehlgeschlagen: %s", exc)

    def _query(self, address: str, reply_address: str, timeout: float = 3.0) -> Optional[str]:
        from pythonosc import udp_client
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError: pass
        sock.settimeout(timeout)
        try:
            sock.bind(("", self.reply_port))
        except OSError:
            pass
        try:
            udp_client.SimpleUDPClient(self.host, self.port).send_message(address, 1)
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    data, _ = sock.recvfrom(512)
                    addr_end = data.find(b"\x00")
                    if addr_end < 0: continue
                    osc_addr = data[:addr_end].decode("ascii", errors="ignore")
                    if osc_addr == reply_address:
                        tag_start = (addr_end + 4) & ~3
                        if tag_start + 2 < len(data) and data[tag_start:tag_start+2] == b",s":
                            str_start = (tag_start + 4) & ~3
                            null_pos  = data.find(b"\x00", str_start)
                            return data[str_start:null_pos].decode("utf-8", errors="ignore") \
                                   if null_pos > str_start else ""
                except socket.timeout:
                    break
        except Exception:
            pass
        finally:
            try: sock.close()
            except Exception: pass
        return None

    # ── Modus ─────────────────────────────────────────────────────────────────

    def get_mode(self) -> str:
        """Aktuellen Launchpad-Modus abfragen: CONTROL | DRUM | INSTRUMENT."""
        result = self._query("/launchpad/mode/get", "/launchpad/mode/response")
        if result:
            self._mode = result
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Modus setzen: 'control' | 'drum' | 'instrument'."""
        mode_lower = mode.lower()
        if mode_lower not in ("control", "drum", "instrument"):
            raise ValueError(f"Ungültiger Modus: {mode!r}. Erlaubt: control, drum, instrument")
        self._send(f"/launchpad/mode/{mode_lower}")
        self._mode = mode_lower.upper()
        log.info("[Launchpad] Modus: %s", self._mode)

    # ── LED / Noten-Vorschläge ────────────────────────────────────────────────

    def suggest_notes(
        self,
        midi_notes: list[int],
        r: int = 0, g: int = 50, b: int = 63,
    ) -> None:
        """Hebt MIDI-Noten auf dem Launchpad visuell hervor."""
        from bitwigbridge.launchpad.profiles import midi_to_pads
        self.clear_suggestions()
        for note in midi_notes:
            for pad in midi_to_pads(note):
                self._send("/launchpad/led", pad, r, g, b)
                self._suggested_pads.append(pad)

    def clear_suggestions(self) -> None:
        """Entfernt alle Vorschlags-LEDs."""
        self._send("/launchpad/suggest/clear")
        self._suggested_pads.clear()

    def set_led(self, pad: int, r: int, g: int, b: int) -> None:
        """Einzelne LED setzen."""
        self._send("/launchpad/led", pad, r, g, b)

    # ── Noten abspielen ───────────────────────────────────────────────────────

    def play_note(
        self,
        midi_note: int,
        velocity: int   = 100,
        duration: float = 0.1,
        gap: float      = 0.05,
    ) -> None:
        """Einzelne Note spielen (Note On + Delay + Note Off)."""
        self._send("/launchpad/note/on",  midi_note, velocity)
        time.sleep(duration)
        self._send("/launchpad/note/off", midi_note)
        time.sleep(gap)

    def play_notes(self, notes: list[dict], bpm: float = 120.0) -> str:
        """Notensequenz spielen: [{note, vel, dur, gap}, ...]"""
        if not notes:
            return "Keine Noten zum Spielen."
        beat_s = 60.0 / bpm
        names  = []
        for n in notes:
            midi  = n.get("note", 60)
            vel   = min(127, max(1, int(n.get("vel", 100))))
            dur   = n.get("dur", 0.1) * beat_s
            gap   = n.get("gap", 0.05) * beat_s
            self.play_note(midi, vel, dur, gap)
            from bitwigbridge.launchpad.profiles import _DRUM_NAMES
            names.append(_DRUM_NAMES.get(midi, f"MIDI{midi}"))
        return f"[Launchpad] {len(notes)} Noten gespielt: {', '.join(names[:4])}"

    # ── Drum-Profil ───────────────────────────────────────────────────────────

    def set_drum_profile(self, plugin_name: str) -> None:
        """Drum-Note-Mapping passend zum geladenen Instrument setzen."""
        self._send("/launchpad/drum/profile", plugin_name)
        log.info("[Launchpad] Drum-Profil: %s", plugin_name)

    # ── Track-Steuerung ───────────────────────────────────────────────────────

    def arm_track(self, arm: bool = True) -> None:
        """Track armen (arm=True) oder disarmen (arm=False)."""
        self._send("/launchpad/track/arm", int(arm))

    def __repr__(self) -> str:
        return f"LaunchpadController(host={self.host!r}, port={self.port}, mode={self._mode!r})"
