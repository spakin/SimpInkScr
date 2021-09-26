# Use Simple Inkscape Scripting to draw a spiral out of Inkscape logos
# downloaded from the Web.

img = 'https://media.inkscape.org/static/images/inkscape-logo.png'
ang = 0
for rad in range(300, 50, -1):
    x = rad*cos(ang*pi/180) + width/4
    y = rad*sin(ang*pi/180) + height/4
    image(img, (width/2, height/2), embed=False,
          transform='translate(%g, %g) scale(0.5)' % (x, y))
    ang += 14
