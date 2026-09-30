"""navigator.Navigator — the rules that move the keypad (numbered as in its docstring)."""

import unittest

import _bootstrap  # noqa: F401

from FusionKeypad.lib import contexts
from FusionKeypad.lib.navigator import Nav, Navigator
from FusionKeypad.lib.registry import Context, FusionState, Registry, Root, Tool

SKETCHING = FusionState("FusionSolidEnvironment", editing_sketch=True)
DESIGNING = FusionState("FusionSolidEnvironment", editing_sketch=False)
RENDERING = FusionState("FusionRenderEnvironment", editing_sketch=False)

LINE = Tool("Line", "line")
CIRCLE = Context("Circle", default="CircleA", items=[Tool("CircleA", "a"), Tool("CircleB", "b")])
DEEP = Context("Deep", items=[Tool("Deep1", "d")])
MANY = Context("Many", items=[*(Tool(f"Many{i}", f"m{i}") for i in range(11)), DEEP])  # 12 keys: two pages
CREATE = Context("Create", items=[LINE, CIRCLE, MANY])
DIMENSION = Tool("Dimension", "dim")
SKETCH = Context("Sketch", items=[CREATE, DIMENSION])
DESIGN = Context("Design", items=[Tool("NewSketch", "new")])
ROOTS = [
    Root(SKETCH, when=lambda fusion: fusion.editing_sketch),
    Root(DESIGN, when=lambda fusion: fusion.workspace == "FusionSolidEnvironment"),
]


class FakeFusion:
    """Records what the navigator asks of Fusion.

    Like Fusion, cancel() ends the running tool, reported as Completed, before
    it returns.
    """

    def __init__(self):
        self.started: list[str] = []
        self.cancels = 0
        self.navigator: Navigator | None = None

    def start(self, command: str) -> None:
        self.started.append(command)

    def cancel(self) -> None:
        self.cancels += 1
        if self.navigator.running is not None:
            self.navigator.command_ended(self.navigator.running, replaced=False)


def make(roots=ROOTS, fusion_state=SKETCHING) -> tuple[Navigator, FakeFusion]:
    fusion = FakeFusion()
    navigator = Navigator(Registry(roots), fusion)
    fusion.navigator = navigator
    navigator.fusion_changed(fusion_state)
    return navigator, fusion


def open_path(navigator: Navigator, *path: Context) -> None:
    for context in path:
        navigator.press(context)


class SlotsTest(unittest.TestCase):
    def test_the_top_level_has_no_back_key(self):
        navigator, _ = make()
        self.assertEqual(navigator.slots(), [CREATE, DIMENSION, *[None] * 7])

    def test_back_comes_first_below_the_top_level(self):
        navigator, _ = make()
        navigator.press(CREATE)
        self.assertEqual(navigator.slots(), [Nav.BACK, LINE, CIRCLE, MANY, *[None] * 5])

    def test_a_context_that_does_not_fit_gets_pages_with_more_last(self):
        navigator, _ = make()
        open_path(navigator, CREATE, MANY)
        self.assertEqual(navigator.slots(), [Nav.BACK, *MANY.items[:7], Nav.MORE])
        navigator.press(Nav.MORE)
        self.assertEqual(navigator.slots(), [Nav.BACK, *MANY.items[7:], None, None, Nav.MORE])

    def test_the_keypad_is_blank_where_no_root_applies(self):
        navigator, _ = make(fusion_state=RENDERING)
        self.assertEqual(navigator.slots(), [None] * 9)


class Rule1WhereTheUserIsTest(unittest.TestCase):
    def test_picks_the_top_level_for_where_the_user_is(self):
        navigator, _ = make(fusion_state=DESIGNING)
        self.assertIs(navigator.context, DESIGN)
        navigator.fusion_changed(SKETCHING)
        self.assertIs(navigator.context, SKETCH)
        navigator.fusion_changed(RENDERING)
        self.assertIsNone(navigator.context)

    def test_leaves_the_page_alone_when_the_top_level_is_unchanged(self):
        navigator, _ = make()
        open_path(navigator, CREATE, MANY)
        navigator.press(Nav.MORE)
        navigator.fusion_changed(SKETCHING)
        self.assertEqual((navigator.context, navigator.page), (MANY, 1))

    def test_a_running_tool_s_context_wins_until_it_ends(self):
        navigator, _ = make(fusion_state=DESIGNING)
        navigator.command_started("CircleB")  # a sketch tool started outside a sketch
        navigator.fusion_changed(DESIGNING)
        self.assertIs(navigator.context, CIRCLE)


class Rule2ToolStartsTest(unittest.TestCase):
    def test_shows_the_context_holding_the_key(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        self.assertEqual((navigator.context, navigator.running), (CIRCLE, "CircleB"))

    def test_shows_the_page_with_the_key(self):
        navigator, _ = make()
        navigator.command_started("Many9")
        self.assertEqual((navigator.context, navigator.page), (MANY, 1))

    def test_ignores_commands_without_a_key(self):
        navigator, _ = make()
        navigator.press(CREATE)
        navigator.command_started("ConstrainedOrbitCommand")
        self.assertEqual((navigator.context, navigator.running), (CREATE, None))


class Rule3PressToolTest(unittest.TestCase):
    def test_only_asks_fusion_to_start_the_tool(self):
        navigator, fusion = make()
        navigator.press(CREATE)
        navigator.press(LINE)
        self.assertEqual(fusion.started, ["Line"])
        self.assertEqual((navigator.context, navigator.running), (CREATE, None))


class Rule4OpenContextTest(unittest.TestCase):
    def test_opens_the_context_and_starts_its_default(self):
        navigator, fusion = make()
        open_path(navigator, CREATE, CIRCLE)
        self.assertIs(navigator.context, CIRCLE)
        self.assertEqual(fusion.started, ["CircleA"])

    def test_a_context_without_a_default_starts_nothing(self):
        navigator, fusion = make()
        open_path(navigator, CREATE, MANY)
        self.assertEqual(fusion.started, [])


class Rule5ShapeDrawnTest(unittest.TestCase):
    def test_returns_from_the_variants_to_the_page_above_and_keeps_the_tool(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        navigator.shape_drawn()
        self.assertEqual((navigator.context, navigator.running), (CREATE, "CircleB"))

    def test_a_tool_without_variants_stays_where_it_is(self):
        navigator, _ = make()
        navigator.command_started("Line")
        navigator.shape_drawn()
        self.assertIs(navigator.context, CREATE)

    def test_does_nothing_once_the_user_has_moved_away_from_the_variants(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        navigator.press(Nav.BACK)
        navigator.press(MANY)
        navigator.shape_drawn()
        self.assertIs(navigator.context, MANY)


class Rule6ToolEndsTest(unittest.TestCase):
    def test_returns_to_the_top_level(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        navigator.command_ended("CircleB", replaced=False)
        self.assertEqual((navigator.context, navigator.running), (SKETCH, None))

    def test_a_replaced_tool_leaves_the_decision_to_the_next_tool(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        navigator.command_started("Line")
        navigator.command_ended("CircleB", replaced=True)
        self.assertEqual((navigator.context, navigator.running), (CREATE, "Line"))

    def test_replaced_by_a_command_without_a_key_stays_put_with_nothing_running(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        navigator.command_ended("CircleB", replaced=True)
        self.assertEqual((navigator.context, navigator.running), (CIRCLE, None))

    def test_ignores_commands_that_are_not_the_running_tool(self):
        navigator, _ = make()
        navigator.command_started("CircleB")
        navigator.command_ended("SelectCommand", replaced=False)
        self.assertEqual((navigator.context, navigator.running), (CIRCLE, "CircleB"))

    def test_a_tool_that_leaves_the_sketch_lands_on_the_new_top_level(self):
        navigator, _ = make()
        navigator.command_started("Dimension")
        navigator.command_ended("Dimension", replaced=False)  # then Fusion reports the move:
        navigator.fusion_changed(DESIGNING)
        self.assertIs(navigator.context, DESIGN)


class Rule7BackTest(unittest.TestCase):
    def test_goes_up_one_level_to_the_page_with_the_key_it_came_from(self):
        navigator, _ = make()
        open_path(navigator, CREATE, MANY)
        navigator.press(Nav.MORE)
        navigator.press(DEEP)
        navigator.press(Nav.BACK)
        self.assertEqual((navigator.context, navigator.page), (MANY, 1))

    def test_below_the_top_level_the_tool_keeps_running(self):
        navigator, fusion = make()
        navigator.command_started("CircleB")
        navigator.press(Nav.BACK)
        self.assertEqual((navigator.context, navigator.running, fusion.cancels), (CREATE, "CircleB", 0))

    def test_arriving_at_the_top_level_cancels_the_running_tool(self):
        navigator, fusion = make()
        navigator.command_started("Line")
        navigator.press(Nav.BACK)
        self.assertEqual((navigator.context, navigator.running, fusion.cancels), (SKETCH, None, 1))

    def test_does_nothing_at_the_top_level(self):
        navigator, _ = make()
        navigator.press(Nav.BACK)
        self.assertIs(navigator.context, SKETCH)


class Rule8MoreTest(unittest.TestCase):
    def test_steps_through_the_pages_and_wraps(self):
        navigator, _ = make()
        open_path(navigator, CREATE, MANY)
        pages = []
        for _ in range(3):
            pages.append(navigator.page)
            navigator.press(Nav.MORE)
        self.assertEqual(pages, [0, 1, 0])


class YourScenarioTest(unittest.TestCase):
    """The behaviour described when the project started, on the real contexts.py."""

    def test_sketching_a_circle_then_constraining(self):
        navigator, fusion = make(contexts.ROOTS)
        self.assertIs(navigator.context, contexts.SKETCH)

        # Create shows line, rectangle, circle, …; Circle starts a circle and shows the circle types.
        open_path(navigator, contexts.CREATE, contexts.CIRCLE)
        self.assertEqual(fusion.started, ["CircleCenterRadius"])
        navigator.command_started("CircleCenterRadius")
        self.assertIs(navigator.context, contexts.CIRCLE)

        # Three-point selects that tool in Fusion.
        three_point = next(tool for tool in contexts.CIRCLE.items if tool.command == "CircleThreePoint")
        navigator.press(three_point)
        navigator.command_started("CircleThreePoint")
        navigator.command_ended("CircleCenterRadius", replaced=True)
        self.assertEqual((navigator.context, navigator.running), (contexts.CIRCLE, "CircleThreePoint"))

        # Drawing the circle returns to the list of things to create.
        navigator.shape_drawn()
        self.assertEqual((navigator.context, navigator.page), (contexts.CREATE, 0))

        # Esc in Fusion: no longer creating, so back to the sketch context.
        navigator.command_ended("CircleThreePoint", replaced=False)
        self.assertIs(navigator.context, contexts.SKETCH)

        # Starting a constraint with the mouse switches to the constraints, on Tangent's page.
        navigator.command_started("ConstraintTangent")
        self.assertEqual((navigator.context, navigator.page), (contexts.CONSTRAINTS, 1))

        # Back returns to the sketch context and ends the constraint tool.
        navigator.press(Nav.BACK)
        self.assertEqual((navigator.context, navigator.running, fusion.cancels), (contexts.SKETCH, None, 1))

    def test_back_from_a_second_page_context_returns_to_that_page(self):
        navigator, _ = make(contexts.ROOTS)
        navigator.press(contexts.CREATE)
        navigator.press(Nav.MORE)
        navigator.press(contexts.TEXT)
        navigator.command_started("MTextCmd")
        navigator.press(Nav.BACK)
        self.assertEqual((navigator.context, navigator.page), (contexts.CREATE, 1))

    def test_a_new_sketch_from_the_design_keys(self):
        navigator, fusion = make(contexts.ROOTS, fusion_state=DESIGNING)
        navigator.press(contexts.DESIGN.items[0])
        navigator.command_started("SketchCreate")
        navigator.command_ended("SketchCreate", replaced=False)
        navigator.fusion_changed(SKETCHING)
        self.assertEqual(fusion.started, ["SketchCreate"])
        self.assertIs(navigator.context, contexts.SKETCH)


if __name__ == "__main__":
    unittest.main()
