##############################################################
# Use Simple Inkscape Scripting to draw concentric ellipses. #
##############################################################

for i in range(10, 0, -1):
    ellipse((width/2, height/2), (i*30, i*20 + 10),
            fill='#0000%02x' % (255 - 255*i//10), stroke='white')
