"""menu.choices — the commands the MCP server offers by name, nearest first."""

import unittest

import _bootstrap  # noqa: F401

from FusionKeypad.lib.menu import Choice, choices
from FusionKeypad.lib.registry import Context, Registry, Root, Tool

ARC = Context("Arc", default="ArcThreePoint", items=[Tool("ArcThreePoint", "3-Point"), Tool("ArcTangent", "Tangent")])
CREATE = Context("Create", items=[Tool("DrawPolyline", "Line"), ARC])
CONSTRAINTS = Context("Constraints", items=[Tool("ConstraintTangent", "Tangent"), Tool("ConstraintEqual", "Equal")])
SKETCH = Context("Sketch", items=[CREATE, CONSTRAINTS, Tool("SketchStop", "Finish")])
PART = Context("Part", items=[Tool("Extrude", "Extrude")])
REGISTRY = Registry([Root(SKETCH, when=lambda fusion: True), Root(PART, when=lambda fusion: True)])

NAMES = {  # Fusion's names
    "DrawPolyline": "Line",
    "ArcThreePoint": "3-Point Arc",
    "ArcTangent": "Tangent Arc",
    "ConstraintTangent": "Tangent",
    "ConstraintEqual": "Equal",
    "SketchStop": "Finish Sketch",
    "Extrude": "Extrude",
}


class ChoicesTest(unittest.TestCase):
    def test_at_the_top_level_are_the_root_s_commands_in_keypad_order(self):
        self.assertEqual(choices(SKETCH, REGISTRY, NAMES), [
            Choice("Line", "DrawPolyline"),
            Choice("Arc", "ArcThreePoint"),  # a page with a default, by its own name
            Choice("3-Point Arc", "ArcThreePoint"),
            Choice("Tangent Arc", "ArcTangent"),
            Choice("Tangent", "ConstraintTangent"),
            Choice("Equal", "ConstraintEqual"),
            Choice("Finish Sketch", "SketchStop"),
        ])

    def test_the_current_context_s_commands_come_first_then_each_level_above(self):
        self.assertEqual([choice.name for choice in choices(ARC, REGISTRY, NAMES)], [
            "3-Point Arc", "Tangent Arc",  # Arc
            "Line", "Arc",  # the rest of Create
            "Tangent", "Equal", "Finish Sketch",  # the rest of Sketch
        ])

    def test_a_name_stays_with_the_nearest_command_that_has_it(self):
        names = {**NAMES, "ArcTangent": "Tangent"}
        self.assertIn(Choice("Tangent", "ArcTangent"), choices(ARC, REGISTRY, names))
        self.assertIn(Choice("Tangent", "ConstraintTangent"), choices(CONSTRAINTS, REGISTRY, names))
        self.assertNotIn(Choice("Tangent", "ConstraintTangent"), choices(ARC, REGISTRY, names))

    def test_commands_this_fusion_build_lacks_are_left_out(self):
        names = {**NAMES, "ArcThreePoint": None}
        self.assertEqual([choice.name for choice in choices(ARC, REGISTRY, names)], [
            "Tangent Arc", "Line", "Tangent", "Equal", "Finish Sketch",
        ])

    def test_nothing_is_offered_without_a_context(self):
        self.assertEqual(choices(None, REGISTRY, NAMES), [])


if __name__ == "__main__":
    unittest.main()
