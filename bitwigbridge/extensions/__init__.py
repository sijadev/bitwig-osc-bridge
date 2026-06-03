"""Bitwig Extension Installer."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

_EXTENSIONS_DIR = Path(__file__).parent


def _detect_bitwig_extensions_dir() -> Path | None:
    """Erkennt automatisch den Bitwig Extensions-Ordner."""
    system = platform.system()
    home   = Path.home()

    candidates = {
        "Windows": [
            home / "Documents" / "Bitwig Studio" / "Extensions",
            Path("C:/Users") / os.getenv("USERNAME", "") / "Documents" / "Bitwig Studio" / "Extensions",
        ],
        "Darwin": [  # macOS
            home / "Documents" / "Bitwig Studio" / "Extensions",
            home / "Music" / "Bitwig Studio" / "Extensions",
        ],
        "Linux": [
            home / "Bitwig Studio" / "Extensions",
            home / ".BitwigStudio" / "Extensions",
        ],
    }

    for path in candidates.get(system, []):
        if path.parent.exists():
            return path
    return None


def install_extensions(extensions_dir: str | Path | None = None) -> str:
    """Kopiert .bwextension Dateien in den Bitwig Extensions-Ordner.

    Args:
        extensions_dir: Zielordner (Optional — wird automatisch erkannt)

    Returns:
        Pfad wo Extensions installiert wurden.

    Raises:
        FileNotFoundError: wenn kein Bitwig Extensions-Ordner gefunden
    """
    target = Path(extensions_dir) if extensions_dir else _detect_bitwig_extensions_dir()
    if target is None:
        raise FileNotFoundError(
            "Bitwig Extensions-Ordner nicht gefunden. "
            "Bitte Pfad via extensions_dir Parameter angeben."
        )

    target.mkdir(parents=True, exist_ok=True)
    installed = []

    for ext_file in _EXTENSIONS_DIR.glob("*.bwextension"):
        dest = target / ext_file.name
        shutil.copy2(ext_file, dest)
        installed.append(ext_file.name)

    return (
        f"✓ {len(installed)} Extensions installiert → {target}\n"
        + "\n".join(f"  • {name}" for name in installed)
    )


def list_extensions() -> list[str]:
    """Gibt verfügbare .bwextension Dateien zurück."""
    return [f.name for f in _EXTENSIONS_DIR.glob("*.bwextension")]
