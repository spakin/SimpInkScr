######################################################################
# Use Simple Inkscape Scripting to draw rows of stars with the stars #
# in each row grouped together.                                      #
######################################################################

rad = canvas.width/50
style(stroke_width=2)
for j in range(10):
    y = j*rad*4 + 2*rad
    style(fill='#%02x%02x%02x' %
          (randint(128, 255), randint(128, 255), randint(128, 255)))
    g = group()
    for i in range(10 + j):
        x = i*(canvas.width - 2*rad)/(10 + j - 1) + rad
        s = star(6, (x, y), (rad, rad*0.575))
        g.append(s)
