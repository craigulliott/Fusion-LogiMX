"""Make the add-in importable the way Fusion imports it, and keep test runs out
of the real add-in log.

Imported first by every test module here. The stubs directory comes first so
`import adsk.core` finds the stand-in rather than failing. Fusion loads the
add-in folder as a package, so tests import `FusionKeypad.lib…` too.
"""

import os
import sys
import tempfile
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ADDIN_ROOT = os.path.dirname(_HERE)  # the folder that contains FusionKeypad/

for _path in (os.path.join(_HERE, "stubs"), _ADDIN_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from FusionKeypad.lib import log  # noqa: E402

log.LOG_PATH = Path(tempfile.gettempdir()) / "FusionKeypad-tests.log"
