"""layout.faces — what each key shows."""

import unittest

import _bootstrap  # noqa: F401

from FusionKeypad.lib.layout import Face, faces
from FusionKeypad.lib.navigator import Nav
from FusionKeypad.lib.registry import Context, Registry, Root, Tool

LINE = Tool("L", "Line")
MARKED = Tool("M", "Mark", icon="mark.png")
CIRCLE = Context("Circle", default="C1", items=[Tool("C1", "Center"), Tool("C2", "2-Point")])
PLAIN = Context("Plain", items=[Tool("P", "p")])
TOP = Context("Top", items=[LINE, MARKED, CIRCLE, PLAIN])
REGISTRY = Registry([Root(TOP, when=lambda fusion: True)])


def icon(source, background):
    return f"<{source} on {background}>"


class FacesTest(unittest.TestCase):
    def test_navigation_and_empty_keys_are_text_only(self):
        self.assertEqual(
            faces([Nav.BACK, None, Nav.MORE], None, REGISTRY, icon),
            [Face("‹ Back", None), Face("", None), Face("More ›", None)],
        )

    def test_a_tool_key_shows_its_label_and_its_icon_for_a_dark_background(self):
        self.assertEqual(
            faces([LINE, MARKED], None, REGISTRY, icon),
            [Face("Line", "<L on dark>"), Face("Mark", "<mark.png on dark>")],
        )

    def test_a_context_key_says_it_opens_a_page(self):
        self.assertEqual(
            faces([CIRCLE, PLAIN], None, REGISTRY, icon),
            [Face("Circle ›", "<C1 on dark>"), Face("Plain ›", None)],
        )

    def test_the_running_tool_and_the_context_leading_to_it_are_marked(self):
        self.assertEqual(
            faces([LINE, CIRCLE, PLAIN], "C2", REGISTRY, icon),
            [Face("Line", "<L on dark>"), Face("▶ Circle ›", "<C1 on dark>"), Face("Plain ›", None)],
        )
        self.assertEqual(faces([LINE], "L", REGISTRY, icon), [Face("▶ Line", "<L on dark>")])


if __name__ == "__main__":
    unittest.main()
