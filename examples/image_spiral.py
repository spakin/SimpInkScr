# Use Simple Inkscape Scripting to draw a spiral out of Inkscape logos
# downloaded from the Web.

img_src = 'https://media.inkscape.org/static/images/inkscape-logo.png'
img = None
ang = 0
scale_tr = Transform()
scale_tr.add_scale(0.5)
unmove_tr = Transform()
for rad in range(300, 70, -1):
    x = rad*cos(ang*pi/180) + width/2
    y = rad*sin(ang*pi/180) + height/2
    move_tr = Transform()
    move_tr.add_translate(x, y)
    if img is None:
        img = image(img_src, (0, 0), embed=False, transform=move_tr*scale_tr)
        unmove_tr.add_translate(-x, -y)
    else:
        clone(img, transform=move_tr*unmove_tr)
    ang += 14
