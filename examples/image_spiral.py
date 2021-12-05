# Use Simple Inkscape Scripting to draw a spiral out of Inkscape logos
# downloaded from the Web.

img = 'https://media.inkscape.org/static/images/inkscape-logo.png'
ang = 0
scale_tr = Transform()
scale_tr.add_scale(0.5)
for rad in range(300, 70, -1):
    x = rad*cos(ang*pi/180) + width/4
    y = rad*sin(ang*pi/180) + height/4
    move_tr = Transform()
    move_tr.add_translate(x, y)
    image(img, (width/2, height/2), embed=False, transform=move_tr*scale_tr)
    ang += 14
