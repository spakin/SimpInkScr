####################################################
# Demonstrate the application of live path effects #
# to a curve using Simple Inkscape Scripting.      #
####################################################

# Define some program parameters.
steps = 7  # Must be odd.
delta = width/steps

# Establish a left-to-right zigzag.
pts = []
for i in range(steps + 1):
    x = i*delta
    if i % 2 == 0:
        y = 0
    else:
        y = delta
    pts.append((x, y))

# Continue with a right-to-left zigzag.
for i in range(steps + 1):
    x = (steps - i)*delta
    if i % 2 == 0:
        y = 0
    else:
        y = delta
    pts.append((x, y))

# Draw a polygon then convert this immediately to a path.
zigzag = polygon(pts, stroke='green', stroke_width=6*pt).to_path(True)

# Instantiate the BSpline live path effect,
bspline = path_effect('bspline', weight=25)

# Instantiate the Knot live path effect.
knot = path_effect('knot')

# Apply both path effects to the path.
zigzag.apply_path_effect([bspline, knot])
