"""server — the tool the model is offered, and what starting a tool reports."""

import unittest

from server import start, tool

PNG = "iVBORw0KGgoAAAANSUhEUg=="  # how a base64 PNG starts
SVG = "PHN2Zy8+"  # "<svg/>"

CONSTRAINING = {
    "type": "state",
    "context": "Sketch/Constraints",
    "running": "ConstraintCoincident",
    "icon": {"dark": SVG, "light": SVG},
    "choices": [
        {"name": "Coincident", "command": "ConstraintCoincident"},
        {"name": "Tangent", "command": "ConstraintTangent"},
        {"name": "Line", "command": "DrawPolyline"},
    ],
}
TANGENT_RUNNING = {**CONSTRAINING, "running": "ConstraintTangent", "icon": {"dark": PNG, "light": SVG}}


class FakeLink:
    """Stands in for AddinLink: the add-in's state, and the state Fusion reports once a command starts."""

    def __init__(self, state, started=None):
        self.state = state
        self.started = started  # None: Fusion is busy and doesn't confirm
        self.ran: list[str] = []

    async def run(self, command):
        self.ran.append(command)
        return self.started


class ToolTest(unittest.TestCase):
    def test_takes_the_name_of_one_of_the_choices_nearest_first(self):
        offered = tool(CONSTRAINING)
        self.assertEqual(offered.name, "start_tool")
        self.assertEqual(offered.input_schema["properties"]["name"]["enum"], ["Coincident", "Tangent", "Line"])
        self.assertEqual(offered.input_schema["required"], ["name"])

    def test_says_where_the_user_is_and_what_is_running(self):
        self.assertIn("(Sketch › Constraints, with Coincident running)", tool(CONSTRAINING).description)
        self.assertIn("(Sketch › Constraints)", tool({**CONSTRAINING, "running": None}).description)

    def test_is_not_offered_when_there_is_nothing_to_choose(self):
        self.assertIsNone(tool(None))
        self.assertIsNone(tool({**CONSTRAINING, "context": None, "running": None, "icon": None, "choices": []}))

    def test_starting_a_tool_is_not_destructive(self):
        annotations = tool(CONSTRAINING).annotations
        self.assertEqual(
            (annotations.destructive_hint, annotations.idempotent_hint, annotations.open_world_hint),
            (False, True, False),
        )


class StartTest(unittest.IsolatedAsyncioTestCase):
    async def test_reports_the_start_with_the_icon_for_the_background_for_the_user(self):
        link = FakeLink(CONSTRAINING, started=TANGENT_RUNNING)
        result = await start(link, "Tangent", "dark")
        self.assertEqual(link.ran, ["ConstraintTangent"])
        self.assertFalse(result.is_error)
        text, image = result.content
        self.assertEqual(text.text, "Started Tangent.")
        self.assertEqual((image.data, image.mime_type, image.annotations.audience), (PNG, "image/png", ["user"]))

    async def test_an_svg_icon_is_sent_as_svg(self):
        result = await start(FakeLink(CONSTRAINING, started=TANGENT_RUNNING), "Tangent", "light")
        self.assertEqual((result.content[1].data, result.content[1].mime_type), (SVG, "image/svg+xml"))

    async def test_a_tool_without_an_icon_is_reported_in_text_alone(self):
        started = {**TANGENT_RUNNING, "icon": {"dark": None, "light": None}}
        result = await start(FakeLink(CONSTRAINING, started=started), "Tangent", "dark")
        self.assertEqual([content.text for content in result.content], ["Started Tangent."])

    async def test_a_start_fusion_has_not_confirmed_is_not_an_error_and_should_not_be_repeated(self):
        result = await start(FakeLink(CONSTRAINING), "Tangent", "dark")
        self.assertFalse(result.is_error)
        self.assertIn("don't ask again", result.content[0].text)

    async def test_a_name_that_is_not_offered_is_an_error_and_runs_nothing(self):
        link = FakeLink(CONSTRAINING, started=TANGENT_RUNNING)
        result = await start(link, "Extrude", "dark")
        self.assertTrue(result.is_error)
        self.assertEqual(link.ran, [])

    async def test_without_the_add_in_it_is_an_error(self):
        result = await start(FakeLink(None), "Tangent", "dark")
        self.assertTrue(result.is_error)
        self.assertIn("isn't reachable", result.content[0].text)


if __name__ == "__main__":
    unittest.main()
