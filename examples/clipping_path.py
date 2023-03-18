###################################################################
# Demonstrate how to apply a clipping path to a number of objects #
# using Simple Inkscape Scripting.                                #
###################################################################

# Define a circular clipping path.
edge = min(canvas.width, canvas.height)
circle_clip = clip_path(circle((canvas.width/2, canvas.height/2), 0.9*edge/2))

# Draw a black background clipped to the clipping path.
rect((0, 0), (canvas.width, canvas.height),
     stroke='none', fill='black', clip_path=circle_clip)

# Draw a grid of stars, each clipped to the clipping path.
all_colors = ['cyan', 'magenta', 'yellow']
sep = edge/10
row, col = 0, 0
for y in range(ceil(sep/2), ceil(canvas.height), ceil(sep)):
    for x in range((row % 2)*ceil(sep/2), ceil(canvas.width), ceil(sep)):
        color = all_colors[(row + col) % len(all_colors)]
        star(8, (x, y), (sep/2.5, sep/5.0),
             stroke_width=2, stroke='white', fill=color, clip_path=circle_clip)
        col += 1
    row += 1
