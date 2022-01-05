Simple Inkscape Scripting Examples
==================================

This directory provides a number of examples demonstrating the breadth of Simple Inkscape Scripting's capabilities.

Recommended document parameters
-------------------------------

The examples in this directory generally assume a "user unit" is about the size of a pixel (roughly 1/100" or 1/4 mm) and that the page size is at least 600×600 user units.  See [Units](https://inkscape.gitlab.io/extensions/documentation/units.html) for a detailed explanation of how units and viewboxes work in SVG and Inkscape.

If some of the output from the examples appears with abnormally thick lines or crowded shapes or comes out much larger than the page size, use Inkscape's Document Properties dialog box to alter the page size and scale/viewbox.  Alternatively, the following Simple Inkscape Scripting code automatically sets the page size to 1024×768 (nominal) pixels and imposes a 1:1 ratio of user units to pixels:

```Python
svg_root.set('width', 1024)
svg_root.set('height', 768)
svg_root.set('viewBox', '0 0 1024 768')
```

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

### Notes

* [Animation](animation.py) produces an animated SVG image, but Inkscape has no mechanism for rendering animations.  Save the resulting SVG file and open it in a Web browser to watch the animation.

* [Poly by angle](poly_by_angle.py) only defines a function; it does not by itself draw anything on the page.  Read the header comments for usage instructions.
