"""The keypad definition: every context and its keys, in keypad order.

This is the file to edit to change what the keypad offers.

- A key that starts a Fusion command is `Tool(command_id, label)`. To find a
  command's id, use it once with the mouse: the add-in logs the id of every
  command that has no key yet (~/Library/Logs/FusionKeypad-addin.log).
- A key that opens another page is a `Context`. Give it a `default` to make it
  a tool with variants (Circle → 2-Point, 3-Point, …): opening it starts the
  default, and drawing a shape with it returns to the page above.
- Each command may have only one key, so a running tool always has exactly one
  place on the keypad.
- Icons come from Fusion. `icon=` overrides one with another command's icon,
  or with a .png/.svg file placed in FusionKeypad/icons/.
- Contexts that don't fit on one page get a More key automatically.
"""

from .registry import Context, Root, Tool

LINE = Context("Line", default="DrawPolyline", items=[
    Tool("DrawPolyline", "Line"),
    Tool("SketchMidpointLine", "Midpoint"),
])

RECTANGLE = Context("Rectangle", default="ShapeRectangleTwoPoint", items=[
    Tool("ShapeRectangleTwoPoint", "2-Point"),
    Tool("ShapeRectangleThreePoint", "3-Point"),
    Tool("ShapeRectangleCenter", "Center"),
])

CIRCLE = Context("Circle", default="CircleCenterRadius", items=[
    Tool("CircleCenterRadius", "Center Dia"),
    Tool("CircleTwoPoint", "2-Point"),
    Tool("CircleThreePoint", "3-Point"),
    Tool("CircleTanTanRadius", "2-Tangent"),
    Tool("CircleThreeTangent", "3-Tangent"),
])

ARC = Context("Arc", default="ArcThreePoint", items=[
    Tool("ArcThreePoint", "3-Point"),
    Tool("ArcCenterTwoPoint", "Center"),
    Tool("ArcTangent", "Tangent"),
])

POLYGON = Context("Polygon", default="ShapePolygonCircumscribed", items=[
    Tool("ShapePolygonCircumscribed", "Circumscribed"),
    Tool("ShapePolygonInscribed", "Inscribed"),
    Tool("ShapePolygonEdge", "Edge"),
])

SLOT = Context("Slot", default="ShapeSlotCenterToCenter", items=[
    Tool("ShapeSlotCenterToCenter", "Ctr to Ctr"),
    Tool("ShapeSlotOverall", "Overall"),
    Tool("ShapeSlotCenterPoint", "Ctr Point"),
    Tool("ShapeArcSlotThreePoint", "3-Pt Arc"),
    Tool("ShapeArcSlotCenterTwoPoint", "Ctr Arc"),
])

SPLINE = Context("Spline", default="DrawSpline", items=[
    Tool("DrawSpline", "Fit Point"),
    Tool("DrawCVMSpline3D", "Ctrl Point"),
])

TEXT = Context("Text", default="MTextCmd", items=[
    Tool("MTextCmd", "Text"),
    Tool("TextOnPathCmd", "On Path"),
])

PATTERN = Context("Pattern", icon="RectangularSketchPatternCommand", items=[
    Tool("RectangularSketchPatternCommand", "Rectangular"),
    Tool("CircularSketchPatternCommand", "Circular"),
])

PROJECT = Context("Project", icon="ProjectNewCmd", items=[
    Tool("ProjectNewCmd", "Project"),
    Tool("IntersectCmd", "Intersect"),
    Tool("Include3DGeometry", "Include 3D"),
    Tool("ProjectToSurface", "To Surface"),
    Tool("IntersectionCurve", "Int. Curve"),
])

CREATE = Context("Create", icon="DrawPolyline", items=[
    LINE,
    RECTANGLE,
    CIRCLE,
    ARC,
    POLYGON,
    Tool("CircleElipse", "Ellipse"),
    SLOT,
    SPLINE,
    Tool("ConicCurveCmd", "Conic"),
    Tool("DrawPoint", "Point"),
    TEXT,
    Tool("MirrorSketchCommand", "Mirror"),
    PATTERN,
    PROJECT,
])

CONSTRAINTS = Context("Constraints", icon="ConstraintCoincident", items=[
    Tool("ConstraintCoincident", "Coincident"),
    Tool("ConstraintCollinear", "Collinear"),
    Tool("ConstraintConcentric", "Concentric"),
    Tool("ConstraintMidPoint", "Midpoint"),
    Tool("ConstraintFix", "Fix"),
    Tool("ConstraintParallel", "Parallel"),
    Tool("ConstraintPerpendicular", "Perpendicular"),
    Tool("ConstraintHorizontalVertical", "Horiz/Vert"),
    Tool("ConstraintTangent", "Tangent"),
    Tool("ConstraintSmooth", "Curvature"),
    Tool("ConstraintEqual", "Equal"),
    Tool("ConstraintSymmetry", "Symmetry"),
])

SKETCH = Context("Sketch", items=[
    CREATE,
    CONSTRAINTS,
    Tool("SketchDimension", "Dimension"),
    Tool("SketchStop", "Finish"),
])

DESIGN = Context("Design", items=[
    Tool("SketchCreate", "New Sketch"),
])

ROOTS = [
    Root(SKETCH, when=lambda fusion: fusion.editing_sketch),
    Root(DESIGN, when=lambda fusion: fusion.workspace == "FusionSolidEnvironment"),
]
