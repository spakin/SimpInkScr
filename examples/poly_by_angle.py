##########################################################################
# Use Simple Inkscape Scripting to draw (possibly self-intersecting)     #
# polygons.                                                              #
#                                                                        #
# Usage: Point to this file in Simple Inkscape Scripting's "Python file" #
# field.  Then, include text to invoke poly_by_angle in the "Python      #
# code" field.  For example, here's a boring, old square:                #
#                                                                        #
#   poly_by_angle(90, 100)                                               #
#                                                                        #
# Here's a 7-pointed star (technically, a {7/2} heptagram) inscribed     #
# within a heptagon:                                                     #
#                                                                        #
#   style(stroke_width=4, stroke='yellow')                               #
#   poly_by_angle(360/7, 100, fill='#800080')                            #
#   poly_by_angle(2*360/7, 100, fill='none')                             #
#                                                                        #
# Here are some stars with lots more points:                             #
#                                                                        #
#   poly_by_angle(140, 200, stroke='#008000')                            #
#   poly_by_angle(140, 70, stroke='#00ff00')                             #
##########################################################################

def poly_by_angle(ang, rad, *args, **kwargs):
    '''Draw a (possibly self-intersecting) polygon given an angle in
    degrees for each corner.'''
    pts = [(rad, 0)]
    a = (ang + 360) % 360
    while abs(a) > 1e-10:
        x = rad*cos(a*pi/180)
        y = rad*sin(a*pi/180)
        pts.append((x, y))
        a = (a + ang) % 360
    polygon(pts, *args, **kwargs)
