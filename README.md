# bitwigbridge

Python package to control **Bitwig Studio** via OSC — standalone, no AI agent required.

## Installation

```bash
pip install bitwigbridge
```

## Setup (einmalig)

```bash
# Bitwig Extensions in Bitwig installieren
bitwigbridge-install
# oder: python -c "from bitwigbridge.extensions import install_extensions; install_extensions()"
```

Danach in Bitwig: **Settings → Controllers → Add Controller → Bitwig Agent → BitwigStepPlugin** aktivieren.

## Schnellstart

```python
from bitwigbridge import BitwigConnection, execute_setup
from bitwigbridge.launchpad.controller import LaunchpadController

# Verbindung
bridge = BitwigConnection(host="127.0.0.1")
print(bridge.is_connected())  # True

# Track anlegen + Instrument laden
execute_setup(bridge, {
    "steps": [
        {"type": "add_track",       "args": {"track_type": "instrument"}},
        {"type": "load_instrument", "args": {"track_index": 1, "name": "Phase-4"}},
        {"type": "set_tempo",       "args": {"bpm": 128}},
    ]
})

# Noten schreiben
from bitwigbridge.executor import compose_notes
compose_notes(bridge, {
    "steps": [{
        "type": "write_notes",
        "args": {
            "track_index": 1,
            "slot": 0,
            "length_beats": 4,
            "notes": [
                {"step": 0.0, "pitch": 60, "vel": 0.8, "dur": 0.5},
                {"step": 1.0, "pitch": 64, "vel": 0.7, "dur": 0.5},
            ]
        }
    }]
})

# Launchpad steuern
lp = LaunchpadController(host="127.0.0.1")
lp.set_mode("drum")
lp.suggest_notes([36, 38, 42])  # Kick, Snare, HiHat leuchten auf
```

## Mit LangChain/LangGraph

```bash
pip install bitwigbridge[langchain]
```

```python
from bitwigbridge.langchain_tools import execute_setup, compose_notes
# @tool-dekorierte Versionen für LangGraph
```

## Interfaces (für eigene Erweiterungen)

```python
from bitwigbridge.protocols import EventEmitter, DrumPatternResolver, DeviceNameResolver

# Eigener Event-Emitter (z.B. für Logging)
class MyEmitter:
    def emit(self, event: str, data: dict) -> None:
        print(f"[{event}]", data)

bridge = BitwigConnection(event_emitter=MyEmitter())

# Eigener Drum-Pattern-Resolver (z.B. via Datenbank)
class MyDrumResolver:
    def resolve(self, step: dict) -> dict:
        # step["args"]["pattern"] → step["args"]["notes"]
        return step

bridge = BitwigConnection(drum_resolver=MyDrumResolver())
```

## Ports

| Port | Richtung | Beschreibung |
|------|----------|-------------|
| 8002 | → Bitwig | BitwigStepPlugin (Haupt-Port) |
| 9002 | ← Bitwig | StepPlugin Reply |
| 8003 | → Bitwig | LaunchpadAgent (LEDs, Modus) |
| 9005 | ← Bitwig | Launchpad Reply |

## Environment Variables

```bash
BITWIG_HOST=127.0.0.1          # Bitwig-Rechner IP
BITWIG_STEP_PORT=8002           # BitwigStepPlugin Port
BITWIG_STEP_REPLY_PORT=9002     # Reply Port
```
