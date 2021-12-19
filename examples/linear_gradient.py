##########################################################################
# Use Simple Inkscape Scripting to fill a shape with a gradient pattern. #
##########################################################################

# Define a colorful gradient ranging from upper left to lower right.
colorful = linear_gradient((0, 0), (1, 1))
for s in range(8):
    r, g, b = ((s >> 2) & 1)*255, ((s >> 1) & 1)*255, ((s >> 0) & 1)*255
    colorful.add_stop(s/7, '#%02x%02x%02x' % (r, g, b))


def square_subpath(ul, lr):
    'Return a square subpath.'
    from inkex.paths import Move, Line, ZoneClose
    x0, y0 = ul
    x1, y1 = lr
    return [Move(x0, y0),
            Line(x1, y0), Line(x1, y1), Line(x0, y1), Line(x0, y0),
            ZoneClose()]


# Create a single path of multiple nested squares.
edge = min(width, height)
squares = square_subpath((0, 0), (edge, edge))
for s in [8, 5, 4, 3]:
    squares.extend(square_subpath((edge/s, edge/s),
                                  (edge - edge/s, edge - edge/s)))

# Fill the path with the gradient we defined.
path(squares, fill_rule='evenodd', fill=colorful, stroke_width=2)
