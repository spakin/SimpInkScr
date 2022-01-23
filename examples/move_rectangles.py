#########################################################################
# Use Simple Inkscape Scripting to move all rectangles in the image 2cm #
# to the right.  All other shapes are left alone.                       #
#########################################################################

# Change all_shapes to selected_shapes in the following to move only
# selected shapes.

for r in all_shapes():
    if r.tag == 'rect':
        r.svg_set('x', r.svg_get('x') + 2*cm)
