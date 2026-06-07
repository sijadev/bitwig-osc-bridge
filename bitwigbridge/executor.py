"""
Bitwig Step-Executor — entkoppelt, kein Agent/Neo4j nötig.

Zwei-Phasen-Workflow:
  Phase 1: execute_setup()  — Tracks, Instrumente, FX, Tempo
  Phase 2: compose_notes()  — Noten für EINEN Track pro Call

Entkopplungs-Interfaces (alle optional):
  - on_step_done: Callback nach jedem erfolgreichen Step
  - on_step_error: Callback bei Step-Fehlern
  - drum_resolver: Löst write_drum_pattern auf (DrumPatternResolver Protocol)
  - connection: BitwigConnection Objekt (alternativ zu env-Variablen)
"""
from __future__ import annotations

import json as _json
import os
import socket as _socket
import threading
import time
from typing import Callable, Optional

from dotenv import load_dotenv
load_dotenv()

from bitwigbridge.protocols import DrumPatternResolver

_SETUP_TYPES = {"set_tempo", "add_track", "load_instrument", "append_effect",
                "set_param", "set_param_named", "set_send", "setup_drum_machine",
                "select_track", "clear_tracks"}
_NOTE_TYPES  = {"write_notes", "write_drum_pattern"}


def _exec_step_and_wait(
    client,
    step_json: str,
    reply_port: int,
    timeout: float = 12.0,
) -> str:
    received = threading.Event()
    reply    = ["error:timeout"]

    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    if hasattr(_socket, "SO_REUSEPORT"):
        try: sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEPORT, 1)
        except OSError: pass
    sock.settimeout(timeout)
    try:
        sock.bind(("", reply_port))
    except OSError:
        sock.close()
        client.send_message("/step/exec", step_json)
        time.sleep(min(timeout, 0.5))
        return "ok:fallback"

    def _listen():
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, _ = sock.recvfrom(4096)
                addr_end = data.find(b"\x00")
                if addr_end < 0: continue
                osc_addr = data[:addr_end].decode("ascii", errors="ignore")
                if osc_addr == "/step/done":
                    tag_start = (addr_end + 4) & ~3
                    if tag_start + 2 < len(data) and data[tag_start:tag_start+2] == b",s":
                        str_start = (tag_start + 4) & ~3
                        null_pos  = data.find(b"\x00", str_start)
                        reply[0]  = data[str_start:null_pos].decode("utf-8", errors="ignore") \
                                    if null_pos > str_start else "ok"
                    else:
                        reply[0] = "ok"
                    received.set()
                    return
            except (_socket.timeout, OSError):
                break

    threading.Thread(target=_listen, daemon=True).start()
    client.send_message("/step/exec", step_json)
    received.wait(timeout)

    try: sock.close()
    except Exception: pass
    return reply[0]


def _execute_steps(
    result: dict,
    host: str,
    step_port: int,
    reply_port: int,
    phase: str = "all",
    on_step_done: Optional[Callable[[dict], None]] = None,
    on_step_error: Optional[Callable[[dict], None]] = None,
    drum_resolver: Optional[DrumPatternResolver] = None,
) -> str:
    from pythonosc import udp_client as _udp
    from bitwigbridge.osc.device_uuid import _lookup_device_uuid

    steps   = result.get("steps", [])
    done_log: list[str] = []
    errors:   list[str] = []

    setup_steps = [s for s in steps if s.get("type", "") in _SETUP_TYPES]
    note_steps  = [s for s in steps if s.get("type", "") in _NOTE_TYPES]
    other_steps = [s for s in steps if s.get("type", "") not in _SETUP_TYPES | _NOTE_TYPES]

    if phase == "setup":
        ordered = setup_steps + other_steps
    elif phase == "notes":
        ordered = note_steps
    else:
        ordered = setup_steps + note_steps + other_steps

    client = _udp.SimpleUDPClient(host, step_port)

    for step in ordered:
        stype = step.get("type", "")
        args  = step.get("args", {}) or {}

        # write_drum_pattern auflösen
        if stype == "write_drum_pattern":
            if drum_resolver is not None:
                try:
                    step  = drum_resolver.resolve(step)
                    stype = "write_notes"
                    args  = step.get("args", {})
                except Exception as exc:
                    errors.append(f"write_drum_pattern resolve: {exc}")
                    if on_step_error:
                        on_step_error({"type": stype, "error": str(exc)})
                    continue
            else:
                errors.append("write_drum_pattern: kein DrumPatternResolver gesetzt")
                continue

        # UUID-Auflösung für load_instrument
        if stype in ("load_instrument", "append_effect") and "uuid" not in args:
            device_name = args.get("name", "")
            if device_name:
                uuid = _lookup_device_uuid(device_name)
                if uuid:
                    args = {**args, "uuid": uuid}

        # VST-Laden: längeres Timeout
        is_vst = stype in ("load_instrument", "append_effect") and not args.get("uuid")
        step_timeout = 20.0 if is_vst else 12.0

        step_json = _json.dumps({"type": stype, "args": args})
        reply     = _exec_step_and_wait(client, step_json, reply_port, timeout=step_timeout)

        # Einmaliger Retry bei browser_timeout
        if reply.startswith("error:browser_timeout:") and stype == "load_instrument":
            reply = _exec_step_and_wait(client, step_json, reply_port, timeout=step_timeout)

        ok  = not reply.startswith("error:")
        tag = f"{stype}✓" if ok else f"{stype}✗({reply})"
        (done_log if ok else errors).append(tag)

        payload = {"type": stype, "args": args, "error": reply if not ok else ""}
        if ok and on_step_done:
            on_step_done(payload)
        elif not ok and on_step_error:
            on_step_error(payload)

    context_type = result.get("context_type", "?")
    target       = result.get("target", {})
    status       = f"[{context_type}] target={target}\n"
    if done_log:
        status += f"✓ {len(done_log)} Steps: {', '.join(done_log)}"
    if errors:
        status += f"\n✗ Fehler: {', '.join(errors)}"
    return status


def execute_setup(
    result: dict,
    connection=None,
    on_step_done: Optional[Callable] = None,
    on_step_error: Optional[Callable] = None,
    drum_resolver: Optional[DrumPatternResolver] = None,
) -> str:
    """Phase 1: Tracks, Instrumente, FX, Tempo anlegen. Keine Noten.

    Args:
        result: BitwigResult-Dict mit 'steps', 'context_type', 'target'
        connection: BitwigConnection (optional, sonst env-Variablen)
        on_step_done: Callback nach jedem erfolgreichen Step
        on_step_error: Callback bei Step-Fehlern
        drum_resolver: Drum-Pattern-Resolver (DrumPatternResolver Protocol)
    """
    note_steps = [s for s in result.get("steps", []) if s.get("type", "") in _NOTE_TYPES]
    if note_steps:
        types = ", ".join(s["type"] for s in note_steps)
        return f"[execute_setup] Noten-Steps nicht erlaubt: {types} — compose_notes verwenden."

    host       = getattr(connection, "host",            None) or os.getenv("BITWIG_HOST", "127.0.0.1")
    step_port  = getattr(connection, "step_port",       None) or int(os.getenv("BITWIG_STEP_PORT", "8002"))
    reply_port = getattr(connection, "step_reply_port", None) or int(os.getenv("BITWIG_STEP_REPLY_PORT", "9002"))

    dr = drum_resolver or (connection.drum_resolver if connection else None)

    return _execute_steps(result, host, step_port, reply_port,
                          phase="setup",
                          on_step_done=on_step_done,
                          on_step_error=on_step_error,
                          drum_resolver=dr)


def compose_notes(
    result: dict,
    connection=None,
    on_step_done: Optional[Callable] = None,
    on_step_error: Optional[Callable] = None,
    drum_resolver: Optional[DrumPatternResolver] = None,
) -> str:
    """Phase 2: Noten für EINEN Track schreiben.

    Mehrere Tracks → mehrere compose_notes-Calls.
    """
    setup_steps = [s for s in result.get("steps", []) if s.get("type", "") in _SETUP_TYPES]
    if setup_steps:
        return "[compose_notes] Setup-Steps nicht erlaubt — execute_setup zuerst."

    host       = getattr(connection, "host",            None) or os.getenv("BITWIG_HOST", "127.0.0.1")
    step_port  = getattr(connection, "step_port",       None) or int(os.getenv("BITWIG_STEP_PORT", "8002"))
    reply_port = getattr(connection, "step_reply_port", None) or int(os.getenv("BITWIG_STEP_REPLY_PORT", "9002"))

    dr = drum_resolver or (connection.drum_resolver if connection else None)

    return _execute_steps(result, host, step_port, reply_port,
                          phase="notes",
                          on_step_done=on_step_done,
                          on_step_error=on_step_error,
                          drum_resolver=dr)


def execute_result(result: dict, connection=None, **kwargs) -> str:
    """Rückwärtskompatibel: Setup + Noten in einem Call."""
    host       = getattr(connection, "host",            None) or os.getenv("BITWIG_HOST", "127.0.0.1")
    step_port  = getattr(connection, "step_port",       None) or int(os.getenv("BITWIG_STEP_PORT", "8002"))
    reply_port = getattr(connection, "step_reply_port", None) or int(os.getenv("BITWIG_STEP_REPLY_PORT", "9002"))
    return _execute_steps(result, host, step_port, reply_port, phase="all", **kwargs)
