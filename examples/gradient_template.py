##########################################################################
# Use Simple Inkscape Scripting to show how to reuse a gradient pattern. #
##########################################################################

edge = 100  # Size of each edge

# Define a gradient pattern with both sharp and smooth color changes
# but no starting or ending points.
smooth_sharp = linear_gradient()
smooth_sharp.add_stop(0.00, 'cyan', opacity=0)
smooth_sharp.add_stop(0.39, 'green')
smooth_sharp.add_stop(0.40, 'white')
smooth_sharp.add_stop(0.49, 'white')
smooth_sharp.add_stop(0.50, 'red')
smooth_sharp.add_stop(0.59, 'red')
smooth_sharp.add_stop(0.60, 'white')
smooth_sharp.add_stop(0.69, 'white')
smooth_sharp.add_stop(0.70, 'green')
smooth_sharp.add_stop(1.00, 'cyan', opacity=0)

# Define a left-to-right version of the pattern (the default,
# actually), and draw a square using it.
l2r = linear_gradient((0, 0), (1, 0), template=smooth_sharp)
rect((0, 0), (edge, edge), fill=l2r)

# Define a top-to-bottom version of the pattern, and draw a square
# using it.
t2b = linear_gradient((0, 0), (0, 1), template=smooth_sharp)
rect((0, 0), (edge, edge), fill=t2b,
     transform='translate(%g, %g)' % (edge*2, 0))

# Define a diagonal version of the pattern and draw a square using it.
diag = linear_gradient((0, 0), (1, 1), template=smooth_sharp)
rect((0, 0), (edge, edge), fill=diag,
     transform='translate(%g, %g)' % (edge*4, 0))

# Define a diagonal version of the pattern that doesn't extend all the
# way to the corners, and draw a square using it.
partial_diag = linear_gradient((1/4, 1/4), (3/4, 3/4),
                               template=smooth_sharp)
rect((0, 0), (edge, edge), fill=partial_diag,
     transform='translate(%g, %g)' % (0, edge*2))

# Define a diagonal version of the pattern that repeats a few times,
# and draw a square using it.
diag3 = linear_gradient((0, 0), (1/3, 1/3), repeat='direct',
                        template=smooth_sharp)
rect((0, 0), (edge, edge), fill=diag3,
     transform='translate(%g, %g)' % (edge*2, edge*2))

# Define a radial version of the pattern, and draw a square using it.
# Note that it's allowed for a radial gradient to use a linear
# gradient as a template.
rad = radial_gradient((0.5, 0.5), 0.5, template=smooth_sharp)
rect((0, 0), (edge, edge), fill=rad,
     transform='translate(%g, %g)' % (edge*4, edge*2))

# Do the same as above but with a larger pattern radius.
rad_big = radial_gradient((0.5, 0.5), sqrt(0.5), template=smooth_sharp)
rect((0, 0), (edge, edge), fill=rad_big,
     transform='translate(%g, %g)' % (0, edge*4))

# Define a radial version of the pattern but with the center (of the
# final colored circle) on the right and the focal point (center of
# the initial colored circle) near the left.  Draw a square using
# this pattern.
rad_focus = radial_gradient((1, 0.5), 1.0,
                            (0.1, 0.5), 0.0,
                            template=smooth_sharp)
rect((0, 0), (edge, edge), fill=rad_focus,
     transform='translate(%g, %g)' % (edge*2, edge*4))

# Define a radial version of the pattern with a slight translation and
# a skew of 20 degrees, and draw a square using this pattern.
rad_skew = radial_gradient((0.5, 0.5), 0.5, template=smooth_sharp,
                           transform='skewX(20) translate(-0.2, 0)')
rect((0, 0), (edge, edge), fill=rad_skew,
     transform='translate(%g, %g)' % (edge*4, edge*4))
