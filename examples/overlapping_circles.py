#################################################################
# Use Simple Inkscape Scripting to draw an array of hundreds of #
# overlapping circles.                                          #
#################################################################

rad = 30
edge = 10

style(fill_opacity=0.5)
for r in range(edge):
    for c in range(edge):
        circle((c*rad*2 + rad, r*rad*2 + rad), rad, fill='red')
for r in range(edge - 1):
    for c in range(edge - 1):
        circle((c*rad*2 + rad*2, r*rad*2 + rad*2), rad, fill='yellow')
