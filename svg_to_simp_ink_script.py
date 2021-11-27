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

    class Statement(object):
        '''Represent a Python statement (or multiple related statements)
        plus dependencies.'''

        # The following characters are not allowed in Python variable names.
        no_var_re = re.compile(r'\W')

        def __init__(self, code, obj_id=None, dep_ids=None):
            '''Associate an array of code lines with the source SVG object
            ID and any SVG object IDs upon which the SVG object depends.'''
            self.code = code
            self.var_name = self.id2var(obj_id)
            if dep_ids is None:
                self.dep_vars = set()
            else:
                self.dep_vars = {self.id2var(i) for i in dep_ids}
            self.need_var_name = False

        def __str__(self):
            if self.need_var_name:
                self.code[0] = '%s = %s' % (self.var_name, self.code[0])
            return '\n'.join(self.code)

        @classmethod
        def id2var(self, obj_id):
            """Return an Inkscape object's ID as a Python variable name.
            Return None if given None."""
            if obj_id is None:
                return None
            var = self.no_var_re.sub(r'_', obj_id)
            if var[0].isdigit():
                var[0] = '_'
            return var

        def identify_dependents(self, var2stmt):
            '''Acquire a set of all dependent statements, and notify each
            that we need its variable name.'''
            self.dep_stmts = set()
            for dep in self.dep_vars:
                # Tell our dependents to assign themselves a variable name.
                try:
                    var2stmt[dep].need_var_name = True
                except KeyError:
                    pass

                # Keep track of our dependent statements by object,
                # not just by name.
                self.dep_stmts.add(var2stmt[dep])

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
        code = ['circle((%s, %s), %s%s)' % (cx, cy, r, extra)]
        return self.Statement(code, node.get_id())

    def convert_ellipse(self, node):
        'Return Python code for drawing an ellipse.'
        cx, cy = node.get('cx'), node.get('cy')
        rx, ry = node.get('rx'), node.get('ry')
        extra = self.extra_args(node)
        code = ['ellipse((%s, %s), %s, %s%s)' % (cx, cy, rx, ry, extra)]
        return self.Statement(code, node.get_id())

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
        code = ['rect((%.5g, %.5g), (%.5g, %.5g)%s)' %
                (x, y, x + wd, y + ht, extra)]
        return self.Statement(code, node.get_id())

    def convert_line(self, node):
        'Return Python code for drawing a line.'
        x1, y1 = node.get('x1'), node.get('y1')
        x2, y2 = node.get('x2'), node.get('y2')
        extra = self.extra_args(node)
        code = ['line((%s, %s), (%s, %s)%s)' % (x1, y1, x2, y2, extra)]
        return self.Statement(code, node.get_id())

    def convert_poly(self, node, poly):
        'Return Python code for drawing a polyline or polygon.'
        toks = self.sep_re.split(node.get('points'))
        pts = []
        for i in range(0, len(toks), 2):
            pts.append('(%s, %s)' % (toks[i], toks[i + 1]))
        extra = self.extra_args(node)
        code = ['%s(%s%s)' % (poly, ', '.join(pts), extra)]
        return self.Statement(code, node.get_id())

    def convert_arc(self, node):
        'Return Python code for drawing an arc.'
        cx, cy = node.get('sodipodi:cx'), node.get('sodipodi:cy')
        rx, ry = node.get('sodipodi:rx'), node.get('sodipodi:ry')
        ang1, ang2 = node.get('sodipodi:start'), node.get('sodipodi:end')
        arc_type = node.get('sodipodi:arc-type')
        extra = self.extra_args(node)
        code = 'arc((%s, %s), %s, %s, %s, %s' % (cx, cy, rx, ry, ang1, ang2)
        if arc_type is not None:
            code += ', %s' % repr(arc_type)
        code += extra
        code = [code]
        return self.Statement(code, node.get_id())

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

        # Produce either a regular polygon or a star.
        if flat == 'true':
            # Regular polygon
            code = ['regular_polygon(%s, (%s, %s), %s, %s, %s, %s%s)' %
                    (sides, cx, cy, r1, arg1, rnd, rand, extra)]
        else:
            # Star
            code = ['star(%s, (%s, %s), (%s, %s), (%s, %s), %s, %s%s)' %
                    (sides, cx, cy, r1, r2, arg1, arg2, rnd, rand, extra)]
        return self.Statement(code, node.get_id())

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
        code = ['path(%s%s)' % (', '.join(cmds), extra)]
        return self.Statement(code, node.get_id())

    def convert_text(self, node):
        'Return Python code for drawing text.'
        # Determine if the text lies on a path.
        tpaths = [c.get('xlink:href')[1:]
                  for c in node.iter()
                  if c.tag[-8:] == 'textPath']
        if tpaths != []:
            tpath_str = ', %s' % self.Statement.id2var(tpaths[0])
        else:
            tpath_str = ''

        # Convert the initial text object.
        x, y = node.get('x'), node.get('y')
        msg = node.text
        if msg is None:
            msg = ''
        extra = self.extra_args(node, {})
        code = ['text(%s, (%s, %s)%s%s)' %
                (repr(msg), x, y, tpath_str, extra)]

        # Convert all sub-text objects.  We assume that <tspan> tags are
        # not nested.  (SVG allows this, but it's not currently supported
        # by Simple Inkscape Scripting.)
        for tspan in [c for c in node.iter() if c.tag[-5:] == 'tspan']:
            if tspan.text is not None:
                # The text within a <tspan> can have a specified position
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
        return self.Statement(code, node.get_id(), set(tpaths))

    def convert_image(self, node):
        'Return Python code for including an image.'
        x, y = node.get('x'), node.get('y')
        href = node.get('xlink:href')
        absref = node.get('sodipodi:absref')
        extra = self.extra_args(node, {})
        if href is not None and href[:5] == 'data:':
            # Embedded image.  Note that we specify False for the embed
            # parameter.  This is because Inkscape has already discarded
            # the original filename.  Hence, we are effectively requesting
            # a non-embeded image described by a data URL.
            code = ['image(%s, (%s, %s), False%s)' %
                    (repr(href), x, y, extra)]
        elif absref is not None:
            # Non-embedded image.  We were given the original filename.
            code = ['image(%s, (%s, %s), False%s)' %
                    (repr(absref), x, y, extra)]
        else:
            # Non-embedded image.  We were given a URL but not a filename.
            code = ['image(%s, (%s, %s), False%s)' %
                    (repr(href), x, y, extra)]
        return self.Statement(code, node.get_id())

    def convert_all_shapes(self):
        'Convert each SVG shape to a Python statement.'
        stmts = []
        for node in self.svg.xpath('//svg:circle | '
                                   '//svg:ellipse | '
                                   '//svg:rect | '
                                   '//svg:line | '
                                   '//svg:polyline | '
                                   '//svg:polygon | '
                                   '//svg:path | '
                                   '//svg:text | '
                                   '//svg:image'):
            if isinstance(node, inkex.Circle):
                stmts.append(self.convert_circle(node))
            elif isinstance(node, inkex.Ellipse):
                stmts.append(self.convert_ellipse(node))
            elif isinstance(node, inkex.Rectangle):
                stmts.append(self.convert_rectangle(node))
            elif isinstance(node, inkex.Line):
                stmts.append(self.convert_line(node))
            elif isinstance(node, inkex.Polyline):
                stmts.append(self.convert_poly(node, 'polyline'))
            elif isinstance(node, inkex.Polygon):
                stmts.append(self.convert_poly(node, 'polygon'))
            elif isinstance(node, inkex.PathElement):
                stmts.append(self.convert_path(node))
            elif isinstance(node, inkex.TextElement):
                stmts.append(self.convert_text(node))
            elif isinstance(node, inkex.Image):
                stmts.append(self.convert_image(node))
        return stmts

    def find_dependencies(self, code):
        'Find the Statements upon which each other Statement depends.'
        # Construct a map from variable name to Statement.
        var2stmt = {}
        for st in code:
            if st.var_name is not None:
                var2stmt[st.var_name] = st

        # Set need_var_name to True for each referenced Statement.
        for st in code:
            st.identify_dependents(var2stmt)

    def save(self, stream):
        'Write Python code that regenerates the SVG to an output stream.'
        stream.write(b'''\
# This script is intended to be run from Inkscape's Simple Inkscape
# Scripting extension.

''')
        code = self.convert_all_shapes()
        self.find_dependencies(code)
        for stmt in code:
            ln = str(stmt) + '\n'
            stream.write(ln.encode('utf-8'))


if __name__ == '__main__':
    SvgToPythonScript().run()
