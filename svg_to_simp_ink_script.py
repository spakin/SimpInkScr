#! /usr/bin/env python

'''
Copyright (C) 2021-2022 Scott Pakin, scott-ink@pakin.org

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
from inkex.localization import inkex_gettext as _
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
            self.need_var_name = False     # Dependency from another object?
            self.delete_if_unused = False  # Definition or other transient?

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

    def clip_path_arg(self, node):
        """Return an SVG node's clip-path string as a function argument.
        Also return additional object dependencies from url(#...) values."""
        c_path = node.get('clip-path')
        if c_path is None:
            return '', []
        c_path_var = self.Statement.id2var(c_path[5:-1])
        return ', clip_path=%s' % c_path_var, [c_path_var]

    def style_args(self, node, def_svg_style, def_sis_style):
        """Return an SVG node's style string as key=value arguments.  Also
        return additional object dependencies from url(#...) values."""
        # As a special case, if we're within a <marker> element, force
        # the default styles to empty.
        if node.get('sis_within_marker') == 'true':
            def_svg_style = {'stroke': None,
                             'fill': None}

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

        # Replace "url(#...)" values with object references.
        url_ids = set()
        for k, v in style_dict.items():
            if v is not None and v[:6] == "'url(#":
                v = v[6:-2]
                url_ids.add(v)
                style_dict[k] = self.Statement.id2var(v)

        # Convert the dictionary to a list of function arguments.
        args = ''.join([', %s=%s' % kv for kv in style_dict.items()])
        return args, list(url_ids)

    def extra_args(self, node, def_svg_style=None, def_sis_style=None):
        '''Return extra function arguments (transform, style) if available.
        Also return a list of dependencies (SVG IDs).'''
        if def_svg_style is None:
            def_svg_style = self._common_svg_defaults
        if def_sis_style is None:
            def_sis_style = self._common_sis_defaults
        clip_args, c_deps = self.clip_path_arg(node)
        style_args, s_deps = \
            self.style_args(node, def_svg_style, def_sis_style)
        args = [self.transform_arg(node),
                self.conn_avoid_arg(node),
                clip_args,
                style_args]
        deps = set()
        deps.update(c_deps)
        deps.update(s_deps)
        return ''.join(args), list(deps)

    def set_within_marker(self, node):
        '''Recursively mark a node and all its children as lying within an
        SVG <marker> element.'''
        node.set('sis_within_marker', 'true')
        for child in node:
            self.set_within_marker(child)

    def convert_circle(self, node):
        'Return Python code for drawing a circle.'
        # Handle the special case of an arc.
        ptype = node.get('sodipodi:type')
        if ptype == 'arc':
            return self.convert_arc(node)

        # Handle the case of an ordinary circle.
        cx, cy, r = node.get('cx'), node.get('cy'), node.get('r')
        extra, extra_deps = self.extra_args(node)
        code = ['circle((%s, %s), %s%s)' % (cx, cy, r, extra)]
        return self.Statement(code, node.get_id(), extra_deps)

    def convert_ellipse(self, node):
        'Return Python code for drawing an ellipse.'
        cx, cy = node.get('cx'), node.get('cy')
        rx, ry = node.get('rx'), node.get('ry')
        extra, extra_deps = self.extra_args(node)
        code = ['ellipse((%s, %s), (%s, %s)%s)' % (cx, cy, rx, ry, extra)]
        return self.Statement(code, node.get_id(), extra_deps)

    def convert_rectangle(self, node):
        'Return Python code for drawing a rectangle.'
        # Acquire a rect's required parameters.
        x, y = float(node.get('x')), float(node.get('y'))
        wd, ht = float(node.get('width')), float(node.get('height'))
        extra, extra_deps = self.extra_args(node)

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
        return self.Statement(code, node.get_id(), extra_deps)

    def convert_line(self, node):
        'Return Python code for drawing a line.'
        x1, y1 = node.get('x1'), node.get('y1')
        x2, y2 = node.get('x2'), node.get('y2')
        extra, extra_deps = self.extra_args(node)
        code = ['line((%s, %s), (%s, %s)%s)' % (x1, y1, x2, y2, extra)]
        return self.Statement(code, node.get_id(), extra_deps)

    def convert_poly(self, node, poly):
        'Return Python code for drawing a polyline or polygon.'
        points_str = node.get('points').strip()
        toks = self.sep_re.split(points_str)
        pts = []
        for i in range(0, len(toks), 2):
            pts.append('(%s, %s)' % (toks[i], toks[i + 1]))
        extra, extra_deps = self.extra_args(node)
        code = ['%s([%s]%s)' % (poly, ', '.join(pts), extra)]
        return self.Statement(code, node.get_id(), extra_deps)

    def convert_arc(self, node):
        'Return Python code for drawing an arc.'
        cx, cy = node.get('sodipodi:cx'), node.get('sodipodi:cy')
        rx, ry = node.get('sodipodi:rx'), node.get('sodipodi:ry')
        ang1, ang2 = node.get('sodipodi:start'), node.get('sodipodi:end')
        arc_type = node.get('sodipodi:arc-type')
        extra, extra_deps = self.extra_args(node)
        code = 'arc((%s, %s), (%s, %s), (%s, %s)' % \
            (cx, cy, rx, ry, ang1, ang2)
        if arc_type is not None and arc_type != 'arc':
            code += ', arc_type=%s' % repr(arc_type)
        code += extra + ')'
        code = [code]
        return self.Statement(code, node.get_id(), extra_deps)

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
        extra, extra_deps = self.extra_args(node)

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
        return self.Statement(code, node.get_id(), extra_deps)

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
        extra, extra_deps = self.extra_args(node)

        # Generate a Statement for the connector.
        code = ['connector(%s, %s%s%s)' %
                (var1, var2, opt_arg_str, extra)]
        return self.Statement(code, node.get_id(), [id1, id2] + extra_deps)

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
        d_str = node.get('inkscape:original-d') or node.get('d')
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
        extra, extra_deps = self.extra_args(node)

        # Depend on any path effects applied to the path.
        pe_list = node.get('inkscape:path-effect')
        if pe_list is None:
            pe_list = []
        else:
            pe_list = [pe[1:] for pe in pe_list.split(';')]
            extra_deps.extend(pe_list)

        # Generate code and wrap it in a statement.
        code = ['path([%s]%s)' % (', '.join(cmds), extra)]
        if len(pe_list) == 1:
            code.append('%s.apply_path_effect(%s)' %
                        (self.Statement.id2var(node.get_id()),
                         self.Statement.id2var(pe_list[0])))
        elif len(pe_list) > 1:
            pe_list_str = ', '.join([self.Statement.id2var(pe)
                                    for pe in pe_list])
            code.append('%s.apply_path_effect([%s])' %
                        (self.Statement.id2var(node.get_id()),
                         pe_list_str))
        stmt = self.Statement(code, node.get_id(), extra_deps)
        if pe_list != []:
            stmt.need_var_name = True
        return stmt

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
        all_deps = set(tpaths)

        # Convert the initial text object.
        x, y = node.get('x'), node.get('y')
        msg = node.text
        if msg is None:
            msg = ''
        extra, extra_deps = self.extra_args(node, {}, {})
        code = ['text(%s, (%s, %s)%s%s)' %
                (repr(msg), x, y, tpath_str, extra)]
        all_deps = all_deps.union(extra_deps)

        # Convert all sub-text objects.  We assume that <tspan> tags are
        # not nested.  (SVG allows this, but it's not currently supported
        # by Simple Inkscape Scripting.)
        for tspan in [c for c in node.iter() if c.tag[-5:] == 'tspan']:
            if tspan.text is not None:
                # The text within a <tspan> can have a specified position
                # and style.
                x, y = tspan.get('x'), tspan.get('y')
                extra, extra_deps = self.extra_args(tspan, {})
                all_deps = all_deps.union(extra_deps)
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
        return self.Statement(code, node.get_id(), sorted(all_deps))

    def convert_image(self, node):
        'Return Python code for including an image.'
        x, y = node.get('x'), node.get('y')
        href = node.get('xlink:href')
        absref = node.get('sodipodi:absref')
        extra, extra_deps = self.extra_args(node, {}, {})
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
        return self.Statement(code, node.get_id(), extra_deps)

    def convert_clone(self, node):
        'Return Python code for cloning an object.'
        href = node.get('xlink:href')[1:]
        var = self.Statement.id2var(href)
        extra, extra_deps = self.extra_args(node, {}, {})
        code = ['clone(%s%s)' % (var, extra)]
        return self.Statement(code, node.get_id(), [href] + extra_deps)

    def convert_group(self, node):
        'Return Python code for grouping objects.'
        if node.get('inkscape:groupmode') == 'layer':
            # Ignore layers.
            return None
        extra, extra_deps = self.extra_args(node, {}, {})
        child_ids = [c.get_id() for c in node]
        child_vars = [self.Statement.id2var(i) for i in child_ids]
        code = ['group([%s]%s)' % (', '.join(child_vars), extra)]
        return self.Statement(code, node.get_id(), child_ids + extra_deps)

    def convert_filter(self, node):
        'Return Python code that defines a filter.'
        # Generate code for the filter effect.
        filt_args = []
        if node.label is not None and node.label != '':
            filt_args.append('name=%s' % repr(node.label))
        x, y = node.get('x'), node.get('y')
        wd, ht = node.get('width'), node.get('height')
        if x is not None and y is not None:
            filt_args.append('pt1=(%s, %s)' % (x, y))
        if wd is not None and ht is not None:
            x0, y0 = float(x or 0), float(y or 0)
            x1, y1 = x0 + float(wd), y0 + float(ht)
            filt_args.append('pt2=(%s, %s)' % (x1, y1))
        f_units, p_units = node.get('filterUnits'), node.get('primitiveUnits')
        if f_units is not None:
            filt_args.append('filter_units=%s' % repr(f_units))
        if p_units is not None:
            filt_args.append('primitive_units=%s' % repr(p_units))
        extra, extra_deps = self.extra_args(node, {}, {})
        if extra != '':
            filt_args.append(extra[2:])  # Drop the leading ", ".
        code = ['filter_effect(%s)' % ', '.join(filt_args)]
        id2var = self.Statement.id2var
        filt_name = id2var(node.get_id())

        class Primitive(object):
            'Represent a single filter primitive.'

            def __init__(self, pnode, var2prim):
                self.prim = pnode
                self.var_name = id2var(pnode.get('result') or pnode.get_id())
                self.src1 = pnode.get('in')
                self.src2 = pnode.get('in2')
                self.var2prim = var2prim
                self.need_var_name = False

            def _attrib2py(self, key, val):
                "Convert an attribute's key and value to a Python tuple."
                key_str = key.replace('-', '_')
                val_list = []
                for v in val.split():
                    try:
                        # If the value is convertible to a float, append it
                        # verbatim.
                        vf = float(v)
                        val_list.append(v)
                    except ValueError:
                        # If the value is not convertible to a float, quote it
                        # as a string and append it.
                        val_list.append(repr(v))
                val_str = ', '.join(val_list)
                if len(val_list) > 1:
                    val_str = '[%s]' % val_str
                return key_str, val_str

            def __str__(self):
                # Invoke the add method on the filter_effect object.
                code = '%s.add(%s' % (filt_name, repr(self.prim.tag_name[2:]))

                # Specially handle src1 and src2.  These point to
                # either a named filter primitive or a string.
                if self.src1 is not None:
                    if self.src1 in self.var2prim:
                        code += ', src1=%s' % self.src1
                    else:
                        code += ', src1=%s' % repr(self.src1)
                if self.src2 is not None:
                    if self.src2 in self.var2prim:
                        code += ', src2=%s' % self.src2
                    else:
                        code += ', src2=%s' % repr(self.src2)

                # Append all remaining attributes.
                for k, v in self.prim.items():
                    if k not in ['in', 'in2', 'result', 'id']:
                        code += ', %s=%s' % self._attrib2py(k, v)
                code += ')'

                # If the primitive contains any child options, add these, too.
                if len(self.prim) > 0:
                    self.need_var_name = True
                for opt in self.prim:
                    code += '\n'
                    ftype = opt.tag[opt.tag.rindex('fe') + 2:]
                    code += '%s.add(%s' % (self.var_name, repr(ftype))
                    for k, v in opt.items():
                        if k != 'id':
                            code += ', %s=%s' % self._attrib2py(k, v)
                    code += ')'

                # Assign a variable name if it was referenced.
                if self.need_var_name:
                    code = '%s = %s' % (self.var_name, code)

                # Return the final string.
                return code

        # Generate code for each underlying filter primitive.
        prim_list = []   # Ordered list of Primitives
        var2prim = {}    # Map from a variable name to a Primitive
        for prim in node:
            if not isinstance(prim, inkex.Filter.Primitive):
                continue
            pobj = Primitive(prim, var2prim)
            prim_list.append(pobj)
            if pobj.src1 is not None and pobj.src1 in var2prim:
                var2prim[pobj.src1].need_var_name = True
            if pobj.src2 is not None and pobj.src2 in var2prim:
                var2prim[pobj.src2].need_var_name = True
            var2prim[pobj.var_name] = pobj
        for pobj in prim_list:
            code.append(str(pobj))

        # Construct and return a Statement.
        stmt = self.Statement(code, node.get_id(), extra_deps)
        stmt.need_var_name = True  # Always needed by filter primitives
        return stmt

    def _common_gradient_args(self, node):
        '''Return a list of arguments common to linear and radial gradients
        and a set of dependent objects.'''
        grad_args = []
        deps = set()
        spread = node.get('spreadMethod')
        if spread is not None and spread != 'pad':
            spread_to_repeat = {'reflect': 'reflected',
                                'repeat':  'direct'}
            grad_args.append('repeat=%s' % repr(spread_to_repeat[spread]))
        g_units = node.get('gradientUnits')
        if g_units is not None:
            grad_args.append('gradient_units=%s' % repr(g_units))
        href = node.get('href')
        xlink = node.get('xlink:href')
        template = href or xlink
        if template is not None:
            template = template[1:]  # Drop the "#".
            grad_args.append('template=%s' % template)
            deps.add(template)
        xform = node.get('gradientTransform')
        if xform is not None:
            grad_args.append('transform=%s' % repr(xform))
        extra, extra_deps = self.extra_args(node, {}, {})
        if extra != '':
            grad_args.append(extra[2:])  # Drop the leading ", ".
            deps = deps.union(extra_deps)
        return grad_args, deps

    def _gradient_stops(self, node):
        '''Return code for adding gradient stops and a set of dependent
        objects.'''
        code = []
        deps = set()
        var_name = self.Statement.id2var(node.get_id())
        for stop in node:
            # The stop offset is a mandatory field.
            if not isinstance(stop, inkex.Stop):
                continue
            stop_args = ['%s' % stop.offset]

            # stop-color and stop-opacity can be expressed directly or
            # within a style.  We therefore have to look in both places.
            # We let the style override the non-style options.
            color = stop.get('stop-color')
            opacity = stop.get('stop-opacity')
            style = stop.style.copy()
            try:
                color = style['stop-color']
                del style['stop-color']
            except KeyError:
                pass
            try:
                opacity = style['stop-opacity']
                del style['stop-opacity']
            except KeyError:
                pass
            stop.style = style
            style_str, style_deps = self.style_args(stop, {}, {})
            stop_args.append(repr(color))
            if opacity is not None:
                stop_args.append('opacity=%s' % opacity)

            # Construct a call to add_stop.
            deps = deps.union(style_deps)
            code.append('%s.add_stop(%s%s)' %
                        (var_name, ', '.join(stop_args), style_str))
        return code, deps

    def convert_linear_gradient(self, node):
        'Return Python code that defines a linear gradient.'
        # Generate code for the linear-gradient object proper.
        grad_args = []
        x1, y1 = node.get('x1'), node.get('y1')
        if x1 is not None and y1 is not None:
            grad_args.append('pt1=(%s, %s)' % (x1, y1))
        x2, y2 = node.get('x2'), node.get('y2')
        if x2 is not None and y2 is not None:
            grad_args.append('pt2=(%s, %s)' % (x2, y2))
        more_args, all_deps = self._common_gradient_args(node)
        grad_args.extend(more_args)
        code = ['linear_gradient(%s)' % ', '.join(grad_args)]

        # Generate code for each stop.
        more_code, more_deps = self._gradient_stops(node)
        code.extend(more_code)
        all_deps = all_deps.union(more_deps)
        have_stops = more_code != []

        # Construct and return a Statement.
        stmt = self.Statement(code, node.get_id(), all_deps)
        if have_stops:
            stmt.need_var_name = True
        stmt.delete_if_unused = True
        return stmt

    def convert_radial_gradient(self, node):
        'Return Python code that defines a radial gradient.'
        # Generate code for the radial-gradient object proper.
        grad_args = []
        cx, cy = node.get('cx'), node.get('cy')
        if cx is not None and cy is not None:
            grad_args.append('center=(%s, %s)' % (cx, cy))
        r = node.get('r')
        if r is not None:
            grad_args.append('radius=%s' % r)
        fx, fy = node.get('fx'), node.get('fy')
        if fx is not None and fy is not None:
            grad_args.append('focus=(%s, %s)' % (fx, fy))
        fr = node.get('fr')
        if fr is not None:
            grad_args.append('fr=%s' % fr)
        more_args, all_deps = self._common_gradient_args(node)
        grad_args.extend(more_args)
        code = ['radial_gradient(%s)' % ', '.join(grad_args)]

        # Generate code for each stop.
        more_code, more_deps = self._gradient_stops(node)
        code.extend(more_code)
        all_deps = all_deps.union(more_deps)
        have_stops = more_code != []

        # Construct and return a Statement.
        stmt = self.Statement(code, node.get_id(), all_deps)
        if have_stops:
            stmt.need_var_name = True
        stmt.delete_if_unused = True
        return stmt

    def convert_clip_path(self, node):
        'Return Python code that defines a clipping path.'
        p_var = self.Statement.id2var(node[0].get_id())
        c_units = node.get('clipPathUnits')
        if c_units is None:
            code = ['clip_path(%s)' % p_var]
        else:
            code = ['clip_path(%s, clip_units=%s)' % (p_var, repr(c_units))]
        stmt = self.Statement(code, node.get_id(), [p_var])
        stmt.delete_if_unused = True
        return stmt

    def convert_marker(self, node):
        'Return Python code that defines a marker.'
        # Mark all of our descendants as lying within a marker.  This
        # suppresses the use of default styles.
        for child in node:
            self.set_within_marker(child)

        # Extract all of the parameters that define the shape.
        x, y = node.get('refX'), node.get('refY')
        orient = node.get('orient')
        m_units = node.get('markerUnits')
        v_box = node.get('viewBox')
        extra, extra_deps = self.extra_args(node, {}, {})
        shape_var = self.Statement.id2var(node[0].get_id())

        # Construct a list of optional arguments.
        marker_args = []
        if x is not None or y is not None:
            marker_args.append('ref=(%s, %s)' % (x or '0', y or '0'))
        if orient is not None:
            marker_args.append('orient=%s' % repr(orient))
        if m_units is not None:
            marker_args.append('marker_units=%s' % repr(m_units))
        if v_box is not None:
            x0, y0, wd, ht = [float(c) for c in v_box.split()]
            marker_args.append('view_box=((%.5g, %.5g), (%.5g, %.5g))' %
                               (x0, y0, x0 + wd, y0 + ht))

        # Generate code and wrap it in a statement.
        m_arg_str = ', '.join(marker_args)
        if m_arg_str != '':
            m_arg_str = ', ' + m_arg_str
        code = ['marker(%s%s%s)' % (shape_var, m_arg_str, extra)]
        stmt = self.Statement(code, node.get_id(), [shape_var] + extra_deps)
        stmt.delete_if_unused = True
        return stmt

    def convert_hyperlink(self, node):
        'Return Python code for wrapping objects within a hyperlink.'
        # Construct a list of arguments.
        link_args = []
        href = node.get('href') or \
            node.get('{http://www.w3.org/1999/xlink}href')
        link_args.append(repr(href))
        try:
            title = [c for c in node if c.TAG == 'title'][0].text
        except IndexError:
            title = node.get('{http://www.w3.org/1999/xlink}title')
        if title is not None:
            link_args.append('title=%s' % repr(title))
        target = node.get('target')
        if target is not None:
            link_args.append('target=%s' % repr(target))
        mime_type = node.get('type')
        if mime_type is not None:
            link_args.append('mime_type=%s' % repr(mime_type))
        link_args_str = ', '.join(link_args)
        extra, extra_deps = self.extra_args(node, {}, {})

        # Generate code and wrap it in a statement.
        child_ids = [c.get_id() for c in node if c.TAG != 'title']
        child_vars = [self.Statement.id2var(i) for i in child_ids]
        if len(child_vars) == 1:
            child_vars_str = child_vars[0]
        else:
            child_vars_str = '[%s]' % (', '.join(child_vars))
        code = ['hyperlink(%s, %s%s)' %
                (child_vars_str, link_args_str, extra)]
        return self.Statement(code, node.get_id(), child_ids + extra_deps)

    def _svg_str_to_python(self, str):
        'Convert an SVG attribute string to an appropriate Python type.'
        # Recursively convert lists.
        fields = str.replace(',', ' ').replace(';', ' ').split()
        if len(fields) > 1:
            return [self._svg_str_to_python(f) for f in fields]

        # Specially handle certain data types then fall back to strings.
        try:
            return int(str)
        except ValueError:
            pass
        try:
            return float(str)
        except ValueError:
            pass
        try:
            str2bool = {'true': True, 'false': False}
            return str2bool[str]
        except KeyError:
            pass
        return repr(str)

    def convert_path_effect(self, node):
        'Return Python code for instantiating a path effect.'
        # Convert the path effect's attributes to Python keyword arguments.
        args = [repr(node.get('effect'))]
        str2bool = {'true': True, 'false': False}
        for k, v in sorted(node.attrib.items()):
            # Skip "special" keys.
            if k in ['effect', 'id']:
                continue
            args.append('%s=%s' % (k, self._svg_str_to_python(v)))

        # Generate code and wrap it in a statement.
        code = ['path_effect(%s)' % ', '.join(args)]
        stmt = self.Statement(code, node.get_id(), [])
        stmt.delete_if_unused = True
        return stmt

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
                                   '//svg:g | '
                                   '//svg:filter | '
                                   '//svg:linearGradient | '
                                   '//svg:radialGradient | '
                                   '//svg:clipPath | '
                                   '//svg:marker | '
                                   '//svg:a | '
                                   '//inkscape:path-effect'):
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
            elif isinstance(node, inkex.Filter):
                stmts.append(self.convert_filter(node))
            elif isinstance(node, inkex.LinearGradient):
                stmts.append(self.convert_linear_gradient(node))
            elif isinstance(node, inkex.RadialGradient):
                stmts.append(self.convert_radial_gradient(node))
            elif isinstance(node, inkex.ClipPath):
                stmts.append(self.convert_clip_path(node))
            elif isinstance(node, inkex.Marker):
                stmts.append(self.convert_marker(node))
            elif isinstance(node, inkex.Anchor):
                stmts.append(self.convert_hyperlink(node))
            elif isinstance(node, inkex.PathEffect):
                stmts.append(self.convert_path_effect(node))
            else:
                raise inkex.AbortExtension(_('Internal error converting %s' %
                                             repr(node)))
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
            if stmt.delete_if_unused and not stmt.need_var_name:
                continue
            ln = str(stmt) + '\n'
            stream.write(ln.encode('utf-8'))


if __name__ == '__main__':
    SvgToPythonScript().run()
