Simple Inkscape Scripting Examples
==================================

This directory provides a number of examples demonstrating the breadth of Simple Inkscape Scripting's capabilities.

Recommended document parameters
-------------------------------

The examples in this directory generally assume a "user unit" is about the size of a pixel (roughly 1/100" or 1/4 mm) and that the page size is at least 600×600 user units.  See [Units](https://inkscape.gitlab.io/extensions/documentation/units.html) for a detailed explanation of how units and viewboxes work in SVG and Inkscape.

If some of the output from the examples appears with abnormally thick lines or crowded shapes or comes out much larger than the page size, use Inkscape's Document Properties dialog box to alter the page size and scale/viewbox, e.g. to a page of 1024×768px and a viewbox of 1024×768.  The following Simple Inkscape Scripting code automates that task:

```Python
canvas.true_width = 1024
canvas.true_height = 768
canvas.viewbox = [0, 0, 1024, 768]
```

List of examples
----------------

| Example | Description |
| :------ | :---------- |
| [Animation](animation.py) | Demonstrate how to create an SVG SMIL animation. |
| [Binary tree](binary_tree.py) | Draw a binary tree.  The canvas should be about as wide as A4 or U.S. Letter paper to avoid node overlap in the deepest level of the tree. |
| [Boolean ops](boolean_ops.py) | Apply Boolean path operations to various objects. |
| [Brick pyramid](brick_pyramid.py) | Draw a brick pyramid. |
| [Chalkboard](chalkboard.py) | Draw a chalkboard with a repeated message written on it. |
| [Clipping path](clipping_path.py) | Demonstrate how to apply a clipping path to a number of objects. |
| [Clone wave](clone_wave.py) | Draw a wave of cloned objects. |
| [Drop shadow](drop_shadow.py) | Draw a circle with a drop shadow. |
| [Ellipses](ellipses.py) | Draw concentric ellipses. |
| [Gradient template](gradient_template.py) | Show how to reuse a gradient pattern. |
| [Guides](guides.py) | Place guides in the document |
| [Holes](holes.py) | Draw a few shapes with holes in them. |
| [Html](html.py) | Embed HTML code within an SVG image. |
| [Hyperlinks](hyperlinks.py) | Create a set of graphical hyperlinks. |
| [Image spiral](image_spiral.py) | Draw a spiral out of Inkscape logos downloaded from the Web. |
| [Inkex paths](inkex_paths.py) | Show how to draw a path using the functions provided by the inkex.paths module (https://tinyurl.com/2p9dna4f) as an alternative to path commands expressed as alternating strings and floats. |
| [Linear gradient](linear_gradient.py) | Fill a shape with a gradient pattern. |
| [Markers](markers.py) | Draw arrows with begin, middle, and ending markers. |
| [Mask](mask.py) | Demonstrate how to apply a mask to a number of objects. |
| [Metadata](metadata.py) | Add metadata to an image. |
| [Move rectangles](move_rectangles.py) | Move all rectangles in the image 2cm to the right.  All other shapes are left alone. |
| [New layer](new_layer.py) | Add a layer to an image. |
| [Overlapping circles](overlapping_circles.py) | Draw an array of hundreds of overlapping circles. |
| [Path effects](path_effects.py) | Demonstrate the application of live path effects to a curve. |
| [Pixels to rectangles](pixels_to_rectangles.py) | Show how to use the Python Imaging Library to convert each pixel of a bitmapped image to a colored rectangle. |
| [Poly by angle](poly_by_angle.py) | Draw (possibly self-intersecting) polygons. |
| [Screen vs print](screen_vs_print.py) | Create a printable page that is differently sized and disjoint from the main canvas. |
| [Sierpinski triangle](sierpinski_triangle.py) | Draw a colorful Sierpinski triangle. |
| [Speedometer](speedometer.py) | Draw an unnumbered speedometer. |
| [Star groups](star_groups.py) | Draw rows of stars with the stars in each row grouped together. |
| [Stroke to path](stroke_to_path.py) | Invoke Inkscape's *Path* → *Stroke to Path* function. |
| [Text flow](text_flow.py) | Flow text into a frame. |
| [Text path](text_path.py) | Place text on a curved path. |
| [Turtle spiral](turtle_spiral.py) | Create a path using turtle graphics and render it. |
| [Units](units.py) | Demonstrate the use of explicitly specified units . |

### Notes

* [Animation](animation.py) produces an animated SVG image, but Inkscape has no mechanism for rendering animations.  Save the resulting SVG file and open it in a Web browser to watch the animation.

* [Poly by angle](poly_by_angle.py) only defines a function; it does not by itself draw anything on the page.  Read the header comments for usage instructions.
