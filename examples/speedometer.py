####################################################################
# Use Simple Inkscape Scripting to draw an unnumbered speedometer. #
####################################################################

# Define some drawing parameters.
r1 = width/4
r2 = r1*0.90
r3 = r1*0.80
r4 = r1*0.75
r5 = r1*0.15
cx, cy = width/2, height/2

# Draw the background.
circle((cx, cy), r1, fill='black')
ang1, ang2 = pi*0.75, pi*2.25

# Draw the tick marks.
for tick in range(0, 240 + 4, 4):
    # Compute the outer and inner coordinates of each tick.
    rr = r3
    if tick % 20 == 0:
        rr = r4
    ang = (ang2 - ang1)*tick/240 + ang1
    x1 = r2*cos(ang) + cx
    y1 = r2*sin(ang) + cy
    x2 = rr*cos(ang) + cx
    y2 = rr*sin(ang) + cy

    # Draw the tick with an appropriate thickness and color.
    clr = 'white'
    if ang >= pi*1.74:
        clr = 'red'
    thick = 2
    if tick % 20 == 0:
        thick = 6
    line((x1, y1), (x2, y2),
         stroke_width=thick, stroke=clr, stroke_linecap='round')

# Draw the surrounding edge.
arc((cx, cy), r2, (ang1, ang2),
    stroke_width=15, stroke='white', stroke_linecap='square')

# Draw the needle.
ang = pi*1.3
x = r3*cos(ang) + cx
y = r3*sin(ang) + cy
line((cx, cy), (x, y), stroke_width=8, stroke='orange')
circle((cx, cy), r5, fill='#303030')
