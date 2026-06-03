# bitwigbridge API Reference

## Schnellübersicht

```python
from bitwigbridge import (
    BitwigConnection,        # Verbindungsklasse
    execute_setup,           # Phase 1: Tracks/Instrumente anlegen
    compose_notes,           # Phase 2: Noten schreiben
    execute_result,          # Kombiniert Phase 1+2 (Rückwärtskompatibilität)
    LaunchpadController,     # Launchpad MK2 steuern
    install_extensions,      # Bitwig Extensions installieren
    list_extensions,         # Verfügbare Extensions auflisten
    EventEmitter,            # Interface: Event-Callbacks
    DrumPatternResolver,     # Interface: Drum-Pattern-Auflösung
    DeviceNameResolver,      # Interface: Geräte-UUID-Lookup
)
```

---

## `BitwigConnection`

Verbindung zu Bitwig Studio via BitwigStepPlugin (OSC Port 8002).

### Konstruktor

```python
BitwigConnection(
    host: str = "127.0.0.1",              # Bitwig-Rechner IP (oder BITWIG_HOST env)
    step_port: int = 8002,                 # BitwigStepPlugin Port
    step_reply_port: int = 9002,           # Reply-Port
    bridge_port: int = 8001,              # BitwigAgentBridge Port (legacy)
    bridge_reply_port: int = 9001,        # AgentBridge Reply
    timeout: float = 20.0,                # Standard-Timeout in Sekunden
    event_emitter: EventEmitter = None,   # Optional: Event-Callbacks
    device_resolver: DeviceNameResolver = None,  # Optional: UUID-Lookup
    drum_resolver: DrumPatternResolver = None,   # Optional: Drum-Pattern
    circuit: CircuitBreaker = None,       # Optional: eigener Circuit Breaker
)
```

### Methoden

| Methode | Rückgabe | Beschreibung |
|---------|----------|-------------|
| `is_connected()` | `bool` | True wenn BitwigStepPlugin antwortet |
| `get_track_count()` | `int` | Anzahl Tracks im aktuellen Projekt |
| `get_track_names()` | `list[str]` | Instrument-Namen aller Tracks |
| `clear_tracks(timeout=5.0)` | `int` | Alle Tracks löschen, gibt Anzahl zurück |
| `emit(event, data)` | `None` | Leitet Event an EventEmitter weiter |
| `resolve_device_uuid(name)` | `str\|None` | Instrument-Name → Bitwig-UUID |

### Beispiel

```python
bridge = BitwigConnection(host="192.168.0.4")

if bridge.is_connected():
    print(bridge.get_track_names())  # ["Phase-4", "FM-4"]
    print(bridge.get_track_count())  # 2
    bridge.clear_tracks()

# Mit eigenem Event-Emitter
class Logger:
    def emit(self, event, data):
        print(f"[{event}]", data)

bridge = BitwigConnection(event_emitter=Logger())
```

---

## `execute_setup()`

Phase 1: Tracks, Instrumente, FX und Tempo anlegen. **Keine Noten.**

```python
execute_setup(
    result: dict,                          # BitwigResult mit 'steps'
    connection: BitwigConnection = None,   # Optional (sonst env-Variablen)
    on_step_done: Callable = None,         # Callback nach erfolgreichem Step
    on_step_error: Callable = None,        # Callback bei Fehler
    drum_resolver: DrumPatternResolver = None,
) -> str
```

### Step-Typen

| type | args | Beschreibung |
|------|------|-------------|
| `set_tempo` | `{bpm: float}` | Tempo setzen |
| `add_track` | `{track_type: "instrument"\|"audio"\|"return"}` | Track anlegen |
| `load_instrument` | `{track_index: int, name: str}` | Instrument/VST laden |
| `append_effect` | `{track_index: int, name: str}` | FX-Kette anhängen |
| `set_param` | `{track_index: int, index: int, value: float}` | Parameter (1–8) setzen |
| `set_param_named` | `{track_index: int, param_name: str, value: float}` | Parameter via Name |
| `select_track` | `{track_index: int}` | Track auswählen |
| `clear_tracks` | `{}` | Alle Tracks löschen |

### Beispiel

```python
result = execute_setup({
    "context_type": "song",
    "target": {"bpm": 128, "genre": "techno"},
    "summary": "Techno Setup",
    "steps": [
        {"type": "set_tempo",       "args": {"bpm": 128},                         "status": "pending", "note": ""},
        {"type": "add_track",       "args": {"track_type": "instrument"},          "status": "pending", "note": "Kick"},
        {"type": "load_instrument", "args": {"track_index": 1, "name": "E-Kick"}, "status": "pending", "note": ""},
        {"type": "append_effect",   "args": {"track_index": 1, "name": "Compressor"}, "status": "pending", "note": ""},
    ]
})
# "[song] target={'bpm': 128, 'genre': 'techno'}\n✓ 4 Steps: set_tempo✓, add_track✓, ..."
```

---

## `compose_notes()`

Phase 2: Noten für **einen Track** schreiben. Mehrere Tracks → mehrere Calls.

```python
compose_notes(
    result: dict,
    connection: BitwigConnection = None,
    on_step_done: Callable = None,
    on_step_error: Callable = None,
    drum_resolver: DrumPatternResolver = None,
) -> str
```

### Note-Step

```python
{
    "type": "write_notes",
    "args": {
        "track_index": int,      # Track-Nummer (1-basiert)
        "slot": int,             # Clip-Slot (0 = erster Clip)
        "length_beats": int,     # Clip-Länge in Beats
        "notes": [
            {
                "step": float,   # Position in Beats (0.25 = 1 Sechzehntel)
                "pitch": int,    # MIDI-Note (0–127)
                "vel": float,    # Velocity (0.0–1.0)
                "dur": float,    # Dauer in Beats
            }
        ]
    },
    "status": "pending", "note": ""
}
```

### Beispiel

```python
compose_notes({
    "context_type": "track",
    "target": {"bpm": 120, "genre": "rock"},
    "track": {"index": 1, "name": "E-Kick", "instrument": "E-Kick"},
    "summary": "Kick Pattern",
    "steps": [{
        "type": "write_notes",
        "args": {
            "track_index": 1,
            "slot": 0,
            "length_beats": 4,
            "notes": [
                {"step": 0.0, "pitch": 36, "vel": 0.9, "dur": 0.25},
                {"step": 1.0, "pitch": 36, "vel": 0.85, "dur": 0.25},
                {"step": 2.0, "pitch": 36, "vel": 0.9, "dur": 0.25},
                {"step": 3.0, "pitch": 36, "vel": 0.85, "dur": 0.25},
            ]
        },
        "status": "pending", "note": ""
    }]
})
```

---

## `LaunchpadController`

Steuert den Novation Launchpad MK2 via OSC (LaunchpadAgent, Port 8003).

### Konstruktor

```python
LaunchpadController(
    host: str = "127.0.0.1",   # Bitwig-Rechner IP
    port: int = 8003,           # LaunchpadAgent Port
    reply_port: int = 9005,     # Reply-Port
)
```

### Methoden

#### Modus

| Methode | Rückgabe | Beschreibung |
|---------|----------|-------------|
| `get_mode()` | `str` | Aktueller Modus: `"CONTROL"` \| `"DRUM"` \| `"INSTRUMENT"` |
| `set_mode(mode)` | `None` | Modus setzen: `"control"` \| `"drum"` \| `"instrument"` |

#### LEDs & Noten-Vorschläge

| Methode | Rückgabe | Beschreibung |
|---------|----------|-------------|
| `suggest_notes(midi_notes, r, g, b)` | `None` | MIDI-Noten visuell hervorheben (Farbe in RGB 0–63) |
| `clear_suggestions()` | `None` | Alle Vorschlags-LEDs löschen |
| `set_led(pad, r, g, b)` | `None` | Einzelne LED setzen (pad = Launchpad Note) |

#### Noten spielen

| Methode | Rückgabe | Beschreibung |
|---------|----------|-------------|
| `play_note(midi_note, velocity, duration, gap)` | `None` | Einzelne Note (Note On + Delay + Note Off) |
| `play_notes(notes, bpm)` | `str` | Notensequenz: `[{note, vel, dur, gap}]` |

#### Drum-Profile

| Methode | Rückgabe | Beschreibung |
|---------|----------|-------------|
| `set_drum_profile(plugin_name)` | `None` | Note-Mapping anpassen: `"VD-HEAVY"` \| `"v9 Kick"` \| ... |

#### Track

| Methode | Rückgabe | Beschreibung |
|---------|----------|-------------|
| `arm_track(arm=True)` | `None` | Track armen (True) oder disarmen (False) |

### Beispiel

```python
lp = LaunchpadController(host="192.168.0.4")

# Modus
lp.set_mode("drum")
print(lp.get_mode())  # "DRUM"

# Visuelle Hervorhebung (Kick/Snare/HiHat leuchten cyan)
lp.suggest_notes([36, 38, 42], r=0, g=50, b=63)

# Noten abspielen (Kick-Pattern)
lp.play_notes([
    {"note": 36, "vel": 100, "dur": 0.1, "gap": 0.15},
    {"note": 36, "vel": 90,  "dur": 0.1, "gap": 0.15},
], bpm=120)

# Drum-Profil für VD-HEAVY (GM-Mapping)
lp.set_drum_profile("VD-HEAVY")

# Track armen
lp.arm_track(True)
```

---

## `install_extensions()`

Bitwig Extensions in den Bitwig-Ordner installieren.

```python
install_extensions(
    extensions_dir: str | Path | None = None  # Optional: eigener Pfad
) -> str  # Bestätigungs-String mit Pfad
```

Automatisch erkannte Pfade:
- **Windows**: `~/Documents/Bitwig Studio/Extensions/`
- **macOS**: `~/Documents/Bitwig Studio/Extensions/`
- **Linux**: `~/Bitwig Studio/Extensions/`

```python
from bitwigbridge.extensions import install_extensions, list_extensions

print(list_extensions())
# ['BitwigStepPlugin.bwextension', 'LaunchpadAgent.bwextension', 'BitwigOscBridge.bwextension']

print(install_extensions())
# ✓ 3 Extensions installiert → /home/user/Bitwig Studio/Extensions
#   • BitwigStepPlugin.bwextension
#   • LaunchpadAgent.bwextension
#   • BitwigOscBridge.bwextension
```

---

## Interfaces (Protocols)

Optionale Erweiterungspunkte — alle implementieren Python `Protocol`.

### `EventEmitter`

```python
class EventEmitter(Protocol):
    def emit(self, event: str, data: dict) -> None: ...
```

Events: `result_step_done`, `result_step_error`, `result_done`, `token_usage`

```python
class MyEmitter:
    def emit(self, event, data):
        print(f"[{event}]", data)

bridge = BitwigConnection(event_emitter=MyEmitter())
```

### `DrumPatternResolver`

```python
class DrumPatternResolver(Protocol):
    def resolve(self, step: dict) -> dict: ...
```

Wandelt `write_drum_pattern` Steps in `write_notes` Steps um.

```python
class SimpleDrumResolver:
    _MIDI = {"kick": 36, "snare": 38, "hihat": 42}

    def resolve(self, step: dict) -> dict:
        pattern = step["args"]["pattern"]
        notes   = []
        for drum, hits in pattern.items():
            pitch = self._MIDI.get(drum, 36)
            for i, hit in enumerate(hits):
                if hit:
                    notes.append({"step": i * 0.25, "pitch": pitch, "vel": 0.85, "dur": 0.25})
        return {**step, "type": "write_notes",
                "args": {**step["args"], "notes": notes}}

bridge = BitwigConnection(drum_resolver=SimpleDrumResolver())
```

### `DeviceNameResolver`

```python
class DeviceNameResolver(Protocol):
    def lookup(self, name: str) -> Optional[str]: ...
```

Übersetzt Instrument-Namen in Bitwig-UUIDs für schnelleres Laden.

```python
MY_UUIDS = {"my-synth": "a1b2c3d4-..."}

class MyResolver:
    def lookup(self, name):
        return MY_UUIDS.get(name.lower())

bridge = BitwigConnection(device_resolver=MyResolver())
```

---

## `CircuitBreaker`

Schützt OSC-Verbindung vor Kaskadenfehler bei Bitwig-Ausfall.

```python
from bitwigbridge.osc.circuit_breaker import CircuitBreaker, get_circuit

cb = get_circuit()         # Singleton
cb.state                   # State.CLOSED | State.OPEN | State.HALF_OPEN
cb.reset()                 # Manuell zurücksetzen
cb.call(fn, *args)         # Funktion mit Circuit Breaker ausführen

# Eigener Circuit Breaker
bridge = BitwigConnection(
    circuit=CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
)
```

---

## OSC-Ports Übersicht

| Port | Protokoll | Extension | Beschreibung |
|------|-----------|-----------|-------------|
| **8002** | UDP → | BitwigStepPlugin | Haupt-Port: Tracks, Noten, Steps |
| **9002** | UDP ← | BitwigStepPlugin | Reply-Port |
| **8003** | UDP → | LaunchpadAgent | LED-Steuerung, Modus |
| **9005** | UDP ← | LaunchpadAgent | Reply-Port |
| 8001 | UDP → | BitwigOscBridge | Transport/Mixer (legacy) |
| 9001 | UDP ← | BitwigOscBridge | Reply-Port (legacy) |

---

## OSC-Endpunkte (BitwigStepPlugin)

| Adresse | Args | Response | Beschreibung |
|---------|------|----------|-------------|
| `/ping` | — | `/pong 1` | Health Check |
| `/step/exec` | JSON-String | `/step/done <status>` | Step ausführen |
| `/agent/track/count` | — | `/agent/track/count/response int string` | Track-Anzahl + Namen |
| `/agent/tracks/clear` | — | `/agent/tracks/clear/response int` | Alle Tracks löschen |
| `/clip/note/count/all` | — | `/clip/note/count/response int string` | Noten-Counter |
| `/clip/note/count/reset` | — | — | Counter zurücksetzen |
| `/devices/export` | — | `/devices/export/response JSON` | Built-in UUID-Map |
| `/plugins/scan` | — | `/plugins/scan/response string` | VST3-Plugins scannen |

### Step-Status-Codes (`/step/done`)

| Code | Bedeutung |
|------|-----------|
| `set_tempo` | Tempo gesetzt |
| `add_track` | Track angelegt |
| `load_instrument` | Instrument geladen |
| `write_notes` | Noten geschrieben |
| `clear_tracks` | Tracks gelöscht |
| `error:unknown:<type>` | Unbekannter Step-Typ |
| `error:browser_timeout:<name>` | Browser-Navigation Timeout |
| `error:load_instrument:not_found:<name>` | Instrument nicht gefunden |
| `error:precondition:track_not_found:<n>` | Track existiert nicht |

---

## OSC-Endpunkte (LaunchpadAgent)

| Adresse | Args | Beschreibung |
|---------|------|-------------|
| `/launchpad/mode/get` | — | Modus abfragen → `/launchpad/mode/response` |
| `/launchpad/mode/control` | — | CONTROL-Modus |
| `/launchpad/mode/drum` | — | DRUM-Modus |
| `/launchpad/mode/instrument` | — | INSTRUMENT-Modus |
| `/launchpad/led` | pad r g b | LED setzen (RGB 0–63) |
| `/launchpad/suggest/clear` | — | Alle Suggestion-LEDs löschen |
| `/launchpad/note/on` | note vel | Note starten |
| `/launchpad/note/off` | note | Note beenden |
| `/launchpad/drum/profile` | name | Drum-Mapping ändern |
| `/launchpad/track/arm` | 1\|0 | Track armen/disarmen |

### Launchpad Pad-Noten (DRUM-Modus, 4×4 Grid)

```
Row 4 (top): 41  42  43  44   →  MIDI 48–51
Row 3:       31  32  33  34   →  MIDI 44–47
Row 2:       21  22  23  24   →  MIDI 40–43
Row 1 (bot): 11  12  13  14   →  MIDI 36–39
                                  (GM: Kick, Rim, Snare, Clap)
```

---

## Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `BITWIG_HOST` | `127.0.0.1` | IP des Bitwig-Rechners |
| `BITWIG_STEP_PORT` | `8002` | BitwigStepPlugin Port |
| `BITWIG_STEP_REPLY_PORT` | `9002` | StepPlugin Reply-Port |
| `BITWIG_PORT` | `8001` | BitwigOscBridge Port (legacy) |
| `BITWIG_REPLY_PORT` | `9001` | OscBridge Reply (legacy) |

```bash
# .env Datei (wird automatisch geladen)
BITWIG_HOST=192.168.0.4
BITWIG_STEP_PORT=8002
```
