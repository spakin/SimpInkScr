#! /usr/bin/env python

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
import re


class SvgToPythonScript(inkex.OutputExtension):
    'Save an Inkscape image to a Simple Inkscape Scripting script.'

    # Most shapes use this as their default style.
    _common_shape_style = {'stroke': repr('none'),
                           'fill': repr('black')}

    # SVG uses both spaces and commas to separate numbers.
    sep_re = re.compile(r'[\s,]+')

    # We separate command characters in path strings from adjoining numbers.
    char_re = re.compile(r'([A-Za-z])')

    def transform_arg(self, node):
        "Return an SVG node's transform string as a function argument."
        xform = node.get('transform')
        if xform is None:
            return ''
        return ', transform=%s' % repr(xform)

    def conn_avoid_arg(self, node):
        "Return an SVG node's connector-avoid value as a function argument."
        avoid = node.get('inkscape:connector-avoid')
        if avoid is None:
            return ''
        return ', conn_avoid=%s' % repr(avoid == 'true')

    def style_args(self, node, def_style):
        "Return an SVG node's style string as key=value arguments."
        # Convert the style string to a dictionary.
        style = node.get('style')
        style_dict = def_style.copy()
        if style is not None:
            for term in style.split(';'):
                # Convert the key from SVG to Python syntax.
                k, v = term.split(':', 1)
                k = k.replace('-', '_')

                # Convert the value from a string to another type if possible.
                try:
                    style_dict[k] = '%.5g' % float(v)
                except ValueError:
                    style_dict[k] = repr(v)

        # Convert the dictionary to a list of function arguments.
        return ''.join([', %s=%s' % kv for kv in style_dict.items()])

    def extra_args(self, node, def_style=None):
        'Return extra function arguments (transform, style) if available.'
        if def_style is None:
            def_style = self._common_shape_style
        args = [self.transform_arg(node),
                self.conn_avoid_arg(node),
                self.style_args(node, def_style)]
        return ''.join(args)

    def convert_circle(self, node):
        'Return Python code for drawing a circle.'
        # Handle the special case of an arc.
        ptype = node.get('sodipodi:type')
        if ptype == 'arc':
            return self.convert_arc(node)

        # Handle the case of an ordinary circle.
        cx, cy, r = node.get('cx'), node.get('cy'), node.get('r')
        extra = self.extra_args(node)
        return ['circle((%s, %s), %s%s)' % (cx, cy, r, extra)]

    def convert_ellipse(self, node):
        'Return Python code for drawing an ellipse.'
        cx, cy = node.get('cx'), node.get('cy')
        rx, ry = node.get('rx'), node.get('ry')
        extra = self.extra_args(node)
        return ['ellipse((%s, %s), %s, %s%s)' % (cx, cy, rx, ry, extra)]

    def convert_rectangle(self, node):
        'Return Python code for drawing a rectangle.'
        # Acquire a rect's required parameters.
        x, y = float(node.get('x')), float(node.get('y'))
        wd, ht = float(node.get('width')), float(node.get('height'))
        extra = self.extra_args(node)

        # Handle the optional corner-rounding parameter.
        rx, ry = node.get('rx'), node.get('ry')
        if rx is not None and ry is not None:
            extra = ', (%s, %s)%s' % (rx, ry, extra)
        elif rx is not None:
            extra = ', %s%s' % (rx, extra)
        elif ry is not None:
            extra = ', %s%s' % (ry, extra)

        # Return a complete call to rect.
        return ['rect((%.5g, %.5g), (%.5g, %.5g)%s)' %
                (x, y, x + wd, y + ht, extra)]

    def convert_line(self, node):
        'Return Python code for drawing a line.'
        x1, y1 = node.get('x1'), node.get('y1')
        x2, y2 = node.get('x2'), node.get('y2')
        extra = self.extra_args(node)
        return ['line((%s, %s), (%s, %s)%s)' % (x1, y1, x2, y2, extra)]

    def convert_poly(self, node, poly):
        'Return Python code for drawing a polyline or polygon.'
        toks = self.sep_re.split(node.get('points'))
        pts = []
        for i in range(0, len(toks), 2):
            pts.append('(%s, %s)' % (toks[i], toks[i + 1]))
        extra = self.extra_args(node)
        return ['%s(%s%s)' % (poly, ', '.join(pts), extra)]

    def convert_arc(self, node):
        'Return Python code for drawing an arc.'
        cx, cy = node.get('sodipodi:cx'), node.get('sodipodi:cy')
        rx, ry = node.get('sodipodi:rx'), node.get('sodipodi:ry')
        ang1, ang2 = node.get('sodipodi:start'), node.get('sodipodi:end')
        arc_type = node.get('sodipodi:arc-type')
        extra = self.extra_args(node)
        py = 'arc((%s, %s), %s, %s, %s, %s' % (cx, cy, rx, ry, ang1, ang2)
        if arc_type is not None:
            py += ', %s' % repr(arc_type)
        py += extra
        return [py]

    def convert_poly_star(self, node):
        'Return Python code for drawing either a regular polygon or a star.'
        # Extract all of the parameters that define the shape.
        sides = node.get('sodipodi:sides')
        cx, cy = node.get('sodipodi:cx'), node.get('sodipodi:cy')
        r1, r2 = node.get('sodipodi:r1'), node.get('sodipodi:r2')
        arg1, arg2 = node.get('sodipodi:arg1'), node.get('sodipodi:arg2')
        flat = node.get('inkscape:flatsided')
        rnd = node.get('inkscape:rounded')
        rand = node.get('inkscape:randomized')
        extra = self.extra_args(node)

        # Case 1: Regular polygon
        if flat == 'true':
            return ['regular_polygon(%s, (%s, %s), %s, %s, %s, %s%s)' %
                    (sides, cx, cy, r1, arg1, rnd, rand, extra)]

        # Case 2: Star
        return ['star(%s, (%s, %s), (%s, %s), (%s, %s), %s, %s%s)' %
                (sides, cx, cy, r1, r2, arg1, arg2, rnd, rand, extra)]

    def convert_path(self, node):
        'Return Python code for drawing a path.'
        # Handle the special case of an arc.
        ptype = node.get('sodipodi:type')
        if ptype == 'arc':
            return self.convert_arc(node)
        if ptype == 'star':
            return self.convert_poly_star(node)

        # Handle the case of a generic path.
        d_str = node.get('d')
        d_str = self.char_re.sub(r' \1 ', d_str).strip()
        toks = self.sep_re.split(d_str)
        cmds = []
        for t in toks:
            try:
                # Number
                f = float(t)
                cmds.append(t)
            except ValueError:
                # String
                cmds.append(repr(t))
        extra = self.extra_args(node)
        return ['path(%s%s)' % (', '.join(cmds), extra)]

    def convert_text(self, node):
        'Return Python code for drawing text.'
        # Convert the initial text object.
        x, y = node.get('x'), node.get('y')
        msg = node.text
        if msg is None:
            msg = ''
        extra = self.extra_args(node, {})
        code = ['text(%s, (%s, %s)%s)' % (repr(msg), x, y, extra)]

        # Convert all sub-text objects.  We assume that <tspan> tags are
        # not nested.  (SVG allows this, but it's not currently supported
        # by Simple Inkscape Scripting.)
        for tspan in [c for c in node.iter() if c.tag[-5:] == 'tspan']:
            if tspan.text is not None:
                # The text within a <tpsan> can have a specified position
                # and style.
                x, y = tspan.get('x'), tspan.get('y')
                extra = self.extra_args(tspan, {})
                if x is not None and y is not None:
                    # Specified position
                    code.append('more_text(%s, (%s, %s)%s)' %
                                (repr(tspan.text), x, y, extra))
                else:
                    # Unspecified position
                    code.append('more_text(%s%s)' %
                                (repr(tspan.text), extra))
            if tspan.tail is not None:
                # The text following a <tspan> has neither a specified
                # position nor style.
                code.append('more_text(%s)' % repr(tspan.tail))
        return code

    def convert_all_shapes(self):
        'Convert each SVG shape to a Python function call.'
        code = []
        for node in self.svg.xpath('//svg:circle | '
                                   '//svg:ellipse | '
                                   '//svg:rect | '
                                   '//svg:line | '
                                   '//svg:polyline | '
                                   '//svg:polygon | '
                                   '//svg:path | '
                                   '//svg:text'):
            if isinstance(node, inkex.Circle):
                code.append(self.convert_circle(node))
            elif isinstance(node, inkex.Ellipse):
                code.append(self.convert_ellipse(node))
            elif isinstance(node, inkex.Rectangle):
                code.append(self.convert_rectangle(node))
            elif isinstance(node, inkex.Line):
                code.append(self.convert_line(node))
            elif isinstance(node, inkex.Polyline):
                code.append(self.convert_poly(node, 'polyline'))
            elif isinstance(node, inkex.Polygon):
                code.append(self.convert_poly(node, 'polygon'))
            elif isinstance(node, inkex.PathElement):
                code.append(self.convert_path(node))
            elif isinstance(node, inkex.TextElement):
                code.append(self.convert_text(node))
        return code

    def save(self, stream):
        'Write Python code that regenerates the SVG to an output stream.'
        stream.write(b'''\
# This script is intended to be run from Inkscape's Simple Inkscape
# Scripting extension.

''')
        for code in self.convert_all_shapes():
            ln = '\n'.join(code) + '\n'
            stream.write(ln.encode('utf-8'))


if __name__ == '__main__':
    SvgToPythonScript().run()
