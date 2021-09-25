A Simple Python API for Inkscape
================================

Description
-----------

In the [Inkscape](https://inkscape.org/) vector-drawing program, how would you go about drawing 100 diamonds, each with a random color and placed at a random position on the page?

![diamonds](https://user-images.githubusercontent.com/650041/134632937-bd3c2d21-04d0-47b9-a61b-170de129022c.png)

* **Option 1**: Draw, color, and place the diamonds manually.  This is exceptionally tedious.

* **Option 2**: Create an [Inkscape extension](https://inkscape-extensions-guide.readthedocs.io/) to automate the process.  This involves gaining familiarity with a large API and writing a substantial amount of setup code just to perform what ought to be a simple task.

Neither option is particularly enticing.  This is why I created the `simple-py-api` Inkscape extension.  `simple-py-api` lets you create shapes in the current Inkscape canvas with a Python script plus a set of simple functions such as `circle` for drawing a circle and `rect` for drawing a rectangle.  The picture shown above was created using just the following six lines of code:
```Python
style(stroke='black', stroke_width="1")
for i in range(100):
    x, y = uniform(0, width), uniform(0, height)
    rect((-5, -5), (5, 5),
         transform='translate(%g, %g) scale(0.75, 1) rotate(45)' % (x, y),
         fill='#%02x%02x%02x' % (randrange(256), randrange(256), randrange(256)))
```

The first line defines the default object style to include a 1-pixel-wide black stroke.  The second line is an ordinary Python `for` loop.  The third line selects a position for the rectangle.  Note that `simple-py-api` predefines `width` as the canvas width and `height` as the canvas height.  The `random` package is imported into the current namespace so `uniform` can be invoked directly.  The fourth line draws a 10×10 pixel rectangle centered on the origin.  The fifth line rotates the rectangle by 45°, squeezes it horizontally into a lozenge, and moves it to the target position.  The sixth line specifies a random fill color.

The diamonds drawn on the canvas are all ordinary Inkscape objects and can be further manipulated using any of the usual Inkscape tools.

In short, `simple-py-api` helps automate repetitive drawing tasks.  Unlike writing a custom Inkscape extension, `simple-py-api` requires sufficiently little boilerplate code as to make its use worthwhile even for tasks that will be performed only once or twice.

Installation
------------

First, identify your Inkscape extensions directory.  This can be found in  Inkscape's preferences: Go to *Edit* → *Preferences* → *System* and look in the *User extensions* field.  On Linux, the extensions directory is typically `$HOME/.config/inkscape/extensions/`.

Second, install `simple-py-api` in that directory or any subdirectory.  For example,
```bash
cd $HOME/.config/inkscape/extensions/
git clone github.com/spakin/simple-py-api
```
will retrieve the code from GitHub.  This later can be updated with
```bash
cd $HOME/.config/inkscape/extensions/simple-py-api/
git pull
```

If Inkscape is already running, exit and restart it to make it look for new extensions.

Usage
-----

### Getting started

Launch the `simple-py-api` extension from Inkscape via *Extensions* → *Render* → *Simple Python API…*.  This will bring up a dialog box that gives you the option to enter a filename for a Python program or enter Python code directly in a text box.  These options are not mutually exclusive; if both are used, the Python code in the file will be executed first, followed by the Python code in the text box.  This enables one, for example, to define functions in a file and invoke them with different parameters from the text box.

As an initial test, try entering
```Python
circle((100, 100), 50)
```
into the text box and clicking *Apply* then *Close*.  This should create a filled, black circle of radius 50 at position (100, 100).  Due to how "generate extensions" work, Inkscape always places the output of `simple-py-api` within a group so ungroup it if desired.

### Shape API

* `circle((cx, cy), r)`

Draw a circle with center `(cx, cy)` and radius `r`.  *Example*: `circle((width/2, height/2), 50)`.

* `ellipse((cx. cy), rx, ry)`.

Draw an ellipse with center `(cx, cy)` and radii `rx` and `ry`.  *Example*: `ellipse((width/2, height/2), 75, 50)`.

* `rect((x1, y1), (x2, y2))`

Draw a rectangle from `(x1, y1)` to `(x2, y2)`.  *Example*: `rect((width/2 - 50, height/2 - 30), (width/2 + 50, height/2 + 30))`.

* `line((x1, y1), (x2, y2))`

Draw a line from `(x1, y1)` to `(x2, y2)`.  *Example*: `line((width, 0), (0, height), stroke='red')`.

* `polyline((x1, y1), (x2, y2), …, (xn, yn))`

Draw a polyline (open polygon) from the given coordinates.  *Example*: `polyline((0, 300), (150, 0), (300, 300), (150, 200), fill='none', stroke='blue', stroke_width=3)`

* `polygon((x1, y1), (x2, y2), …, (xn, yn))`

Draw a polygon from the given coordinates.  *Example*: `polygon((0, 300), (150, 0), (300, 300), (150, 200), fill='none', stroke='green', stroke_width=3)`

* `path(elt, …)`

Draw a path from a list of path commands (strings) and arguments (floats).  *Example*: `path('M', 226, 34, 'V', 237, 'L', 32, 185, 'C', 32, 185, 45, -9, 226, 34, 'Z')`.

* `text(msg, (x, y))`

Draw a piece of text starting at `(x, y)`.  *Example*: `text('Simple Python API', (0, height), font_size='36pt')`.

* `more_text(msg, (x, y))`

Append to a previous piece of text (created with `text` or `more_text`), possibly changing the style.  The starting coordinates `(x, y)` are optional and can be used, e.g., to begin a new line.  *Example*: `text('Hello, ', (width/2, height/2), font_size='24pt', text_anchor='middle'); more_text('Inkscape', font_weight='bold', fill='#800000'); more_text('!!!')`.

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

### Styles

Trailing *key=value* arguments passed to any of the functions presented under [Shape API](#shape-api) are treated as style parameters.  Use `_` instead of `_` in *key*.  For example, write `stroke_width=2` to represent the SVG style `stroke-width:2`.)

A shortcut for applying the same style to multiple objects is to invoke

* `style(key=value, …)`

This augments the default style with the given parameters.  Use a value of `None` to remove the default value for *key*.  Objects specifying *key=value* style parameters override any default value for the corresponding key.  Here, too, a value of `None` cancels the effect of a previously assigned key.

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

### Additional convenience features

The document's width and height are provided in pre-defined variables:

* `width`
* `height`

Because they are likely to be used quite frequently for drawing repetitive objects, `simple-py-api` imports Python's [`math`](https://docs.python.org/3/library/math.html) and [`random`](https://docs.python.org/3/library/random.html) packages into the program's namespace with
```Python
from math import *
from random import *
```
Hence, programs can invoke functions such as `cos(rad)` and `uniform(a, b)` and constants such as `pi` without having to import any packages or prefix those names with their package name.

### Advanced usage

Because the Python code is invoked from within an Inkscape [`GenerateExtension`](https://inkscape-extensions-guide.readthedocs.io/en/latest/inkex-modules.html#inkex.extensions.GenerateExtension) object's `generate` method, it is possible to invoke functions from Inkscape's [core API](https://inkscape-extensions-guide.readthedocs.io/en/latest/inkex-core.html).  For example, a debug message can be output with `inkex.utils.debug(msg)`, and the document as a whole can be read and modified via `self.svg`, just as in a conventionally developed generate extension.

Author
------

Scott Pakin, *scott-ink@pakin.org*
