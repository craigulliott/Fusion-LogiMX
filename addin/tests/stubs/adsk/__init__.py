"""Minimal stand-in for Fusion's `adsk` package.

Only exists so lib/events.py and lib/link.py can be imported and tested outside
Fusion. The pure modules (registry, contexts, navigator, layout) never import
adsk. This is not a simulation of Fusion: lib/fusion.py and lib/tracker.py are
thin adapters over the real API and are tested in Fusion itself.

Never shipped: it lives under tests/, not in the add-in.
"""

from . import core  # noqa: F401  (so `import adsk.core` works)
