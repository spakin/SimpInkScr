########################################################################
# Use Simple Inkscape Scripting to draw a spiral out of Inkscape logos #
# downloaded from the Web.                                             #
########################################################################

img_src = 'https://media.inkscape.org/static/images/inkscape-logo.png'
img = image(img_src, (0, 0), embed=False, transform='scale(0.5)').to_def()
ang = 0
for rad in range(300, 70, -1):
    x = rad*cos(ang*pi/180) + canvas.width/2
    y = rad*sin(ang*pi/180) + canvas.height/2
    move_tr = inkex.Transform()
    move_tr.add_translate(x, y)
    clone(img, transform=move_tr)
    ang += 14
