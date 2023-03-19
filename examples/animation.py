#####################################################################
# Demonstrate the use of Simple Inkscape Scripting to create an SVG #
# SMIL animation.                                                   #
#####################################################################

# Force the image to a known size.
canvas.true_width = 1024
canvas.true_height = 768
canvas.viewbox = [0, 0, 1024, 768]

# Define the final configuration of the graphics.
style(font_size='42pt', font_family='Arial Black; Arial, Bold; serif',
      fill='#000080', opacity=1)
simple_final = text('Simple', (353, 330))
inkscape_final = text('Inkscape', (355, 400))
scripting_final = text('Scripting', (0, 0))  # Path (below) ends at (353, 471).

# Move "Simple" in a straight line from the lower-left corner of the image
# to a position near the lower right to a position near the upper right to
# its final position near the center.  The word starts fully transparent
# and fades to fully opaque as it moves.
simple_init = text('Simple', (0, 768), opacity=0)
simple_mid1 = text('Simple', (800, 600), opacity=1/3)
simple_mid2 = text('Simple', (600, 100), opacity=2/3)
simple_init.animate([simple_mid1, simple_mid2, simple_final], duration='3s')

# Start "Inkscape" in a giant font and with a different color, rotation,
# and translation.  Smoothly alter all of these to their target values.
inkscape_init = text('Inkscape', (-800, -800), font_size='420pt',
                     fill='#ff6600', transform='rotate(135)')
inkscape_init.animate(inkscape_final, duration='3.5s')

# Define a path along which to move "Scripting".
scripting_path = path([Move(1152, 336),
                       Curve(784, 64, 432, 0, 197, 145),
                       Curve(-176, 368, 171, 471, 353, 471)],
                      fill='none').to_def()
scripting_final.animate(path=scripting_path, path_rotate='auto',
                        duration='4s')
