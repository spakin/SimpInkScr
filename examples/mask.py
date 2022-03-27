##########################################################
# Demonstrate how to apply a mask to a number of objects #
# using Simple Inkscape Scripting.                       #
##########################################################

# --------------------------------------------------------------------------
# NOTE: This example requires Inkscape 1.2+.  It is also best applied to
# a document in landscape orientation.
# --------------------------------------------------------------------------

# Construct a textual mask.
cx, cy = width/2, height/2
t = text('Wow!', (cx, cy), fill='white',
         text_anchor='middle', dominant_baseline='middle',
         font='Arial;sans', font_weight='bold',
         font_size=min(width/2, height/2))
text_mask = mask(t)

# Draw colored concentric ellipses.
dec = width/50
rx, ry = width, height
while rx > 0 and ry > 0:
    rd, gr, bl = randint(0, 255), randint(0, 255), randint(0, 255)
    ellipse((cx, cy), (rx, ry), mask=text_mask,
            fill='#%02X%02X%02X' % (rd, gr, bl))
    rx -= dec
    ry -= dec
