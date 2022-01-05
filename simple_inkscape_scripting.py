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
import PIL.Image
import base64
import io
import lxml
import os
import re
import sys

# The following imports are provided for user convenience.
from math import *
from random import *
from inkex.paths import *
from inkex.transforms import Transform


# ----------------------------------------------------------------------

# The following definitions are utilized by the user convenience
# functions.

# Define a prefix for all IDs we assign.  This contains randomness so
# running the same script repeatedly will be unlikely to produce
# conflicting IDs.
_id_prefix = 'simp-ink-scr-%d-' % randint(100000, 999999)

# Keep track of the next ID to append to _id_prefix.
_next_obj_id = 1

# Store all SimpleObjects the user creates in _simple_objs.
_simple_objs = []

# Store the user-specified default style in _default_style.
_default_style = {}

# Most shapes use this as their default style.
_common_shape_style = {'stroke': 'black',
                       'fill': 'none'}

# Store the default transform in _default_transform.
_default_transform = None

# Store the top-level SVG tree in _svg_root.
_svg_root = None


def _debug_print(*args):
    'Implement print in terms of inkex.utils.debug.'
    inkex.utils.debug(' '.join([str(a) for a in args]))


def _unique_id():
    'Return a unique ID.'
    global _id_prefix, _next_obj_id
    tag = '%s%d' % (_id_prefix, _next_obj_id)
    _next_obj_id += 1
    return tag


def _split_two_or_one(val):
    '''Split a tuple into two values and a scalar into two copies of the
    same value.'''
    try:
        a, b = val
    except TypeError:
        a, b = val, val
    return a, b


def _abend(msg):
    'Abnormally end execution with an error message.'
    inkex.utils.errormsg(msg)
    sys.exit(1)


class Mpath(inkex.Use):
    'Point to a path object.'
    tag_name = 'mpath'


class SimpleObject(object):
    'Encapsulate an Inkscape object and additional metadata.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, base_style,
                 obj_style, track=True):
        'Wrap an Inkscape object within a SimpleObject.'
        # Combine the current and default transforms.
        ts = []
        if transform is not None:
            transform = str(transform)   # Transform may be an inkex.Transform.
            if transform != '':
                ts.append(transform)
        if _default_transform is not None and _default_transform != '':
            ts.append(_default_transform)
        if ts == []:
            self._transform = inkex.Transform()
        else:
            obj.transform = ' '.join(ts)
            self._transform = inkex.Transform(obj.transform)

        # Optionally indicate that connectors are to avoid this object.
        if conn_avoid:
            obj.set('inkscape:connector-avoid', 'true')

        # Optionally employ a clipping path.
        if clip_path_obj is not None:
            if isinstance(clip_path_obj, str):
                clip_str = clip_path_obj
            else:
                if not isinstance(clip_path_obj, SimpleClippingPath):
                    clip_path_obj = clip_path(clip_path_obj)
                clip_str = 'url(#%s)' % clip_path_obj._inkscape_obj.get_id()
            obj.set('clip-path', clip_str)

        # Combine the current and default styles.
        ext_style = self._construct_style(base_style, obj_style)
        if ext_style != '':
            obj.style = ext_style

        # Assign the object a unique ID.
        obj.set_id(_unique_id())

        # Store the modified Inkscape object.
        self._inkscape_obj = obj
        if track:
            _simple_objs.append(self)

    def __str__(self):
        '''Return the object as a string of the form "url(#id)".  This
        enables the object to be used as a value in style key=value
        arguments such as shape_inside.'''
        return 'url(#%s)' % self._inkscape_obj.get_id()

    def _construct_style(self, base_style, new_style):
        '''Combine a shape default style, a global default style, and an
        object-specific style and return the result as a string.'''
        # Start with the default style for the shape type.
        style = base_style.copy()

        # Update the style according to the current global default style.
        style.update(_default_style)

        # Update the style based on the object-specific style.
        for k, v in new_style.items():
            k = k.replace('_', '-')
            if v is None:
                style[k] = None
            else:
                style[k] = str(v)

        # Remove all keys whose value is None.
        style = {k: v for k, v in style.items() if v is not None}

        # Concatenate the style into a string.
        return ';'.join(['%s:%s' % kv for kv in style.items()])

    def _get_bbox_center(self):
        "Return the center of an object's bounding box."
        bbox = self._inkscape_obj.bounding_box()
        return (bbox.center_x, bbox.center_y)

    def bounding_box(self):
        "Return the object's bounding box as an inkex.transforms.BoundingBox."
        return self._inkscape_obj.bounding_box()

    def to_def(self):
        '''Convert the object to a definition, removing it from the list of
        rendered objects.'''
        global _simple_objs, _svg_root
        _simple_objs = [o for o in _simple_objs if o is not self]
        _svg_root.defs.add(self._inkscape_obj)
        return self

    @property
    def transform(self):
        "Return the object's current transformation as an inkex.Transform."
        return self._transform

    @transform.setter
    def transform(self, xform):
        '''Assign a new transformation to an object from either a string or
        an inkex.Transform.'''
        if isinstance(xform, inkex.Transform):
            self._transform = xform
        else:
            self._transform = inkex.Transform(xform)
        self._apply_transform()

    def _apply_transform(self):
        "Apply the SimpleObject's transform to the underlying SVG object."
        if self._transform != self._inkscape_obj.transform:
            self._inkscape_obj.set('transform', self._transform)

    def _diff_transforms(self, objs):
        'Return a list of transformations to animate.'
        # Determine if any object has a different transformation from any
        # other.
        xforms = [o.get('transform') for o in objs]
        if all([x is None for x in xforms]):
            return []  # No transform on any object: nothing to animate.
        for i, x in enumerate(xforms):
            if x is None:
                xforms[i] = inkex.Transform()
            else:
                xforms[i] = inkex.Transform(x)
        if len(set([str(x) for x in xforms])) == 1:
            return []  # All transforms are identical: nothing to animate.
        hexads = [list(x.to_hexad()) for x in xforms]

        # Find changes in translation.
        xlate_values = []
        for h in hexads:
            xlate_values.append('%.5g %.5g' % (h[4], h[5]))

        # Find changes in scale.
        scale_values = []
        for i, h in enumerate(hexads):
            sx = sqrt(h[0]**2 + h[1]**2)
            sy = sqrt(h[2]**2 + h[3]**2)
            if abs(sx - sy) <= 0.00001:
                scale_values.append('%.5g' % ((sx + sy)/2))
            else:
                scale_values.append('%.5g %.5g' % (sx, sy))
            h[0] /= sx
            h[1] /= sx
            h[2] /= sy
            h[3] /= sy
            hexads[i] = h

        # Find changes in rotation, initially as numeric radians.
        rot_values = []
        for h in hexads:
            # Ignore transforms with inconsistent rotation angles.
            angles = [acos(h[0]), asin(h[1]), asin(-h[2]), acos(h[3])]
            if abs(angles[0] - angles[3]) > 0.00001 or \
               abs(angles[1] - angles[2]) > 0.00001:
                return []   # Transform is too complicated for us to handle.

            # Determine the angle in the correct quadrant.
            if h[0] >= 0 and h[1] >= 0:
                ang = angles[0]
            elif h[0] < 0 and h[1] >= 0:
                ang = angles[0]
            elif h[0] < 0 and h[1] < 0:
                ang = pi - angles[1]
            else:
                ang = 2*pi + angles[1]
            rot_values.append(ang)

        # Convert changes in rotation from radians to degrees and floats to
        # strings.
        rot_values = ['%.5g' % (r*180/pi) for r in rot_values]

        # Return a list of transformations to apply.
        xform_list = []
        if len(set(scale_values)) == len(objs):
            xform_list.append(('scale', scale_values))
        if len(set(rot_values)) == len(objs):
            xform_list.append(('rotate', rot_values))
        if len(set(xlate_values)) == len(objs):
            xform_list.append(('translate', xlate_values))
        return xform_list

    def _animate_transforms(self, objs, duration,
                            begin_time, key_times,
                            repeat_count, repeat_time,
                            keep, attr_filter):
        'Specially handle animating transforms.'
        # Determine the transforms to apply.  We treat each transform as a
        # filterable attribute.
        xforms = self._diff_transforms(objs)
        if attr_filter is not None:
            xforms = [xf for xf in xforms if attr_filter(xf[0])]
        if len(xforms) == 0:
            return  # No transforms to animate

        # Animate each transform in turn.
        target = self
        for i, xf in enumerate(xforms):
            # Only one transform animation can be applied per object.
            # Hence, we keep wrapping the object in successive levels of
            # groups and apply one transform to each group.
            if i > 0:
                target = group(target)
            anim = lxml.etree.Element('animateTransform')
            anim.set('attributeName', 'transform')
            anim.set('type', xf[0])
            anim.set('values', '; '.join(xf[1]))
            if duration is not None:
                anim.set('dur', str(duration))
            if begin_time is not None:
                anim.set('begin', str(begin_time))
            if key_times is not None:
                if len(key_times) != len(iobjs):
                    _abend('Expected %d key times but saw %d' %
                           (len(iobjs), len(key_times)))
                anim.set('keyTimes', '; '.join([str(kt) for kt in key_times]))
            if repeat_count is not None:
                anim.set('repeatCount', str(repeat_count))
            if repeat_time is not None:
                anim.set('repeatDur', str(repeat_time))
            if keep:
                anim.set('fill', 'freeze')
            target._inkscape_obj.append(anim)

    def _diff_attributes(self, objs):
        '''Given a list of ShapeElements, return a dictionary mapping an
        attribute name to a list of values it takes on across all of the
        ShapeElements.'''
        # Do nothing if we don't have at least two objects.
        if len(objs) < 2:
            return {}  # Too few objects on which to compute differences

        # For each attribute in the first object, produce a list of
        # corresponding attributes in all other objects.
        attr2vals = {}
        for a in objs[0].attrib:
            if a in ['id', 'style', 'transform']:
                continue
            vs = [o.get(a) for o in objs]
            vs = [v for v in vs if v is not None]
            if len(set(vs)) == len(objs):
                attr2vals[a] = vs

        # Handle styles specially.
        if objs[0].get('style') is not None:
            style = inkex.Style(objs[0].get('style'))
            for a in style:
                vs = []
                for o in objs:
                    obj_style = inkex.Style(o.get('style'))
                    vs.append(obj_style.get(a))
                if len(set(vs)) == len(objs):
                    attr2vals[a] = vs
        return attr2vals

    def _key_times_string(self, key_times, num_objs, interpolation):
        'Validate key-time values before converting them to a string.'
        # Ensure the argument is the correct type (list of floats) and
        # length and is ordered correctly.
        orig_kt = [float(v) for v in key_times]
        kt = sorted(orig_kt)
        if kt != orig_kt:
            _abend('Key times must be sorted: %s' % repr(orig_kt))
        if len(kt) != num_objs:
            _abend('Expected a list of %d key times but saw %d' %
                   (num_objs, len(kt)))

        # Ensure the first and last values are as required by interpolation.
        if interpolation is None:
            interpolation = 'linear'  # Default for SVG
        if interpolation in ['linear', 'spline', 'discrete'] and kt[0] != 0:
            _abend('The first key time must be 0: %s' % repr(kt))
        if interpolation in ['linear', 'spline'] and kt[-1] != 1:
            _abend('The final key time must be 1: %s' % repr(kt))

        # Convert the key times to a string, and return it.
        return '; '.join(['%.5g' % v for v in kt])

    def animate(self, objs=[], duration=None,
                begin_time=None, key_times=None,
                repeat_count=None, repeat_time=None, keep=True,
                interpolation=None, path=None, path_rotate=None,
                at_end=False, attr_filter=None):
        "Animate the object through each of the given objects' appearance."
        # Prepare the list of objects.
        try:
            iobjs = [o._inkscape_obj for o in objs]
        except TypeError:
            objs = [objs]
            iobjs = [o._inkscape_obj for o in objs]
        if at_end:
            all_iobjs = iobjs + [self._inkscape_obj]
        else:
            all_iobjs = [self._inkscape_obj] + iobjs

        # Identify the differences among all the objects.
        attr2vals = self._diff_attributes(all_iobjs)
        if attr_filter is not None:
            attr2vals = {k: v for k, v in attr2vals.items() if attr_filter(k)}

        # Add one <animate> element per attribute.
        for a, vs in attr2vals.items():
            anim = lxml.etree.Element('animate')
            anim.set('attributeName', a)
            anim.set('values', '; '.join(vs))
            if duration is not None:
                anim.set('dur', str(duration))
            if begin_time is not None:
                anim.set('begin', str(begin_time))
            if key_times is not None:
                kt_str = self._key_times_string(key_times,
                                                len(all_iobjs),
                                                interpolation)
                anim.set('keyTimes', kt_str)
            if repeat_count is not None:
                anim.set('repeatCount', str(repeat_count))
            if repeat_time is not None:
                anim.set('repeatDur', str(repeat_time))
            if keep:
                anim.set('fill', 'freeze')
            if interpolation is not None:
                anim.set('calcMode', str(interpolation))
            self._inkscape_obj.append(anim)

        # Add an <animateMotion> element if a path was supplied.
        if path is not None:
            # Create an <animateMotion> element.
            animMo = lxml.etree.Element('animateMotion')
            if duration is not None:
                animMo.set('dur', str(duration))
            if begin_time is not None:
                animMo.set('begin', str(begin_time))
            if key_times is not None:
                kt_str = self._key_times_string(key_times,
                                                len(all_iobjs),
                                                interpolation)
                anim.set('keyTimes', kt_str)
            if repeat_count is not None:
                animMo.set('repeatCount', str(repeat_count))
            if repeat_time is not None:
                animMo.set('repeatDur', str(repeat_time))
            if keep:
                animMo.set('fill', 'freeze')
            if interpolation is not None:
                animMo.set('calcMode', str(interpolation))
            if path_rotate is not None:
                animMo.set('rotate', str(path_rotate))

            # Insert an <mpath> child under <animateMotion> that links to
            # the given path.
            mpath = Mpath()
            mpath.href = path._inkscape_obj.get_id()
            animMo.append(mpath)

            # Add the <animateMotion> to the target object.
            self._inkscape_obj.append(animMo)

        # Handle animated transforms specially because only one can apply
        # to a given object.  We therefore add levels of grouping, each
        # with one <animateTransform> applied to it, as necessary.
        self._animate_transforms(all_iobjs, duration,
                                 begin_time, key_times,
                                 repeat_count, repeat_time,
                                 keep, attr_filter)

        # Remove all given objects from the top-level set of objects.
        global _simple_objs
        rem_objs = set([o for o in objs if o is not self])
        _simple_objs = [o for o in _simple_objs if o not in rem_objs]


class SimpleMarker(SimpleObject):
    'Represent a path marker, which wraps an arbitrary object.'

    def __init__(self, obj, **style):
        super().__init__(obj, transform=None, conn_avoid=False,
                         clip_path_obj=None, base_style={}, obj_style=style,
                         track=True)


class SimpleGroup(SimpleObject):
    'Represent a group of objects.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, base_style,
                 obj_style, track=True):
        super().__init__(obj, transform, conn_avoid, clip_path_obj, base_style,
                         obj_style, track)
        self._children = []

    def __len__(self):
        return len(self._children)

    def __getitem__(self, idx):
        return self._children[idx]

    def __iter__(self):
        yield from self._children

    def add(self, objs):
        'Add one or more SimpleObjects to the group.'
        # Ensure the addition is legitimate.
        global _simple_objs
        if type(objs) != list:
            objs = [objs]   # Convert scalar to list
        for obj in objs:
            if not isinstance(obj, SimpleObject):
                _abend(_('Only Simple Inkscape Scripting '
                         'objects can be added to a group.'))
            if isinstance(obj, SimpleLayer):
                _abend(_('Layers cannot be added to groups.'))
                return
            if obj not in _simple_objs:
                _abend(_('Only objects not already in a group '
                         'or layer can be added to a group.'))

            # Remove the object from the top-level set of objects.
            _simple_objs = [o for o in _simple_objs if o is not obj]

            # Add the object to both the SimpleGroup and the SVG group.
            self._children.append(obj)
            self._inkscape_obj.add(obj._inkscape_obj)


class SimpleLayer(SimpleGroup):
    'Represent an Inkscape layer.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, base_style,
                 obj_style):
        super().__init__(obj, transform, conn_avoid, clip_path_obj, base_style,
                         obj_style, track=False)
        self._children = []
        global _svg_root
        _svg_root.add(self._inkscape_obj)


class SimpleClippingPath(SimpleGroup):
    'Represent a clipping path.'

    def __init__(self, obj, clip_units):
        super().__init__(obj, transform=None, conn_avoid=False,
                         clip_path_obj=None, base_style={}, obj_style={},
                         track=False)
        self._children = []
        if clip_units is not None:
            self._inkscape_obj.set('clipPathUnits', clip_units)
        _svg_root.defs.add(self._inkscape_obj)


class SimpleHyperlink(SimpleGroup):
    'Represent a hyperlink.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, base_style,
                 obj_style):
        super().__init__(obj, transform, conn_avoid, clip_path_obj, base_style,
                         obj_style, track=True)


class SimpleFilter(object):
    'Represent an SVG filter effect.'

    def __init__(self, defs, name=None, pt1=None, pt2=None,
                 filter_units=None, primitive_units=None, **style):
        self.filt = defs.add(inkex.Filter())
        if name is not None and name != '':
            self.filt.set('inkscape:label', name)
        if pt1 is not None or pt2 is not None:
            x0 = float(pt1[0] or 0)
            y0 = float(pt1[1] or 0)
            x1 = float(pt2[0] or 1)
            y1 = float(pt2[1] or 1)
            self.filt.set('x', x0)
            self.filt.set('y', y0)
            self.filt.set('width', x1 - x0)
            self.filt.set('height', y1 - y0)
        if filter_units is not None:
            self.filt.set('filterUnits', filter_units)
        if primitive_units is not None:
            self.filt.set('primitiveUnits', primitive_units)
        style_str = str(inkex.Style(**style))
        if style_str != '':
            self.filt.set('style', style_str)

    def __str__(self):
        return 'url(#%s)' % self.filt.get_id()

    class SimpleFilterPrimitive(object):
        'Represent one component of an SVG filter effect.'

        def __init__(self, filt, ftype, **kw_args):
            # Assign a random ID for the default result.
            all_args = {'result': _unique_id()}

            # Make "src1" and "src2" smart aliases for "in" and "in2".
            s2i = {'src1': 'in', 'src2': 'in2'}
            for k, v in kw_args.items():
                k = k.replace('_', '-')
                if k in s2i:
                    # src1 and src2 accept either SimpleFilterPrimitive
                    # objects -- extracting their "result" string -- or
                    # ordinary strings.
                    if isinstance(v, self.__class__):
                        v = v.prim.get('result')
                    all_args[s2i[k]] = v
                elif type(v) == str:
                    # Strings are used unmodified.
                    all_args[k] = v
                else:
                    try:
                        # Sequences (other than strings, which are
                        # sequences of characters) are converted to a
                        # string of space-separated values.
                        all_args[k] = ' '.join([str(e) for e in v])
                    except TypeError:
                        # Scalars are converted to strings.
                        all_args[k] = str(v)

            # Add a primitive to the filter.
            self.prim = filt.add_primitive(ftype, **all_args)

    def add(self, ftype, **kw_args):
        'Add a primitive to a filter and return an object representation.'
        return self.SimpleFilterPrimitive(self.filt, 'fe' + ftype, **kw_args)


class SimpleGradient(object):
    'Virtual base class for an SVG linear or radial gradient pattern.'

    # Map Inkscape repetition names to SVG names.
    repeat_to_spread = {'none':      'pad',
                        'reflected': 'reflect',
                        'direct':    'repeat'}

    def _set_common(self, grad, repeat=None, gradient_units=None,
                    template=None, transform=None, **style):
        'Set arguments that are common to both linear and radial gradients.'
        if repeat is not None:
            try:
                spread = self.repeat_to_spread[repeat]
            except KeyError:
                spread = repeat
            grad.set('spreadMethod', spread)
        if gradient_units is not None:
            grad.set('gradientUnits', gradient_units)
        if template is not None:
            tmpl_name = str(template)[5:-1]  # Strip the 'url(#' and the ')'.
            grad.set('href', '#%s' % tmpl_name)        # No Inkscape support
            grad.set('xlink:href', '#%s' % tmpl_name)  # Deprecated by SVG
        if transform is not None:
            grad.set('gradientTransform', transform)
        style_str = str(inkex.Style(**style))
        if style_str != '':
            grad.set('style', style_str)
        grad.set('inkscape:collect', 'always')

    def __str__(self):
        return 'url(#%s)' % self.grad.get_id()

    def add_stop(self, ofs, color, opacity=None, **style):
        'Add a stop to a gradient.'
        stop = inkex.Stop()
        stop.offset = ofs
        stop.set('stop-color', color)
        if opacity is not None:
            stop.set('stop-opacity', opacity)
        style_str = str(inkex.Style(**style))
        if style_str != '':
            stop.set('style', style_str)
        self.grad.append(stop)


class SimpleLinearGradient(SimpleGradient):
    'Represent an SVG linear gradient pattern.'

    def __init__(self, defs, pt1=None, pt2=None, repeat=None,
                 gradient_units=None, template=None, transform=None,
                 **style):
        grad = inkex.LinearGradient()
        if pt1 is not None:
            grad.set('x1', pt1[0])
            grad.set('y1', pt1[1])
        if pt2 is not None:
            grad.set('x2', pt2[0])
            grad.set('y2', pt2[1])
        self._set_common(grad, repeat, gradient_units, template,
                         transform, **style)
        self.grad = defs.add(grad)


class SimpleRadialGradient(SimpleGradient):
    'Represent an SVG radial gradient pattern.'

    def __init__(self, defs, center=None, radius=None, focus=None, fr=None,
                 repeat=None, gradient_units=None, template=None,
                 transform=None, **style):
        grad = inkex.RadialGradient()
        if center is not None:
            grad.set('cx', center[0])
            grad.set('cy', center[1])
        if radius is not None:
            grad.set('r', radius)
        if focus is not None:
            grad.set('fx', focus[0])
            grad.set('fy', focus[1])
        if fr is not None:
            grad.set('fr', fr)
        self._set_common(grad, repeat, gradient_units, template,
                         transform, **style)
        self.grad = defs.add(grad)


# ----------------------------------------------------------------------

# The following functions represent the Simple Inkscape Scripting API
# and are intended to be called by user code.

def style(**kwargs):
    'Modify the default style.'
    global _default_style
    for k, v in kwargs.items():
        k = k.replace('_', '-')
        if v is None:
            _default_style[k] = None
        else:
            _default_style[k] = str(v)


def transform(t):
    'Set the default transform.'
    global _default_transform
    _default_transform = str(t).strip()


def circle(center, radius, transform=None, conn_avoid=False, clip_path=None,
           **style):
    'Draw a circle.'
    obj = inkex.Circle(cx=str(center[0]), cy=str(center[1]), r=str(radius))
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def ellipse(center, radii, transform=None, conn_avoid=False, clip_path=None,
            **style):
    'Draw an ellipse.'
    rx, ry = _split_two_or_one(radii)
    obj = inkex.Ellipse(cx=str(center[0]), cy=str(center[1]),
                        rx=str(rx), ry=str(ry))
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def rect(pt1, pt2, round=None, transform=None, conn_avoid=False,
         clip_path=None, **style):
    'Draw a rectangle.'
    # Convert pt1 and pt2 to an upper-left starting point and
    # rectangle dimensions.
    x0 = min(pt1[0], pt2[0])
    y0 = min(pt1[1], pt2[1])
    x1 = max(pt1[0], pt2[0])
    y1 = max(pt1[1], pt2[1])
    wd = x1 - x0
    ht = y1 - y0

    # Draw the rectangle.
    obj = inkex.Rectangle(x=str(x0), y=str(y0),
                          width=str(wd), height=str(ht))

    # Optionally round the corners.
    if round is not None:
        try:
            rx, ry = round
        except TypeError:
            rx, ry = round, round
        obj.set('rx', str(rx))
        obj.set('ry', str(ry))
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def line(pt1, pt2, transform=None, conn_avoid=False, clip_path=None, **style):
    'Draw a line.'
    obj = inkex.Line(x1=str(pt1[0]), y1=str(pt1[1]),
                     x2=str(pt2[0]), y2=str(pt2[1]))
    base_style = {'stroke': 'black'}  # No need for fill='none' here.
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        base_style, style)


def polyline(coords, transform=None, conn_avoid=False, clip_path=None,
             **style):
    'Draw a polyline.'
    if len(coords) < 2:
        _abend(_('A polyline must contain at least two points.'))
    pts = ' '.join(["%s,%s" % (str(x), str(y)) for x, y in coords])
    obj = inkex.Polyline(points=pts)
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def polygon(coords, transform=None, conn_avoid=False, clip_path=None, **style):
    'Draw a polygon.'
    if len(coords) < 3:
        _abend(_('A polygon must contain at least three points.'))
    pts = ' '.join(["%s,%s" % (str(x), str(y)) for x, y in coords])
    obj = inkex.Polygon(points=pts)
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def regular_polygon(sides, center, radius, angle=-pi/2, round=0.0, random=0.0,
                    transform=None, conn_avoid=False, clip_path=None, **style):
    'Draw a regular polygon.'
    # Create a star object, which is also used for regular polygons.
    if sides < 3:
        _abend(_('A regular polygon must contain at least three points.'))
    obj = inkex.PathElement.star(center, (radius, radius/2), sides, round)

    # Set all the regular polygon's parameters.
    obj.set('sodipodi:arg1', angle)
    obj.set('sodipodi:arg2', angle + pi/sides)
    obj.set('inkscape:flatsided', 'true')   # Regular polygon, not star
    obj.set('inkscape:rounded', round)
    obj.set('inkscape:randomized', random)
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def star(sides, center, radii, angles=None, round=0.0, random=0.0,
         transform=None, conn_avoid=False, clip_path=None, **style):
    'Draw a star.'
    # Create a star object.
    if sides < 3:
        _abend(_('A star must contain at least three points.'))
    obj = inkex.PathElement.star(center, radii, sides, round)

    # If no angles were specified, point the star upwards.
    if angles is not None:
        pass
    elif radii[0] >= radii[1]:
        angles = (-pi/2, pi/sides - pi/2)
    else:
        angles = (pi/2, pi/sides + pi/2)

    # Set all the star's parameters.
    obj.set('sodipodi:arg1', angles[0])
    obj.set('sodipodi:arg2', angles[1])
    obj.set('inkscape:flatsided', 'false')   # Star, not regular polygon
    obj.set('inkscape:rounded', round)
    obj.set('inkscape:randomized', random)
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def arc(center, radii, angles, arc_type='arc',
        transform=None, conn_avoid=False, clip_path=None, **style):
    'Draw an arc.'
    # Construct the arc proper.
    rx, ry = _split_two_or_one(radii)
    ang1, ang2 = angles
    obj = inkex.PathElement.arc(center, rx, ry, start=ang1, end=ang2)
    if arc_type in ['arc', 'slice', 'chord']:
        obj.set('sodipodi:arc-type', arc_type)
    else:
        _abend(_('Invalid arc_type "%s"' % str(arc_type)))

    # The arc is visible only in Inkscape because it lacks a path.
    # Here we manually add a path to the object.  (Is there a built-in
    # method for doing this?)
    p = []
    ang1 %= 2*pi
    ang2 %= 2*pi
    x0 = rx*cos(ang1) + center[0]
    y0 = ry*sin(ang1) + center[1]
    p.append(Move(x0, y0))
    delta_ang = (ang2 - ang1) % (2*pi)
    if delta_ang == 0.0:
        delta_ang = 2*pi   # Special case for full ellipses
    n_segs = int((delta_ang + pi/2) / (pi/2))
    for s in range(n_segs):
        a = ang1 + delta_ang*(s + 1)/n_segs
        x1 = rx*cos(a) + center[0]
        y1 = ry*sin(a) + center[1]
        p.append(Arc(rx, ry, 0, False, True, x1, y1))
    if arc_type == 'arc':
        obj.set('sodipodi:open', 'true')
    elif arc_type == 'slice':
        p.append(Line(center[0], center[1]))
        p.append(ZoneClose())
    elif arc_type == 'chord':
        p.append(ZoneClose())
    else:
        _abend(_('Invalid arc_type "%s"' % str(arc_type)))
    obj.path = inkex.Path(p)

    # Return a Simple Inkscape Scripting object.
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def path(elts, transform=None, conn_avoid=False, clip_path=None, **style):
    'Draw an arbitrary path.'
    if type(elts) == str:
        elts = re.split(r'[\s,]+', elts)
    if len(elts) == 0:
        _abend(_('A path must contain at least one path element.'))
    d = ' '.join([str(e) for e in elts])
    obj = inkex.PathElement(d=d)
    return SimpleObject(obj, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def connector(obj1, obj2, ctype='polyline', curve=0,
              transform=None, conn_avoid=False, clip_path=None, **style):
    'Connect two objects with a path.'
    # Create a path that links the two objects' centers.
    center1 = obj1._get_bbox_center()
    center2 = obj2._get_bbox_center()
    d = 'M %g,%g L %g,%g' % (center1[0], center1[1], center2[0], center2[1])
    path = inkex.PathElement(d=d)

    # Mark the path as a connector.
    path.set('inkscape:connector-type', str(ctype))
    path.set('inkscape:connector-curvature', str(curve))
    path.set('inkscape:connection-start', '#%s' % obj1._inkscape_obj.get_id())
    path.set('inkscape:connection-end', '#%s' % obj2._inkscape_obj.get_id())

    # Store the connector as its own object.
    return SimpleObject(path, transform, conn_avoid, clip_path,
                        _common_shape_style, style)


def text(msg, base, path=None, transform=None, conn_avoid=False,
         clip_path=None, **style):
    'Typeset a piece of text, optionally along a path.'
    # Create the basic text object.
    obj = inkex.TextElement(x=str(base[0]), y=str(base[1]))
    obj.set('xml:space', 'preserve')
    obj.text = msg

    # Optionally place the text along a path.
    if path is not None:
        tp = obj.add(inkex.TextPath())
        tp.href = path._inkscape_obj.get_id()

    # Wrap the text object within a SimpleObject.
    return SimpleObject(obj, transform, conn_avoid, clip_path, {}, style)


def more_text(msg, base=None, conn_avoid=False, **style):
    'Append text to the preceding object, which must be text.'
    if len(_simple_objs) == 0 or \
       not isinstance(_simple_objs[-1]._inkscape_obj, inkex.TextElement):
        _abend(_('more_text must immediately follow'
                 ' text or another more_text'))
    obj = _simple_objs[-1]
    tspan = inkex.Tspan()
    tspan.text = msg
    tspan.style = obj._construct_style({}, style)
    if base is not None:
        tspan.set('x', str(base[0]))
        tspan.set('y', str(base[1]))
    obj._inkscape_obj.append(tspan)
    return obj


def image(fname, ul, embed=True, transform=None, conn_avoid=False,
          clip_path=None, **style):
    'Include an image, either embedded or linked.'
    obj = inkex.Image()
    obj.set('x', ul[0])
    obj.set('y', ul[1])
    if embed:
        # Read and embed the named file.
        img = PIL.Image.open(fname)
        data = io.BytesIO()
        img.save(data, img.format)
        mime = PIL.Image.MIME[img.format]
        b64 = base64.b64encode(data.getvalue()).decode('utf-8')
        uri = 'data:%s;base64,%s' % (mime, b64)
    else:
        # Point to an external file.
        uri = fname
    obj.set('xlink:href', uri)
    return SimpleObject(obj, transform, conn_avoid, clip_path, {}, style)


def clone(obj, transform=None, conn_avoid=False, clip_path=None, **style):
    'Return a linked clone of the object.'
    c = inkex.Use()
    c.href = obj._inkscape_obj.get_id()
    return SimpleObject(c, transform, conn_avoid, clip_path, {}, style)


def group(objs=[], transform=None, conn_avoid=False, clip_path=None,
          **style):
    'Create a container for other objects.'
    g = inkex.Group()
    g_obj = SimpleGroup(g, transform, conn_avoid, clip_path, {}, style)
    g_obj.add(objs)
    return g_obj


def layer(name, objs=[], transform=None, conn_avoid=False, clip_path=None,
          **style):
    'Create a container for other objects.'
    layer = inkex.Layer.new(name)
    l_obj = SimpleLayer(layer, transform, conn_avoid, clip_path, {}, style)
    l_obj.add(objs)
    return l_obj


def hyperlink(objs, href, title=None, target=None, mime_type=None,
              transform=None, conn_avoid=False, clip_path=None, **style):
    'Hyperlink one or more objects to a given URI.'
    anc = inkex.Anchor()
    anc.set('{http://www.w3.org/1999/xlink}href', href)  # Older SVG
    anc.set('href', href)                                # Newer SVG
    if title is not None:
        # Inkscape uses primarily the older SVG xlink:title attribute.
        anc.set('{http://www.w3.org/1999/xlink}title', title)

        # Newer SVG files should include a <title> element.
        t_obj = lxml.etree.Element('title')
        t_obj.text = title
        anc.append(t_obj)
    if target is not None:
        anc.set('target', target)
    if mime_type is not None:
        anc.set('type', mime_type)
    anc_obj = SimpleHyperlink(anc, transform, conn_avoid, clip_path, {}, style)
    anc_obj.add(objs)
    return anc_obj


def inkex_object(obj, transform=None, conn_avoid=False, clip_path=None,
                 **style):
    'Expose an arbitrary inkex-created object to Simple Inkscape Scripting.'
    return SimpleObject(obj, transform, conn_avoid, clip_path, {}, style)


def filter_effect(name=None, pt1=None, pt2=None,
                  filter_units=None, primitive_units=None, **style):
    'Return an object representing an empty filter effect.'
    return SimpleFilter(_svg_root.defs, name, pt1, pt2,
                        filter_units, primitive_units, **style)


def linear_gradient(pt1=None, pt2=None, repeat=None, gradient_units=None,
                    template=None, transform=None, **style):
    'Return an object representing a linear gradient.'
    return SimpleLinearGradient(_svg_root.defs, pt1, pt2, repeat,
                                gradient_units, template, transform,
                                **style)


def radial_gradient(center=None, radius=None, focus=None, fr=None,
                    repeat=None, gradient_units=None, template=None,
                    transform=None, **style):
    'Return an object representing a radial gradient.'
    return SimpleRadialGradient(_svg_root.defs, center, radius, focus, fr,
                                repeat, gradient_units, template,
                                transform, **style)


def clip_path(obj, clip_units=None):
    'Convert an object to a clipping path.'
    clip = SimpleClippingPath(inkex.ClipPath(), clip_units)
    obj._apply_transform()
    clip.add(obj)
    return clip


def marker(obj, ref=None, orient='auto', marker_units=None,
           view_box=None, **style):
    'Convert an object to a marker.'
    global _simple_objs
    _simple_objs = [o for o in _simple_objs if o is not obj]
    m = inkex.Marker(obj._inkscape_obj.copy())  # Copy so we can reuse obj.
    if ref is not None:
        m.set('refX', str(ref[0]))
        m.set('refY', str(ref[1]))
    m.set('orient', str(orient))
    if marker_units is not None:
        m.set('markerUnits', marker_units)
    if view_box == 'auto':
        bb = obj.bounding_box()
        m.set('viewBox', '%.5g %.5g %.5g %.5g' %
              (bb.left, bb.top, bb.width, bb.height))
    elif view_box is not None:
        ul, lr = view_box
        x0, y0 = ul
        x1, y1 = lr
        m.set('viewBox', '%.5g %.5g %.5g %.5g' % (x0, y0, x1 - x0, y1 - y0))
    return SimpleMarker(m, **style).to_def()


# ----------------------------------------------------------------------

class SimpleInkscapeScripting(inkex.GenerateExtension):
    'Help the user create Inkscape objects with a simple API.'

    def add_arguments(self, pars):
        'Process program parameters passed in from the UI.'
        pars.add_argument('--tab', dest='tab',
                          help='The selected UI tab when OK was pressed')
        pars.add_argument('--program', type=str,
                          help='Python code to execute')
        pars.add_argument('--py-source', type=str,
                          help='Python source file to execute')

    def container_transform(self):
        '''Return an empty tranform so as to preserve user-specified
        coordinates.'''
        return inkex.Transform()

    def generate(self):
        'Generate objects from user-provided Python code.'
        # Prepare global values we want to export.
        global _svg_root
        _svg_root = self.svg
        sis_globals = globals().copy()
        try:
            # Inkscape 1.2+
            sis_globals['width'] = self.svg.viewbox_width
            sis_globals['height'] = self.svg.viewbox_height
        except AttributeError:
            # Inkscape 1.0 and 1.1
            sis_globals['width'] = self.svg.width
            sis_globals['height'] = self.svg.height
        sis_globals['svg_root'] = self.svg
        sis_globals['print'] = _debug_print
        try:
            # Inkscape 1.2+
            convert_unit = self.svg.viewport_to_unit
        except AttributeError:
            # Inkscape 1.0 and 1.1
            convert_unit = self.svg.unittouu
        for unit in ['mm', 'cm', 'pt', 'px']:
            sis_globals[unit] = convert_unit('1' + unit)
        sis_globals['inch'] = \
            convert_unit('1in')  # "in" is a keyword.

        # Launch the user's script.
        code = ''
        py_source = self.options.py_source
        if py_source is not None and not os.path.isdir(py_source):
            # The preceding test for isdir is explained in
            # https://gitlab.com/inkscape/inkscape/-/issues/2822
            with open(self.options.py_source) as fd:
                code += fd.read()
            code += '\n'
        if self.options.program is not None:
            code += self.options.program.replace(r'\n', '\n')
        exec(code, sis_globals)

        # Yield all objects created to the Inkscape core.
        for obj in _simple_objs:
            obj._apply_transform()
            yield obj._inkscape_obj


if __name__ == '__main__':
    SimpleInkscapeScripting().run()
