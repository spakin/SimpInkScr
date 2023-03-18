####################################################################
# Use Simple Inkscape Scripting to draw a binary tree.  The canvas #
# should be about as wide as A4 or U.S. Letter paper to avoid node #
# overlap in the deepest level of the tree.                        #
####################################################################


def tree_from(cx, cy, rad, hsep, vsep, depth, max_depth):
    'Recursively draw a binary tree.'
    left, right = None, None
    if depth < max_depth:
        left = tree_from(cx - hsep, cy + vsep, rad,
                         hsep/2, vsep,
                         depth + 1, max_depth)
        right = tree_from(cx + hsep, cy + vsep, rad,
                          hsep/2, vsep,
                          depth + 1, max_depth)
    c = circle((cx, cy), rad)
    if left is not None:
        connector(c, left, fill='none')
        connector(c, right, fill='none')
    return c


style(stroke_width=2, fill='#f4e3d7')
tree_from(cx=canvas.width/2, cy=20, rad=10,
          hsep=canvas.width/4, vsep=50,
          depth=0, max_depth=5)
