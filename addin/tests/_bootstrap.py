"""Put the adsk stubs and the add-in package on sys.path, and keep test runs
out of the real add-in log.

Imported first by every test module here. The stubs directory comes first so
`import adsk.core` finds the stand-in rather than failing.
"""

import os
import sys
import tempfile
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ADDIN = os.path.join(os.path.dirname(_HERE), "FusionKeypad")

for _path in (os.path.join(_HERE, "stubs"), _ADDIN):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from lib import log  # noqa: E402

log.LOG_PATH = Path(tempfile.gettempdir()) / "FusionKeypad-tests.log"
