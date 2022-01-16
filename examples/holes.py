##########################################################################
# Use Simple Inkscape Scripting to draw a few shapes with holes in them. #
##########################################################################

# Use the same style for all of the following objects.
style(stroke_width=2, fill='rgb(171, 55, 200)')

# Draw a square with a circular hole.
outer1 = rect((0, 0), (100, 100)).to_path()
inner1 = circle((50, 50), 30).to_path()
outer1.append(inner1)

# Draw a circle with a square hole.
outer2 = circle((200, 50), 50).to_path()
inner2 = rect((175, 25), (225, 75)).to_path()
outer2.append(inner2)
