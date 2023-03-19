####################################################################
# Use Simple Inkscape Scripting to create a printable page that is #
# differently sized and disjoint from the main canvas.             #
####################################################################

# Set the canvas to 15x15cm.
canvas.true_width = '15cm'
canvas.true_height = '15cm'
canvas.viewbox = [0, 0, 100, 100]

# Draw on the canvas.
wd, ht = canvas.width, canvas.height
circle((wd/2, ht/2), 0.9*canvas.width/2, stroke_width='3pt', stroke='#008000')
text('This is what you see on screen.', (wd/2, ht/2),
     font_size='5px', font_family='"Bitstream Vera Sans", sans-serif',
     text_anchor='middle', fill='#3737c8')

# Create a portrait A4 page.
p1 = page('1', (canvas.width + 1*cm, 0), (210*mm, 297*mm))
p1_bbox = p1.bounding_box()
regular_polygon(3, (p1_bbox.center_x, p1_bbox.center_y),
                0.9*p1.width/2,
                stroke_width='3pt', stroke='#008000')
text('This is what you see in print.',
     (p1_bbox.center_x, p1_bbox.center_y + 4*24*pt),
     font_size='24pt', font_family='"Bitstream Vera Sans", sans-serif',
     text_anchor='middle', fill='#3737c8')
