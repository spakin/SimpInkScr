######################################################################
# Use Simple Inkscape Scripting to flow text into a frame.           #
# (The text shown is an original haiku by Scott Pakin, 26-Nov-2021.) #
######################################################################

sun = path(['M', 0, 150,
            'C', 0, 68, 68, 0, 150, 0,
            232, 0, 300, 68, 300, 150],
           transform='translate(%.5g, %.5g)' % (width/2 - 150, height/2 - 75),
           fill='#380000', stroke='none')
t = text('The sun sets early, ', (0, 0),
         font_family='"Zapf Chancery", "TeX Gyre Chorus", cursive',
         text_align='justify', font_size='24px', fill='#fdaa30',
         shape_inside=sun)
t.add_text('crimson rays obscured by clouds; ', fill='#fb6854')
t.add_text('a cold darkness spreads.', fill='#fd4539')
