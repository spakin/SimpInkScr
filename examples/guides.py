#################################################################
# Use Simple Inkscape Scripting to place guides in the document #
#################################################################

margin = 0.1    # Fraction of width or height
g_left = guide((width*margin, height/2), -90)
g_right = guide((width - width*margin, height/2), -90)
g_top = guide((width/2, height*margin), 0)
g_bottom = guide((width/2, height - height*margin), 0)
guides.extend([g_left, g_right, g_top, g_bottom])
