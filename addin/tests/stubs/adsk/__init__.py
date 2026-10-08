"""Minimal stand-in for Fusion's `adsk` package.

Only exists so the add-in can be imported, and lib/events.py and lib/link.py
tested, outside Fusion. The pure modules (registry, contexts, navigator, layout,
menu) never import adsk. This is not a simulation of Fusion: lib/fusion.py and
lib/tracker.py are thin adapters over the real API and are tested in Fusion itself.

Never shipped: it lives under tests/, not in the add-in.
"""

from . import core, fusion  # noqa: F401  (so `import adsk.core` and `import adsk.fusion` work)
