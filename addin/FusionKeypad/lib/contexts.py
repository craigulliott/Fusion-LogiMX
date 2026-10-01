"""The keypad definition: every context and its keys, in keypad order.

This is the file to edit to change what the keypad offers.

- A key that starts a Fusion command is `Tool(command_id, label)`. To find a
  command's id, use it once with the mouse: the add-in logs the id of every
  command that has no key yet (~/Library/Logs/FusionKeypad-addin.log).
- A key that opens another page is a `Context`. Give it a `default` to make it
  a tool with variants (Circle → 2-Point, 3-Point, …): opening it starts the
  default, and drawing a shape with it returns to the page above.
- Each command may have only one key in each root, so a running tool always has
  exactly one place on the keypad.
- Icons come from Fusion. `icon=` overrides one with another command's icon,
  or with a .png/.svg file placed in FusionKeypad/icons/.
- Contexts that don't fit on one page get a More key automatically.
"""

from .registry import Context, Root, Tool

# Editing a sketch -----------------------------------------------------------

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

SKETCH_PATTERN = Context("Pattern", icon="RectangularSketchPatternCommand", items=[
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

SKETCH_CREATE = Context("Create", icon="DrawPolyline", items=[
    LINE,
    RECTANGLE,
    CIRCLE,
    ARC,
    Tool("DrawPoint", "Point"),
    TEXT,
    PROJECT,
    Tool("ConicCurveCmd", "Conic"),
    Tool("CircleElipse", "Ellipse"),
    Tool("MirrorSketchCommand", "Mirror"),
    SKETCH_PATTERN,
    POLYGON,
    SLOT,
    SPLINE,
])

CONSTRAINTS = Context("Constraints", icon="ConstraintCoincident", items=[
    Tool("ConstraintMidPoint", "Midpoint"),
    Tool("ConstraintPerpendicular", "Perpendicular"),
    Tool("ConstraintHorizontalVertical", "Horiz/Vert"),
    Tool("ConstraintTangent", "Tangent"),
    Tool("ConstraintEqual", "Equal"),
    Tool("ConstraintConcentric", "Concentric"),
    Tool("ConstraintCoincident", "Coincident"),
    Tool("ConstraintSymmetry", "Symmetry"),
    Tool("ConstraintParallel", "Parallel"),
    Tool("ConstraintSmooth", "Curvature"),
    Tool("ConstraintCollinear", "Collinear"),
    Tool("ConstraintFix", "Fix"),
])

SKETCH = Context("Sketch", items=[
    SKETCH_CREATE,
    CONSTRAINTS,
    Tool("SketchDimension", "Dimension"),
    Tool("SketchConstructionCmd", "Construction"),
    Tool("SketchCenterLineCmd", "Centerline"),
    Tool("SketchStop", "Finish"),
])

# Part and Hybrid designs, which share Fusion's Solid tab --------------------

PART_PATTERN = Context("Pattern", icon="PatternRectangular", items=[
    Tool("PatternRectangular", "Rectangular"),
    Tool("PatternCircular", "Circular"),
    Tool("PatternOnPath", "On Path"),
    Tool("FusionPatternGeometricCommand", "Geometric"),
])

PART_CREATE = Context("Create", icon="Extrude", items=[
    Tool("Extrude", "Extrude"),
    Tool("Revolve", "Revolve"),
    PART_PATTERN,
    Tool("MirrorCommand", "Mirror"),
    Tool("FusionThreadCommand", "Thread"),
    Tool("FusionHoleCommand", "Hole"),
])

MODIFY = Context("Modify", icon="FusionFilletEdgesCommand", items=[
    Tool("FusionFilletEdgesCommand", "Fillet"),
    Tool("FusionChamferCommand", "Chamfer"),
    Tool("FusionCombineCommand", "Combine"),
])

CONSTRUCT = Context("Construct", icon="ConstructionPlaneOffsetFromPlaneCommand", items=[
    Tool("ConstructionPlaneOffsetFromPlaneCommand", "Offset Plane"),
    Tool("ConstructionAxisThroughCylinderCommand", "Axis Thru Cyl"),
    Tool("ConstructionTangentPlaneCommand", "Tangent Plane"),
    Tool("ConstructionMidPlaneCommand", "Midplane"),
])

PART = Context("Part", items=[
    Tool("SketchCreate", "New Sketch"),
    PART_CREATE,
    MODIFY,
    CONSTRUCT,
    Tool("JointOrigin", "Joint Origin"),
    Tool("ChangeParameterCommand", "Parameters"),
    Tool("FusionHalfSectionViewCommand", "Section"),
    Tool("PushDeriveCommand", "Derive"),
])

# Assembly designs -----------------------------------------------------------

ASSEMBLY = Context("Assembly", items=[
    Tool("FusionImportCommandFromToolbar", "Insert"),
    Tool("JointAssembleCmdNew", "Joint"),
    Tool("FusionHalfSectionViewCommand", "Section"),
])

ROOTS = [
    Root(SKETCH, when=lambda fusion: fusion.editing_sketch),
    Root(ASSEMBLY, when=lambda fusion: fusion.workspace == "FusionSolidEnvironment" and fusion.assembly),
    Root(PART, when=lambda fusion: fusion.workspace == "FusionSolidEnvironment" and not fusion.assembly),
]
