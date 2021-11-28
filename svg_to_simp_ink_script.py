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

    # Most SVG shapes use this as their default style.
    _common_svg_defaults = {'stroke': repr('none'),
                            'fill': repr('black')}

    # Most Simple Inkscape Scripting shapes use this as their default style.
    _common_sis_defaults = {'stroke': '#000000',  # More common than "black"
                            'fill': 'none'}

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
                self.dep_vars = []
            else:
                self.dep_vars = [self.id2var(i) for i in dep_ids]
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
            '''Acquire a list of all dependent statements, and notify each
            that we need its variable name.'''
            self.dep_stmts = []
            for dep in self.dep_vars:
                # Tell our dependents to assign themselves a variable name.
                try:
                    var2stmt[dep].need_var_name = True
                except KeyError:
                    pass

                # Keep track of our dependent statements by object,
                # not just by name.
                try:
                    self.dep_stmts.append(var2stmt[dep])
                except KeyError:
                    pass

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

    def style_args(self, node, def_svg_style, def_sis_style):
        "Return an SVG node's style string as key=value arguments."
        # Convert the style string to a dictionary.
        style = node.get('style')
        style_dict = def_svg_style.copy()
        if style is not None:
            for term in style.split(';'):
                # Convert the key from SVG to Python syntax.
                k, v = term.split(':', 1)
                k = k.replace('-', '_')

                # Convert the value from a string to another type if possible.
                try:
                    # Number -- format and use.
                    style_dict[k] = '%.5g' % float(v)
                except ValueError:
                    # String -- quote if not already quoted.
                    try:
                        if (v[0] == "'" and v[-1] == "'") or \
                           (v[0] == '"' and v[-1] == '"'):
                            style_dict[k] = v
                        else:
                            style_dict[k] = repr(v)
                    except IndexError:
                        pass

        # Remove key=value pairs that are Simple Inkscape Scripting defaults.
        for k, v in def_sis_style.items():
            try:
                if style_dict[k] == repr(v):
                    del style_dict[k]
            except KeyError:
                pass

        # Convert the dictionary to a list of function arguments.
        return ''.join([', %s=%s' % kv for kv in style_dict.items()])

    def extra_args(self, node, def_svg_style=None, def_sis_style=None):
        'Return extra function arguments (transform, style) if available.'
        if def_svg_style is None:
            def_svg_style = self._common_svg_defaults
        if def_sis_style is None:
            def_sis_style = self._common_sis_defaults
        args = [self.transform_arg(node),
                self.conn_avoid_arg(node),
                self.style_args(node, def_svg_style, def_sis_style)]
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
            extra = ', round=(%s, %s)%s' % (rx, ry, extra)
        elif rx is not None:
            extra = ', round=%s%s' % (rx, extra)
        elif ry is not None:
            extra = ', round%s%s' % (ry, extra)

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
        points_str = node.get('points').strip()
        toks = self.sep_re.split(points_str)
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
        if arc_type is not None and arc_type != 'arc':
            code += ', arc_type=%s' % repr(arc_type)
        code += extra + ')'
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

        # Construct a list of optional arguments.  We always include
        # the angle, though.
        opt_args = []
        if rnd is not None and float(rnd) != 0.0:
            opt_args.append('round=%s' % rnd)
        if rand is not None and float(rand) != 0.0:
            opt_args.append('random=%s' % rand)
        opt_arg_str = ''
        if opt_args != []:
            opt_arg_str = ', ' + ', '.join(opt_args)

        # Produce either a regular polygon or a star.
        if flat == 'true':
            # Regular polygon
            code = ['regular_polygon(%s, (%s, %s), %s, ang=%s%s%s)' %
                    (sides, cx, cy, r1, arg1, opt_arg_str, extra)]
        else:
            # Star
            code = ['star(%s, (%s, %s), (%s, %s), ang=(%s, %s)%s%s)' %
                    (sides, cx, cy, r1, r2, arg1, arg2, opt_arg_str, extra)]
        return self.Statement(code, node.get_id())

    def convert_connector(self, node):
        'Return Python code for drawing a connector between objects.'
        # Process the required arguments.
        id1 = node.get('inkscape:connection-start')[1:]
        var1 = self.Statement.id2var(id1)
        id2 = node.get('inkscape:connection-end')[1:]
        var2 = self.Statement.id2var(id2)

        # Process the optional arguments.
        opt_args = []
        ctype = node.get('inkscape:connector-type')
        if ctype is not None and ctype != 'polyline':
            opt_args.append('ctype=%s' % repr(ctype))
        curve = node.get('inkscape:connector-curvature')
        if curve is not None and float(curve) != 0:
            opt_args.append('curve=%s' % curve)
        opt_arg_str = ''
        if opt_args != []:
            opt_arg_str = ', ' + ', '.join(opt_args)
        extra = self.extra_args(node)

        # Generate a Statement for the connector.
        code = ['connector(%s, %s%s%s)' %
                (var1, var2, opt_arg_str, extra)]
        return self.Statement(code, node.get_id(), {id1, id2})

    def convert_path(self, node):
        'Return Python code for drawing a path.'
        # Handle the special case of an arc.
        ptype = node.get('sodipodi:type')
        if ptype == 'arc':
            return self.convert_arc(node)
        if ptype == 'star':
            return self.convert_poly_star(node)
        if node.get('inkscape:connector-type') is not None:
            return self.convert_connector(node)

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
            tpath_str = ', path=%s' % self.Statement.id2var(tpaths[0])
        else:
            tpath_str = ''

        # Convert the initial text object.
        x, y = node.get('x'), node.get('y')
        msg = node.text
        if msg is None:
            msg = ''
        extra = self.extra_args(node, {}, {})
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
        extra = self.extra_args(node, {}, {})
        if href is not None and href[:5] == 'data:':
            # Embedded image.  Note that we specify False for the embed
            # parameter.  This is because Inkscape has already discarded
            # the original filename.  Hence, we are effectively requesting
            # a non-embeded image described by a data URL.
            code = ['image(%s, (%s, %s), embed=False%s)' %
                    (repr(href), x, y, extra)]
        elif absref is not None:
            # Non-embedded image.  We were given the original filename.
            code = ['image(%s, (%s, %s), embed=False%s)' %
                    (repr(absref), x, y, extra)]
        else:
            # Non-embedded image.  We were given a URL but not a filename.
            code = ['image(%s, (%s, %s), embed=False%s)' %
                    (repr(href), x, y, extra)]
        return self.Statement(code, node.get_id())

    def convert_clone(self, node):
        'Return Python code for cloning an object.'
        href = node.get('xlink:href')[1:]
        var = self.Statement.id2var(href)
        extra = self.extra_args(node, {}, {})
        code = ['clone(%s%s)' % (var, extra)]
        return self.Statement(code, node.get_id(), {href})

    def convert_group(self, node):
        'Return Python code for grouping objects.'
        if node.get('inkscape:groupmode') == 'layer':
            # Ignore layers.
            return None
        extra = self.extra_args(node, {}, {})
        child_ids = [c.get_id() for c in node]
        child_vars = [self.Statement.id2var(i) for i in child_ids]
        code = ['group([%s]%s)' % (', '.join(child_vars), extra)]
        return self.Statement(code, node.get_id(), child_ids)

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
                                   '//svg:image | '
                                   '//svg:use | '
                                   '//svg:g'):
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
            elif isinstance(node, inkex.Use):
                stmts.append(self.convert_clone(node))
            elif isinstance(node, inkex.Group):
                stmts.append(self.convert_group(node))
        return [st for st in stmts if st is not None]

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

    def sort_statement_forest(self, code, seen=set()):
        '''Return a list of statements with dependencies before dependents
        but otherwise maintaining the original order.'''
        ordered_code = []
        for stmt in code:
            # Ignore statements we've seen before.
            if stmt in seen:
                continue

            # Recursively process our dependencies.
            children = self.sort_statement_forest(stmt.dep_stmts, seen)
            ordered_code.extend(children)

            # Append ourself.
            ordered_code.append(stmt)
            seen.add(stmt)
        return ordered_code

    def save(self, stream):
        'Write Python code that regenerates the SVG to an output stream.'
        stream.write(b'''\
# This Python script is intended to be run from Inkscape's Simple
# Inkscape Scripting extension.

''')
        code = self.convert_all_shapes()
        self.find_dependencies(code)
        code = self.sort_statement_forest(code)
        for stmt in code:
            ln = str(stmt) + '\n'
            stream.write(ln.encode('utf-8'))


if __name__ == '__main__':
    SvgToPythonScript().run()
