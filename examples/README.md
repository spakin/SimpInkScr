Simple Inkscape Scripting Examples
==================================

This directory provides a number of examples demonstrating the breadth of Simple Inkscape Scripting's capabilities.

Recommended document parameters
-------------------------------

The examples in this directory generally assume a "user unit" is about the size of a pixel (roughly 1/100" or 1/4 mm) and that the page size is at least 600×600 user units.  The following Simple Inkscape Scripting code automatically sets the page size to 1024×768 (nominal) pixels and imposes a 1:1 ratio of user units to pixels:

```Python
svg_root.set('width', 1024)
svg_root.set('height', 768)
svg_root.set('viewBox', '0 0 1024 768')
```

## Explanation

Most of the examples in this directly work in terms of SVG "user units".  For example, `line((10, 10), (110, 10), stroke_width=2)` says to draw a line that is 100 user units wide and has a thickness of 2 user units.  While this is more convenient than specifying absolute units, e.g., `line((2.7*mm, 2.7*mm), (29.2*mm, 2.7*mm), stroke_width=0.53*mm)`, it comes at the cost of portability.

Although a user unit is commonly the size of a (nominal) pixel, it can be redefined arbitrarily.  (In Inkscape, the Document Properties dialog provides "scale" and "viewbox" widgets for this purpose.)  If a user unit is defined as, say, 1cm, then `line((10, 10), (110, 10), stroke_width=2)` will produce a much longer, much thicker line than if the user unit is defined to be closer to the size of a pixel.  While this feature may be desirable when writing your own scripts, it implies that the provided examples will look different depending on the current document properties.

See [Units](https://inkscape.gitlab.io/extensions/documentation/units.html) for a detailed description of how units work in SVG and Inkscape.

## Troubleshooting

If the examples produce distorted output (e.g., abnormally thick lines, crowded shapes, or pictures much larger than the page size), your document probably does not abide by the [recommended document parameters](#recommended-document-parameters) listed above.  Run the following Simple Inkscape Scripting script to help you troubleshoot:

```Python
################################################################
# Issue warnings if the Inkscape page is inappropriately sized #
# for the Simple Inkscape Scripting example scripts.           #
################################################################

print('Image dimension in pixels: %.1f by %.1f' % (width, height))
if width < 600:
    print('WARNING: Image is a bit narrow')
if height < 600:
    print('WARNING: Image is a bit short')
print('')

vbox = [float(e) for e in svg_root.get('viewBox').split()]
vwd = vbox[2] - vbox[0]
vht = vbox[3] - vbox[1]
swd = inkex.units.convert_unit(svg_root.get('width'), "px")
sht = inkex.units.convert_unit(svg_root.get('height'), "px")
print('Pixels per user-space unit: %.1f (H) and %.1f (V)' % (swd/vwd, sht/vht))
if not 0.75 < swd/vwd < 1.5:
    print('WARNING: Horizontal ratio is far from 1.0')
if not 0.75 < sht/vht < 1.5:
    print('WARNING: Vertical ratio is far from 1.0')
if abs(swd/vwd - sht/vht) > 1e-5:
    print('WARNING: Horizontal and vertical ratios differ')
```

The script will issue warnings for the most common sources of distorted output.
If the examples still do not look as expected, check the list of [existing Simple Inkscape Scripting issues](https://github.com/spakin/SimpInkScr/issues?q=is%3Aissue) for a solution and submit a new bug report if your problem has not been reported previously.

List of examples
----------------

| Example | Description |
| :------ | :---------- |
| [Animation](animation.py) | Demonstrate the use of Simple Inkscape Scripting to create an SVG SMIL animation. |
| [Binary tree](binary_tree.py) | Use Simple Inkscape Scripting to draw a binary tree.  The canvas should be about as wide as A4 or U.S. Letter paper to avoid node overlap in the deepest level of the tree. |
| [Brick pyramid](brick_pyramid.py) | Use Simple Inkscape Scripting to draw a brick pyramid. |
| [Chalkboard](chalkboard.py) | Use Simple Inkscape Scripting to draw a chalkboard with a repeated message written on it. |
| [Clipping path](clipping_path.py) | Demonstrate how to apply a clipping path to a number of objects using Simple Inkscape Scripting. |
| [Clone wave](clone_wave.py) | Use Simple Inkscape Scripting to draw a wave of cloned objects. |
| [Drop shadow](drop_shadow.py) | Use Simple Inkscape Scripting to draw a circle with a drop shadow. |
| [Ellipses](ellipses.py) | Use Simple Inkscape Scripting to draw concentric ellipses. |
| [Gradient template](gradient_template.py) | Use Simple Inkscape Scripting to show how to reuse a gradient pattern. |
| [Hyperlinks](hyperlinks.py) | Use Simple Inkscape Scripting to create a set of graphical hyperlinks. |
| [Image spiral](image_spiral.py) | Use Simple Inkscape Scripting to draw a spiral out of Inkscape logos downloaded from the Web. |
| [Inkex paths](inkex_paths.py) | Show how Simple Inkscape Scripting can draw a path using the functions provided by the inkex.paths module (https://tinyurl.com/2p9dna4f) as an alternative to path commands expressed as alternating strings and floats. |
| [Linear gradient](linear_gradient.py) | Use Simple Inkscape Scripting to fill a shape with a gradient pattern. |
| [Markers](markers.py) | Use Simple Inkscape Scripting to draw arrows with begin, middle, and ending markers. |
| [New layer](new_layer.py) | Use Simple Inkscape Scripting to add a layer to an image. |
| [Overlapping circles](overlapping_circles.py) | Use Simple Inkscape Scripting to draw an array of hundreds of overlapping circles. |
| [Poly by angle](poly_by_angle.py) | Use Simple Inkscape Scripting to draw (possibly self-intersecting) polygons. |
| [Sierpinski triangle](sierpinski_triangle.py) | Use Simple Inkscape Scripting to draw a colorful Sierpinski triangle. |
| [Speedometer](speedometer.py) | Use Simple Inkscape Scripting to draw an unnumbered speedometer. |
| [Star groups](star_groups.py) | Use Simple Inkscape Scripting to draw rows of stars with the stars in each row grouped together. |
| [Text flow](text_flow.py) | Use Simple Inkscape Scripting to flow text into a frame. (The text shown is an original haiku by Scott Pakin, 26-Nov-2021.) |
| [Text path](text_path.py) | Use Simple Inkscape Scripting to place text on a curved path. |
| [Turtle spiral](turtle_spiral.py) | Create a path using turtle graphics and render it using Simple Inkscape Scripting. |
| [Units](units.py) | Demonstrate the use of explicitly specified units in Simple Inkscape Scripting. |

## Notes

* [Animation](animation.py) produces an animated SVG image, but Inkscape has no mechanism for rendering animations.  Save the resulting SVG file and open it in a Web browser to watch the animation.

* [Poly by angle](poly_by_angle.py) only defines a function; it does not by itself draw anything on the page.  Read the header comments for usage instructions.
