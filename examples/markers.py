# Use Simple Inkscape Scripting to draw arrows with begin, middle, and
# ending markers.

# Define a triangular arrowhead to use as an end marker, a large dot
# to use as a begin marker, and a chevron to use as a middle marker.
# All of these are defined with no fill and no stroke to allow these
# to be provided by the call to marker.
tri = polygon([(0, 0), (4, 2), (0, 4), (1, 2)], fill=None, stroke=None)
circ = circle((0, 0), 1.1, fill=None, stroke=None)
v = polyline([(0, 0), (2, 2), (0, 4)],
             fill=None, stroke=None, stroke_linecap=None)


def draw_arrow(begin, end, color, **style):
    'Draw an arrow from given beginning to given ending coordinates.'
    # Define beginning, middle, and ending markers.
    arrowhead = marker(tri, ref=(1, 2), fill=color, stroke='none')
    dot = marker(circ, fill=color, stroke='none')
    chevron = marker(v, ref=(2, 2), fill='none',
                     stroke=color, stroke_width=0.5, stroke_linecap='round')

    # Draw the arrow as a polyline with markers.  We use a polyline
    # because an ordinary line has no place to put a middle marker.
    x0, y0 = begin
    x1, y1 = end
    xm, ym = (x0 + x1)/2, (y0 + y1)/2
    polyline([(x0, y0), (xm, ym), (x1, y1)], stroke=color,
             marker_start=dot, marker_mid=chevron, marker_end=arrowhead,
             **style)


# Draw a large number of arrows.
for i in range(100):
    x0, y0 = uniform(0, width - 1), uniform(0, height - 1)
    x1, y1 = uniform(0, width - 1), uniform(0, height - 1)
    color = '#%02x%02x%02x' % \
        (randint(0, 255), randint(0, 255), randint(0, 255))
    thick = uniform(2, 6)
    draw_arrow((x0, y0), (x1, y1), color, stroke_width=thick)
