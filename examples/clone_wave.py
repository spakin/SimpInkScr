#######################################################################
# Use Simple Inkscape Scripting to draw a wave of cloned objects.     #
#                                                                     #
# Try rotating, scaling, or recoloring the original (leftmost) object #
# in the Inkscape GUI and seeing how all the other objects change     #
# accordingly.                                                        #
#######################################################################

mark = regular_polygon(5, (0, canvas.height/2), 10, fill='#55ddff')
for a in range(5, 360, 5):
    x = a*canvas.width/360
    y = sin(a*pi/180)*canvas.height/2 + canvas.height/2
    tr = inkex.Transform()
    tr.add_translate(x, y - canvas.height/2)
    clone(mark, transform=tr)
