"""registry.Registry — lookups over a keypad definition, and the checks on it."""

import unittest

import _bootstrap  # noqa: F401

from FusionKeypad.lib.registry import Context, FusionState, Registry, Root, Tool


def _definition():
    circle = Context("Circle", default="C1", items=[Tool("C1", "c1"), Tool("C2", "c2")])
    create = Context("Create", icon="L", items=[Tool("L", "line"), circle])
    sketch = Context("Sketch", items=[create, Tool("DIM", "dim")])
    design = Context("Design", items=[Tool("NEW", "new")])
    roots = [
        Root(sketch, when=lambda fusion: fusion.editing_sketch),
        Root(design, when=lambda fusion: fusion.workspace == "Design"),
    ]
    return roots, sketch, create, circle, design


class LookupTest(unittest.TestCase):
    def setUp(self):
        roots, self.sketch, self.create, self.circle, self.design = _definition()
        self.registry = Registry(roots)

    def test_the_first_root_whose_condition_holds_is_the_top_level(self):
        self.assertIs(self.registry.root_for(FusionState("Design", editing_sketch=True, assembly=False)), self.sketch)
        self.assertIs(self.registry.root_for(FusionState("Design", editing_sketch=False, assembly=False)), self.design)
        self.assertIsNone(self.registry.root_for(FusionState("Render", editing_sketch=False, assembly=False)))

    def test_a_command_s_home_is_the_context_holding_its_key(self):
        self.assertIs(self.registry.home("C2"), self.circle)
        self.assertIs(self.registry.home("DIM"), self.sketch)
        self.assertIsNone(self.registry.home("SelectCommand"))

    def test_a_command_s_key_is_its_tool_in_that_home(self):
        self.assertIs(self.registry.key("C2"), self.circle.items[1])
        self.assertIsNone(self.registry.key("SelectCommand"))

    def test_parents_and_roots(self):
        self.assertIs(self.registry.parent(self.circle), self.create)
        self.assertIsNone(self.registry.parent(self.sketch))
        self.assertIs(self.registry.root_of(self.circle), self.sketch)

    def test_a_context_s_path_names_it_from_its_root(self):
        self.assertEqual(self.registry.path(self.circle), "Sketch/Create/Circle")
        self.assertEqual(self.registry.path(self.design), "Design")

    def test_a_context_contains_the_keys_below_it_at_any_depth(self):
        self.assertTrue(self.registry.contains(self.circle, "C2"))
        self.assertTrue(self.registry.contains(self.sketch, "C2"))
        self.assertFalse(self.registry.contains(self.circle, "L"))
        self.assertFalse(self.registry.contains(self.design, "C2"))
        self.assertFalse(self.registry.contains(self.sketch, "SelectCommand"))

    def test_lists_every_command_with_a_key(self):
        self.assertEqual(sorted(self.registry.commands()), ["C1", "C2", "DIM", "L", "NEW"])

    def test_icons_fall_back_to_the_command_or_the_default(self):
        self.assertEqual(Tool("L", "line").icon_source, "L")
        self.assertEqual(Tool("L", "line", icon="line.png").icon_source, "line.png")
        self.assertEqual(self.circle.icon_source, "C1")
        self.assertEqual(self.create.icon_source, "L")
        self.assertIsNone(self.sketch.icon_source)


class KeyInEachRootTest(unittest.TestCase):
    """A command may have a key in each root; where the user is picks the one that counts."""

    def setUp(self):
        self.sketch = Context("Sketch", items=[Tool("L", "line")])
        self.assembly = Context("Assembly", items=[Tool("SEC", "section")])
        self.part = Context("Part", items=[Tool("SEC", "section")])
        self.registry = Registry([
            Root(self.sketch, when=lambda fusion: fusion.editing_sketch),
            Root(self.assembly, when=lambda fusion: fusion.assembly),
            Root(self.part, when=lambda fusion: not fusion.assembly),
        ])

    def test_the_first_root_that_applies_and_has_a_key_holds_the_home(self):
        part = FusionState("Design", editing_sketch=False, assembly=False)
        sketching_in_a_part = FusionState("Design", editing_sketch=True, assembly=False)
        assembly = FusionState("Design", editing_sketch=False, assembly=True)
        self.assertIs(self.registry.home("SEC", part), self.part)
        self.assertIs(self.registry.home("SEC", sketching_in_a_part), self.part)
        self.assertIs(self.registry.home("SEC", assembly), self.assembly)

    def test_the_key_that_counts_is_the_one_in_that_home(self):
        assembly = FusionState("Design", editing_sketch=False, assembly=True)
        self.assertIs(self.registry.key("SEC", assembly), self.assembly.items[0])

    def test_otherwise_the_first_root_with_a_key_holds_the_home(self):
        self.assertIs(self.registry.home("L", FusionState("Design", editing_sketch=False, assembly=False)), self.sketch)
        self.assertIs(self.registry.home("SEC"), self.assembly)

    def test_each_root_contains_its_own_key(self):
        self.assertTrue(self.registry.contains(self.part, "SEC"))
        self.assertTrue(self.registry.contains(self.assembly, "SEC"))
        self.assertFalse(self.registry.contains(self.sketch, "SEC"))


class ChecksTest(unittest.TestCase):
    def _build(self, *contexts):
        return Registry([Root(context, when=lambda fusion: True) for context in contexts])

    def test_a_command_may_have_only_one_key_in_each_root(self):
        with self.assertRaisesRegex(ValueError, "more than one key in 'Top'"):
            self._build(Context("Top", items=[Tool("A", "a"), Context("Sub", items=[Tool("A", "again")])]))

    def test_a_context_is_defined_once(self):
        shared = Context("Shared", items=[Tool("A", "a")])
        with self.assertRaisesRegex(ValueError, "defined more than once"):
            self._build(Context("One", items=[shared]), Context("Two", items=[shared]))

    def test_a_default_must_be_one_of_the_context_s_own_keys(self):
        with self.assertRaisesRegex(ValueError, "not one of its keys"):
            self._build(Context("Top", default="B", items=[Tool("A", "a"), Context("Sub", items=[Tool("B", "b")])]))


if __name__ == "__main__":
    unittest.main()
