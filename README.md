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

### Python code to Inkscape

Launch the Simple Inkscape Scripting extension from Inkscape via *Extensions* → *Render* → *Simple Inkscape Scripting…*.  This will bring up a dialog box that gives you the option to enter a filename for a Python program or enter Python code directly in a text box.  These options are not mutually exclusive; if both are used, the Python code in the file will be executed first, followed by the Python code in the text box.  This enables one, for example, to define functions in a file and invoke them with different parameters from the text box.

As an initial test, try entering
```Python
circle((100, 100), 50)
```
into the text box and clicking *Apply* then *Close*.  This should create a black circle of radius 50 at position (100, 100).

### Inkscape to Python code

Simple Inkscape Scripting can also *save* illustrations from the Inkscape GUI to a Python script that, when run from the Simple Inkscape Scripting extension, reproduces the original illustration.  (Note, though, that not all Inkscape features are currently supported.)  From *File* → *Save a Copy…*, simply select `Simple Inkscape Scripting script (*.py)` from the pull-down menu at the bottom of the dialog box.  This can be useful, for instance, for manually drawing a complex object then using Simple Inkscape Scripting to replicate and transform it.

Documentation
-------------

* [Quick-reference guide](https://github.com/spakin/SimpInkScr/wiki/Quick-reference)
* [Main documentation](https://github.com/spakin/SimpInkScr/wiki)
* [Additional examples](examples/)

Legal
-----

Simple Inkscape Scripting is

Copyright © 2021–2022 Scott Pakin

All code is licensed under the GNU General Public License version 3.  See [the license file](LICENSE) for details.

Author
------

Scott Pakin, *scott-ink@pakin.org*
