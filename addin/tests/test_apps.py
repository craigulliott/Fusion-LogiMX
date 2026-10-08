"""apps — what apps are told: the definition and the state."""

import unittest

import _bootstrap  # noqa: F401

from FusionKeypad.lib import apps
from FusionKeypad.lib.registry import Context, Registry, Root, Tool

LINE = Tool("L", "Line")
CIRCLE = Context("Circle", default="C1", items=[Tool("C1", "Center"), Tool("C2", "2-Point")])
TOP = Context("Top", items=[LINE, CIRCLE])
REGISTRY = Registry([Root(TOP, when=lambda fusion: True)])


class FakeFusion:
    """Knows the names of a few commands; each has an icon folder named after it."""

    NAMES = {"L": "Line", "C1": "Center Circle", "C2": "2-Point Circle", "M": "Mark"}

    def command_name(self, command):
        return self.NAMES.get(command)

    def icon_folder(self, command):
        return f"/fusion/{command}" if command in self.NAMES else None


class DefinitionTest(unittest.TestCase):
    def test_is_every_root_s_contexts_and_tools_in_keypad_order(self):
        self.assertEqual(apps.definition(REGISTRY, FakeFusion()), {"type": "definition", "roots": [{
            "id": "Top", "name": "Top", "default": None, "icons": None, "items": [
                {"command": "L", "label": "Line", "name": "Line", "icons": "/fusion/L"},
                {"id": "Top/Circle", "name": "Circle", "default": "C1", "icons": "/fusion/C1", "items": [
                    {"command": "C1", "label": "Center", "name": "Center Circle", "icons": "/fusion/C1"},
                    {"command": "C2", "label": "2-Point", "name": "2-Point Circle", "icons": "/fusion/C2"},
                ]},
            ],
        }]})

    def test_fusion_s_name_and_artwork_are_null_where_it_has_none(self):
        marked = Tool("M", "Mark", icon="mark.png")  # an icon file of the add-in's own
        unknown = Tool("Gone", "Gone")  # a command this Fusion build doesn't have
        registry = Registry([Root(Context("Top", items=[marked, unknown]), when=lambda fusion: True)])
        self.assertEqual(apps.definition(registry, FakeFusion())["roots"][0]["items"], [
            {"command": "M", "label": "Mark", "name": "Mark", "icons": None},
            {"command": "Gone", "label": "Gone", "name": None, "icons": None},
        ])


class StateTest(unittest.TestCase):
    def test_names_the_current_context_by_its_path_and_the_running_tool(self):
        self.assertEqual(
            apps.state(CIRCLE, "C2", REGISTRY),
            {"type": "state", "context": "Top/Circle", "running": "C2"},
        )

    def test_has_no_context_where_the_keypad_is_blank(self):
        self.assertEqual(apps.state(None, None, REGISTRY), {"type": "state", "context": None, "running": None})


if __name__ == "__main__":
    unittest.main()
