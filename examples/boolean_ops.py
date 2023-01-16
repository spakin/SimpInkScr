##################################################################
# Use Simple Inkscape Scripting to apply Boolean path operations #
# to various objects.                                            #
##################################################################

# Draw all shapes in dark purple with a golden outline.
style(fill='#330080', stroke_width=3, stroke='#ffcc00')

# Draw a rectangle with a circle at each corner.
r1 = rect((128, 128), (384, 256))
c1 = circle((128, 128), 32)
c2 = circle((384, 128), 32)
c3 = circle((384, 256), 32)
c4 = circle((128, 256), 32)

# Merge all of the above into a single shape via path union.
shapes = [r1, c1, c2, c3, c4]
merged = apply_path_operation('union', [s.to_path() for s in shapes])

# Draw a star in the middle of the rectangle.
s1 = star(7, (256, 192), (45, 24))

# Subtract the star from the rectangle.
apply_path_operation('difference', [merged[0], s1.to_path()])
