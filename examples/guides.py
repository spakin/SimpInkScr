#################################################################
# Use Simple Inkscape Scripting to place guides in the document #
#################################################################

margin = 0.1    # Fraction of width or height
g_left = guide((canvas.width*margin, canvas.height/2), -90)
g_right = guide((canvas.width - canvas.width*margin, canvas.height/2), -90)
g_top = guide((canvas.width/2, canvas.height*margin), 0)
g_bottom = guide((canvas.width/2, canvas.height - canvas.height*margin), 0)
guides.extend([g_left, g_right, g_top, g_bottom])
