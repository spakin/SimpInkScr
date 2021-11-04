Simple Inkscape Scripting
=========================

Description
-----------

In the [Inkscape](https://inkscape.org/) vector-drawing program, how would you go about drawing 100 diamonds, each with a random color and placed at a random position on the page?

![diamonds](https://user-images.githubusercontent.com/650041/134632937-bd3c2d21-04d0-47b9-a61b-170de129022c.png)

**Option 1**: Draw, color, and place the diamonds manually.  This is exceptionally tedious.

**Option 2**: Create an [Inkscape extension](https://inkscape-extensions-guide.readthedocs.io/) to automate the process.  This involves gaining familiarity with a large API and writing a substantial amount of setup code just to perform what ought to be a simple task.

Neither option is particularly enticing.  This is why I created the Simple Inkscape Scripting extension for Inkscape.  Simple Inkscape Scripting lets you create shapes in the current Inkscape canvas with a Python script plus a set of simple functions such as `circle` for drawing a circle and `rect` for drawing a rectangle.  The picture shown above was created using just the following five lines of code:
```Python
for i in range(100):
    x, y = uniform(0, width), uniform(0, height)
    rect((-5, -5), (5, 5),
         transform='translate(%g, %g) scale(0.75, 1) rotate(45)' % (x, y),
         fill='#%02x%02x%02x' % (randrange(256), randrange(256), randrange(256)))
```

The first line is an ordinary Python `for` loop.  The second line selects a position for the rectangle.  Note that Simple Inkscape Scripting predefines `width` as the canvas width and `height` as the canvas height.  The `random` package is imported into the current namespace so `uniform` can be invoked directly.  The third line draws a 10×10 pixel rectangle centered on the origin.  The fourth line rotates the rectangle by 45°, squeezes it horizontally into a lozenge, and moves it to the target position.  The fifth line specifies a random fill color.

The diamonds drawn on the canvas are all ordinary Inkscape objects and can be further manipulated using any of the usual Inkscape tools.

In short, Simple Inkscape Scripting helps automate repetitive drawing tasks.  Unlike writing a custom Inkscape extension, Simple Inkscape Scripting requires sufficiently little boilerplate code as to make its use worthwhile even for tasks that will be performed only once or twice.

Installation
------------

First, identify your Inkscape extensions directory.  This can be found in  Inkscape's preferences: Go to *Edit* → *Preferences* → *System* and look in the *User extensions* field.  On Linux, the extensions directory is typically `$HOME/.config/inkscape/extensions/`.

Second, install Simple Inkscape Scripting in that directory or any subdirectory.  For example,
```bash
cd $HOME/.config/inkscape/extensions/
git clone https://github.com/spakin/SimpInkScr.git
```
will retrieve the code from GitHub.  This later can be updated with
```bash
cd $HOME/.config/inkscape/extensions/SimpInkScr/
git pull
```

If Inkscape is already running, exit and restart it to make it look for new extensions.

Usage
-----

### Getting started

Launch the Simple Inkscape Scripting extension from Inkscape via *Extensions* → *Render* → *Simple Inkscape Scripting…*.  This will bring up a dialog box that gives you the option to enter a filename for a Python program or enter Python code directly in a text box.  These options are not mutually exclusive; if both are used, the Python code in the file will be executed first, followed by the Python code in the text box.  This enables one, for example, to define functions in a file and invoke them with different parameters from the text box.

As an initial test, try entering
```Python
circle((100, 100), 50)
```
into the text box and clicking *Apply* then *Close*.  This should create a black circle of radius 50 at position (100, 100).  Due to how "generate extensions" work, Inkscape always places the output of Simple Inkscape Scripting within a group so ungroup it if desired.

See the [`examples` directory](examples/) for a collection of examples that can be run from the Simple Inkscape Scripting dialog box.

### Shape API

All of the following functions return a Simple Inkscape Scripting object, which can be passed to the `connector` and `group` functions.

* `circle((cx, cy), r)`

Draw a circle with center `(cx, cy)` and radius `r`.  *Example*: `circle((width/2, height/2), 50)`

* `ellipse((cx. cy), rx, ry)`

Draw an ellipse with center `(cx, cy)` and radii `rx` and `ry`.  *Example*: `ellipse((width/2, height/2), 75, 50)`

* `rect((x1, y1), (x2, y2))`

Draw a rectangle from `(x1, y1)` to `(x2, y2)`.  *Example*: `rect((width/2 - 50, height/2 - 30), (width/2 + 50, height/2 + 30))`

* `line((x1, y1), (x2, y2))`

Draw a line from `(x1, y1)` to `(x2, y2)`.  *Example*: `line((width, 0), (0, height))`

* `polyline((x1, y1), (x2, y2), …, (xn, yn))`

Draw a polyline (open polygon) from the given coordinates.  *Example*: `polyline((0, 300), (150, 0), (300, 300), (150, 200))`

* `polygon((x1, y1), (x2, y2), …, (xn, yn))`

Draw an arbitrary polygon from the given coordinates.  *Example*: `polygon((0, 300), (150, 0), (300, 300), (150, 200), fill='none')`

* `regular_polygon(sides, (cx, cy), r, ang, round, random)`

Draw a `sides`-sided regular polygon centered at `(cx, cy)` with radius `r`.  All of the remaining arguments are optional.  `ang` is the initial angle in radians and default to −𝜋/2 (upwards).  `round` specifies how much to round the corners and defaults to `0.0` (sharp).  `random` adds an amount of randomness to all vertex coordinates (default `0.0`).  *Example*: `regular_polygon(5, (100, 100), 80)`

* `star(sides, (cx, cy), (rt, rb), (angt, angb), round, random)`

Draw a `sides`-sided star centered at `(cx, cy)` with tip radius `rt` and base radius `rb`.  All of the remaining arguments are optional.  `angt` and `angb` are the tip and base angles in radians and default to angles that do not skew the star and that point it upwards.  `round` specifies how much to round the corners and defaults to `0.0` (sharp).  `random` adds an amount of randomness to all vertex coordinates (default `0.0`).  *Example*: `star(5, (100, 100), (80, 30))`

* `arc((cx. cy), rx, ry, ang1, ang2, [arc_type])`

Draw an arc as a segment of an ellipse with center `(cx, cy)` and radii `rx` and `ry`, ranging clockwise from angle `ang1` to angle `ang2`.  If `arc_type` is `arc`, draw an ordinary arc; if `slice`, draw a pie slice; if `chord`, draw an arc with the endpoints connected with a straight line.  *Example*:
`arc((width/2, height/2), 100, 100, pi/5, 9*pi/5, 'slice', fill='yellow', stroke_width=2)`

* `path(elt, …)`

Draw a path from a list of path commands (strings) and arguments (floats) or a list of `PathCommand`s from [`inkex.paths`](https://inkscape.gitlab.io/extensions/documentation/source/inkex.paths.html).  *Example*: `path('M', 226, 34, 'V', 237, 'L', 32, 185, 'C', 32, 185, 45, -9, 226, 34, 'Z')`
or equivalently,
```Python
from inkex.paths import *
path(Move(226, 34),
     Vert(237),
     Line(32, 185),
     Curve(32, 185, 45, -9, 226, 34),
     ZoneClose())
```

* `connector(obj1, obj2, ctype, curve)`

Draw a path that routes automatically between two Simple Inkscape Scripting objects.  (All functions in the shape API return such an object.)  `ctype` specifies the connector type and must be either `polyline` (any angle, the default) or `orthogonal` (only 90° bends).  `curve` specifies the curvature amount (default `0`).  *Example*: `r = rect((50, 50), (100, 100)); c = circle((200, 200), 25); connector(r, c, ctype='orthogonal', curve=15)`

* `text(msg, (x, y))`

Draw a piece of text starting at `(x, y)`.  *Example*: `text('Simple Inkscape Scripting', (0, height), font_size='36pt')`

* `more_text(msg, (x, y))`

Append to a previous piece of text (created with `text` or `more_text`), possibly changing the style.  The starting coordinates `(x, y)` are optional and can be used, e.g., to begin a new line.  *Example*: `text('Hello, ', (width/2, height/2), font_size='24pt', text_anchor='middle'); more_text('Inkscape', font_weight='bold', fill='#800000'); more_text('!!!')`

* `image(fname, (x, y), embed)`

Include an image.  `fname` is the name of the file to include.  A variety of image formats are supported, but only PNG, JPEG, and SVG are guaranteed to be supported by all SVG viewers.  The upper-left corner of the image will lie at coordinates `(x, y)`.  If `embed` is `True` (the default), the image data will be embedded in the SVG file.  This results in a larger SVG file, but it can be viewed without access to the original image file.  If `embed` is `False`, the SVG file will merely reference the named file.  This results in a smaller SVG file, but it requires access to the image file.  If the image file is moved or deleted, it will no longer appear in the SVG file.  `fname` can be a URL.  In this case, `embed` must be set to `False`.  *Example*: `image('https://media.inkscape.org/static/images/inkscape-logo.png', (0, 0), embed=False)`

* `clone(obj)`

Return a linked clone of an object.  Modifications made in the Inkscape GUI to the original object propagate to all clones.  (This applies only to certain modifications such as rotations, style properties, and path control-point locations.)  *Example*: `r1 = rect((100, 100), (200, 200), fill='#668000')
r2 = clone(r1, transform='translate(200, 0)')`

### Transformations

All of the functions presented under [Shape API](#shape-api) accept an additional `transform` parameter.  `transform` takes a string representing an [SVG transform](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform) (`rotate`, `scale`, etc.) and applies that transform to the object.

A shortcut for applying the same transformation to multiple objects is to invoke

* `transform(t)`

This sets the default transformation to the string `t`.  Objects specifying a `transform` parameter will prepend their transformations to the default (i.e., apply them afterwards).

*Example*:
```Python
transform('translate(100, 200) skewX(-15)')
for i in range(5):
    rect((i*100 + 10, 10), (i*100 + 40, 40))
    circle((i*100 + 75, 25), 15)
```
The above draws the shapes using coordinates near the origin then applies a transform to shift them to (100, 200).  The transform also skews all the shapes to the right by 15°.

### Connector avoidance

All of the functions presented under [Shape API](#shape-api) accept an additional `conn_avoid` parameter.  `conn_avoid` takes a Boolean argument.  If `True`, connectors created with `connector` will route around the shape.  If `False` (the default), connectors will ignore the shape and route through it.

*Example*:
```Python
r1 = rect((100, 0), (150, 50), fill='#fff6d5')
r2 = rect((200, 400), (250, 450), fill='#fff6d5')
connector(r1, r2, ctype='orthogonal', curve=100)
circle((225, 225), 25, fill='red', conn_avoid=True)
```

### Styles

Trailing *key=value* arguments passed to any of the functions presented under [Shape API](#shape-api) are treated as style parameters.  Use `_` instead of `-` in *key*.  For example, write `stroke_width=2` to represent the SVG style `stroke-width:2`.)

A shortcut for applying the same style to multiple objects is to invoke

* `style(key=value, …)`

This augments the default style with the given parameters.  Use a value of `None` to remove the default value for *key*.  Objects specifying *key=value* style parameters override any default value for the corresponding key.  Here, too, a value of `None` cancels the effect of a previously assigned key.

The default style for most shapes is `stroke='black', fill='none'`.  Text has an empty default, which SVG interprets as `stroke='none', fill='black'`.

*Example*:
```Python
style(stroke='red', stroke_width=2, stroke_dasharray='5,5')
cx, cy = width/2, height/2
for d in range(200, 20, -20):
    gray = 255 - int(d*255/200)
    shade = '#%02x%02x%02x' % (gray, gray, gray)
    rect((cx - d, cy - d), (cx + d, cy + d), fill=shade)
```
In the above, the stroke style is set once and inherited by all of the rectangles, which specify only a fill color.

### Groups

Due to how "generate extensions" work, Inkscape always places the output of Simple Inkscape Scripting within a group.  It is possible to specify additional levels of grouping using

* `group(objs)`

where *objs* is a list of initial objects in the group and is allowed to be empty.  Like all of the objects in the [shape API](#shape-api), `group` accepts optional `transform`, `conn_avoid`, and *key=value* style parameters.

Additional objects can be added to a group one-by-one by invoking the `add` method on the object returned by a call to `group` and passing it an object to add.  Groups are themselves objects and can be added to other groups.

*Example*:
```Python
rad = 25
evens = group()
odds = group()
fills = ['cyan', 'yellow']
for i in range(8):
    sides = i + 3
    p = regular_polygon(sides, (i*rad*3 + rad*2, 3*rad), rad, fill=fills[i%2])
    if sides%2 == 0:
        evens.add(p)
    else:
        odds.add(p)
```
The preceding example draws regular polygons of an increasing number of sides.  All polygons with an even number of sides are grouped together, and all polygons with an odd number of sides are grouped together.  (Because all Simple Inkscape Scripting output is put in a single top-level group, you will need to ungroup once to access the separate even/odd-side groups.)

### Additional convenience features

The document's width and height are provided in pre-defined variables:

* `width`
* `height`

`print` is redefined to invoke `inkex.utils.debug`, which presents its output within a dialog box after the script completes.

Because they are likely to be used quite frequently for drawing repetitive objects, Simple Inkscape Scripting imports Python's [`math`](https://docs.python.org/3/library/math.html) and [`random`](https://docs.python.org/3/library/random.html) packages into the program's namespace with
```Python
from math import *
from random import *
```
Hence, programs can invoke functions such as `cos(rad)` and `uniform(a, b)` and constants such as `pi` without having to import any packages or prefix those names with their package name.

### Advanced usage

Because the Python code is invoked from within an Inkscape [`GenerateExtension`](https://inkscape-extensions-guide.readthedocs.io/en/latest/inkex-modules.html#inkex.extensions.GenerateExtension) object's `generate` method, it is possible to invoke functions from Inkscape's [core API](https://inkscape-extensions-guide.readthedocs.io/en/latest/inkex-core.html).  For example, the document as a whole can be read and modified via `self.svg`, just as in a conventionally developed generate extension.

Objects created directly using Inkscape's core API should be made available to Simple Inkscape Scripting by passing them to the `inkex_object` function:

* `inkex_object(iobj)`

*Example*: `c = inkex.Circle(cx="200", cy="200", r="50"); inkex_object(c)`

Author
------

Scott Pakin, *scott-ink@pakin.org*
