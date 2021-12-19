##########################################################################
# Use Simple Inkscape Scripting to create a set of graphical hyperlinks. #
##########################################################################

# Create two ordinary hyperlinks.  Although the title is optional,
# its use is recommended.
github = circle((50, 50), 40, fill='red')
hyperlink(github, 'https://github.com/spakin/SimpInkScr',
          title='Simple Inkscape Scripting home page')
wiki = circle((150, 50), 40, fill='yellow')
hyperlink(wiki, 'https://github.com/spakin/SimpInkScr/wiki',
          title='Simple Inkscape Scripting documentation')

# Demonstrate that a hyperlink can contain multiple objects.
gallery_big = circle((50, 150), 40, fill='#008000')
gallery_small = circle((50, 150), 15, fill='#00ff00')
hyperlink([gallery_big, gallery_small],
          'https://inkscape.org/~pakin/%E2%98%85simple-inkscape-scripting',
          title='Simple Inkscape Scripting extension page')

# Show that hyperlinks can have styles, which apply to their contents.
# The content's style overrides the hyperlink's style so we need to
# use a stroke color of None here (the default for a circle is black)
# to allow the hyperlink's stroke color to take effect.
inkscape = circle((150, 150), 40, fill='blue', stroke=None)
hyperlink(inkscape, 'https://inkscape.org/', title='Inkscape home page',
          stroke='#5599ff', stroke_width=4)

# The cyan link opens in a separate browser tab.
home = circle((50, 250), 40, fill='cyan')
hyperlink(home, 'https://www.pakin.org/~scott',
          title="Scott Pakin's home page", target='_blank')

# The magenta link provides a hint that its target is a GIF image.
gif = circle((150, 250), 40, fill='magenta')
hyperlink(gif, 'https://www.pakin.org/graphics/ScottSSJ.gif',
          title='Animation of Scott Pakin morphing into a Super Saiyan',
          mime_type='image/gif')
