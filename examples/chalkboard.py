######################################################################
# Use Simple Inkscape Scripting to draw a chalkboard with a repeated #
# message written on it.                                             #
######################################################################

msg = 'I will not talk in class.'
rect((0, 0), (700, 400), stroke_width=10, stroke='#aa4400', fill='#004000')
for y in range(50, 400, 40):
    text(msg + '  ' + msg, (30, y),
         fill='white', font_family='Comic Sans MS', font_size='30')
