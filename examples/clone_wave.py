# Use Simple Inkscape Scripting to draw a wave of cloned objects.
#
# Try rotating, scaling, or recoloring the original (leftmost) object
# and seeing how all the other objects change accordingly.

mark = regular_polygon(5, (0, height/2), 10, fill='#55ddff')
for a in range(5, 360, 5):
    x = a*width/360
    y = sin(a*pi/180)*height/2 + height/2
    clone(mark,
          transform='translate(%.5g, %.5g) translate(0, %.5g)' %
          (x, y, -height/2))
