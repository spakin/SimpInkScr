# Use Simple Inkscape Scripting to draw an arrow with begin, middle,
# and ending markers.

# Define a triangular arrowhead to use as an end marker.
tri = polygon([(0, 0), (4, 2), (0, 4), (1, 2)], fill=None, stroke=None)
arrowhead = marker(tri, x=1, y=2, fill='blue', stroke='none')

# Define a large dot to use as a begin marker.
circ = circle((0, 0), 1.1, fill=None, stroke=None)
dot = marker(circ, fill='blue', stroke='none')

# Define a chevron to use as a middle marker.
v = polyline([(0, 0), (2, 2), (0, 4)],
             fill=None, stroke=None, stroke_linecap=None)
chevron = marker(v, x=2, y=2, fill='none',
                 stroke='blue', stroke_width=0.5, stroke_linecap='round')

# Draw an arrow using all of the above.
polyline([(16, 16), (32, 16), (48, 16)], stroke='blue',
         marker_start=dot, marker_mid=chevron, marker_end=arrowhead)
