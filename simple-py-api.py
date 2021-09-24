#! /usr/bin/python

'''
Copyright (C) 2021 Scott Pakin, scott-ink@pakin.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301, USA.

'''

import inkex

# ----------------------------------------------------------------------

# The following definitions are utilized by the user convenience
# functions.

# Store all objects the users creates in _simple_objs.
_simple_objs = []

# Store the default style in _default_style.
_default_style = {}

def _construct_style(new_style):
    'Combine new styles with the default style and return the result as a string.'
    style = _default_style.copy()
    for k, v in new_style.items():
        k = k.replace('_', '-')
        if v == None:
            del style[k]
        else:
            style[k] = str(v)
    return ';'.join(['%s:%s' % kv for kv in style.items()])

def _finalize_object(obj, transform, style):
    'Assign a transform and a style then record the object in the object list.'
    if transform is not None:
        obj.transform = transform
    ext_style = _construct_style(style)
    if ext_style != '':
        obj.style = ext_style
    _simple_objs.append(obj)

# ----------------------------------------------------------------------

# The following imports and functions are provided for user convenience.

from math import *
from random import *

def style(**kwargs):
    'Modify the default style.'
    for k, v in kwargs.items():
        k = k.replace('_', '-')
        if v == None:
            del _default_style[k]
        else:
            _default_style[k] = str(v)

def circle(center, r, transform=None, **style):
    'Draw a circle.'
    obj = inkex.Circle(cx=str(center[0]), cy=str(center[1]), r=str(r))
    _finalize_object(obj, transform, style)

def ellipse(center, rx, ry, transform=None, **style):
    'Draw an ellipse.'
    obj = inkex.Ellipse(cx=str(center[0]), cy=str(center[1]),
                        rx=str(rx), ry=str(ry))
    _finalize_object(obj, transform, style)

def rect(ul, lr, transform=None, **style):
    'Draw a rectangle.'
    wd = lr[0] - ul[0]
    ht = lr[1] - ul[1]
    obj = inkex.Rectangle(x=str(ul[0]), y=str(ul[1]),
                          width=str(wd), height=str(ht))
    _finalize_object(obj, transform, style)

def line(pt1, pt2, transform=None, **style):
    'Draw a line.'
    obj = inkex.Line(x1=str(pt1[0]), y1=str(pt1[1]),
                     x2=str(pt2[0]), y2=str(pt2[1]))
    _finalize_object(obj, transform, style)

def polyline(*coords, transform=None, **style):
    'Draw a polyline.'
    if len(coords) < 2:
        inkex.utils.errormsg('A polyline must contain at least two points.')
        return
    pts = ' '.join(["%s,%s" % (str(x), str(y)) for x, y in coords])
    obj = inkex.Polyline(points=pts)
    _finalize_object(obj, transform, style)

def polygon(*coords, transform=None, **style):
    'Draw a polygon.'
    if len(coords) < 3:
        inkex.utils.errormsg('A polygon must contain at least three points.')
        return
    pts = ' '.join(["%s,%s" % (str(x), str(y)) for x, y in coords])
    obj = inkex.Polygon(points=pts)
    _finalize_object(obj, transform, style)

def path(*elts, transform=None, **style):
    'Draw an arbitrary path.'
    if len(elts) == 0:
        inkex.utils.errormsg('A path must contain at least one path element.')
        return
    d = ' '.join([str(e) for e in elts])
    obj = inkex.PathElement(d=d)
    _finalize_object(obj, transform, style)

def text(msg, base, transform=None, **style):
    'Typeset a piece of text.'
    obj = inkex.TextElement(x=str(base[0]), y=str(base[1]))
    obj.set('xml:space', 'preserve')
    obj.text = msg
    _finalize_object(obj, transform, style)

def more_text(msg, base=None, **style):
    'Append text to the preceding object, which must be text.'
    if len(_simple_objs) == 0 or not isinstance(_simple_objs[-1], inkex.TextElement):
        inkex.utils.errormsg('more_text must immediately follow text or another more_text')
        return
    tspan = inkex.Tspan()
    tspan.text = msg
    tspan.style = _construct_style(style)
    if base is not None:
        tspan.set('x', str(base[0]))
        tspan.set('y', str(base[1]))
    _simple_objs[-1].append(tspan)

# ----------------------------------------------------------------------

class SimplePyAPI(inkex.GenerateExtension):
    'Help the user create Inkscape objects with a simple API.'

    def add_arguments(self, pars):
        'Process program parameters passed in from the UI.'
        pars.add_argument('--tab', dest='tab',
                          help='The selected UI tab when OK was pressed')
        pars.add_argument('--program', type=str,
                          help='Python code to execute')

    def container_transform(self):
        'Return an empty tranform so as to preserve user-specified coordinates.'
        return inkex.Transform()

    def generate(self):
        'Generate objects from user-provided Python code.'
        code = self.options.program.replace(r'\n', '\n')
        exec(code)
        for obj in _simple_objs:
            yield obj

if __name__ == '__main__':
    SimplePyAPI().run()
