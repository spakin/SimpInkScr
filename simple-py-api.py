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

# ----------------------------------------------------------------------

# The following imports and functions are provided for user convenience.

import random

def style(**kwargs):
    'Modify the default style.'
    for k, v in kwargs.items():
        k = k.replace('_', '-')
        if v == None:
            del _default_style[k]
        else:
            _default_style[k] = str(v)

def circle(center, r, **kwargs):
    'Create a circle.'
    obj = inkex.Circle(cx=str(center[0]), cy=str(center[1]), r=str(r),
                       style=_construct_style(kwargs))
    _simple_objs.append(obj)

def ellipse(center, rx, ry, **kwargs):
    'Create an ellipse.'
    obj = inkex.Ellipse(cx=str(center[0]), cy=str(center[1]),
                        rx=str(rx), ry=str(ry),
                        style=_construct_style(kwargs))
    _simple_objs.append(obj)

def rect(ul, lr, **kwargs):
    'Create a rectangle.'
    wd = lr[0] - ul[0]
    ht = lr[1] - ul[1]
    obj = inkex.Rectangle(x=str(ul[0]), y=str(ul[1]),
                          width=str(wd), height=str(ht),
                          style=_construct_style(kwargs))
    _simple_objs.append(obj)

# ----------------------------------------------------------------------

class SimplePyAPI(inkex.GenerateExtension):
    'Help the user create Inkscape objects with a simple API.'

    def add_arguments(self, pars):
        'Process program parameters passed in from the UI.'
        pars.add_argument('--tab', dest='tab',
                          help='The selected UI tab when OK was pressed')
        pars.add_argument('--program', type=str,
                          help='Python code to execute')

    def generate(self):
        'Generate objects from user-provided Python code.'
        code = self.options.program.replace(r'\n', '\n')
        exec(code)
        for obj in _simple_objs:
            yield obj

if __name__ == '__main__':
    SimplePyAPI().run()
