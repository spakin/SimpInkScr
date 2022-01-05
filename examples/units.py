########################################################################
# Demonstrate the use of explicitly specified units in Simple Inkscape #
# Scripting.                                                           #
########################################################################

# Define some program parameters.
tx, ty = 18*pt, 36*pt
y_inc = 3*cm
lx, ly = 8*cm, ty - 4*pt
style(font_size=18*pt, font_family='serif')


def show_units(name, factor, row):
    'Present a single unit.'
    text('10\u00d71 %s:' % name, (tx, ty + row*y_inc))
    line((lx, ly + row*y_inc), (lx + 10*factor, ly + row*y_inc),
         stroke_width=1*factor, stroke='blue')


# Compare various units.
show_units('user units',  1,    0)
show_units('pixels',      px,   1)
show_units('points',      pt,   2)
show_units('millimeters', mm,   3)
show_units('centimeters', cm,   4)
show_units('inches',      inch, 5)
