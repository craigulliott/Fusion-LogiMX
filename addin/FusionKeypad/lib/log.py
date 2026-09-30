"""Append-only add-in log. Safe from any thread: it never touches the API."""

import sys
import tempfile
import threading
import time
from pathlib import Path

_LOG_DIR = Path.home() / "Library" / "Logs" if sys.platform == "darwin" else Path(tempfile.gettempdir())
LOG_PATH = _LOG_DIR / "FusionKeypad-addin.log"

_lock = threading.Lock()


def log(kind: str, text: str = "") -> None:
    now = time.time()
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)) + f".{int(now * 1000) % 1000:03d}"
    line = f"{stamp} {kind:<6} {text}".rstrip()
    try:
        with _lock, LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # a missing log must never break Fusion
