##########################################################
# Use Simple Inkscape Scripting to draw a brick pyramid. #
##########################################################

bwd, bht = 60, 30
for row in range(1, 11):
    x0, y0 = (canvas.width - row*bwd)/2, row*bht
    for col in range(row):
        red = '#%02x0000' % randint(64, 192)
        rect((x0 + col*bwd, y0), (x0 + (col + 1)*bwd, y0 + bht), fill=red)
