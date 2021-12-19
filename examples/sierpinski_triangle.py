#########################################################################
# Use Simple Inkscape Scripting to draw a colorful Sierpinski triangle. #
#########################################################################

def eq_triangle(tx, ty, edge, **style):
    """Draw an equilateral triangle with a given top coordinate and
    edge position.  Return the triangle's height."""
    ht = sqrt(3)*edge/2
    polygon([(tx, ty), (tx + edge/2, ty + ht), (tx - edge/2, ty + ht)],
            **style)
    return ht


def sierpinski(tx, ty, edge, depth, colors):
    '''Draw a Sierpinski triangle to a given depth until a set of colors
    runs out.'''
    max_depth = len(colors)
    if depth >= max_depth:
        return
    ht = eq_triangle(tx, ty, edge, fill=colors[depth % len(colors)])
    sierpinski(tx, ty, edge/2, depth + 1, colors)
    sierpinski(tx - edge/4, ty + ht/2, edge/2, depth + 1, colors)
    sierpinski(tx + edge/4, ty + ht/2, edge/2, depth + 1, colors)


edge = min(width, height)/2
colors = ['#ff0000', '#00ff00', '#0000ff', '#00ffff', '#ff00ff', '#ffff00']
sierpinski(width/2, 50, edge, 0, colors)
