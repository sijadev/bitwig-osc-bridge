"""Launchpad Pad-Mapping und Drum-Noten-Namen."""
from __future__ import annotations

_DRUM_NAMES: dict[int, str] = {
    36: "Kick", 37: "Rimshot", 38: "Snare", 39: "Clap",
    40: "E-Snare", 41: "Low Tom", 42: "HH closed", 43: "High Tom",
    44: "Pedal HH", 45: "Low-Mid Tom", 46: "Open HH", 47: "Mid Tom",
    48: "Hi-Mid Tom", 49: "Crash", 50: "High Tom", 51: "Ride",
}

# MIDI note → Launchpad pad note (DRUM mode 4×4 grid)
_DRUM_NOTE_TO_PAD: dict[int, int] = {
    36: 11, 37: 12, 38: 13, 39: 14,
    40: 21, 41: 22, 42: 23, 43: 24,
    44: 31, 45: 32, 46: 33, 47: 34,
    48: 41, 49: 42, 50: 43, 51: 44,
}

# MIDI note → Launchpad pad note (INSTRUMENT mode 8×8 chromatic)
_INST_ROOT_NOTE    = 48  # C3
_INST_ROW_INTERVAL = 5   # Perfect Fourth
_INST_SCALE        = [0, 2, 4, 5, 7, 9, 11]  # Major


def midi_to_pads(midi_note: int, mode: str = "drum") -> list[int]:
    """Gibt Launchpad-Pad-Noten für eine MIDI-Note zurück."""
    if mode == "drum":
        pad = _DRUM_NOTE_TO_PAD.get(midi_note)
        return [pad] if pad else []
    # Instrument-Modus: alle Pads die diese Note produzieren würden
    pads = []
    for row in range(1, 9):
        for col in range(1, 9):
            base       = _INST_ROOT_NOTE + (row - 1) * _INST_ROW_INTERVAL
            scale_step = (col - 1) % len(_INST_SCALE)
            octave     = (col - 1) // len(_INST_SCALE)
            note       = base + _INST_SCALE[scale_step] + octave * 12
            if note == midi_note:
                pads.append(row * 10 + col)
    return pads
