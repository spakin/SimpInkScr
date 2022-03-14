#################################################################
# Use Simple Inkscape Scripting to place guides in the document #
#################################################################

margin = 0.1    # Fraction of width or height
g_left = Guide((width*margin, height/2), -90)
g_right = Guide((width - width*margin, height/2), -90)
g_top = Guide((width/2, height*margin), 0)
g_bottom = Guide((width/2, height - height*margin), 0)
guides.extend([g_left, g_right, g_top, g_bottom])
