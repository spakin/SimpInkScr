# Show how Simple Inkscape Scripting can draw a path using the functions
# provided by the inkex.paths module
# (https://inkscape.gitlab.io/extensions/documentation/source/inkex.paths.html)
# as an alternative to path commands expressed as alternating strings and
# floats.

cmds = [Move(0, 0)]
for i in range(0, 10, 2):
    cmds.append(Smooth((i + 1)*100, 100, (i + 2)*100, 0))
path(cmds, transform='translate(0, 100)', stroke_width=4, stroke='magenta')
