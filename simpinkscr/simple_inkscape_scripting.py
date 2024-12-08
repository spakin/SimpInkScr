#! /usr/bin/env python

'''
Copyright (C) 2021-2023 Scott Pakin, scott-ink@pakin.org

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

import base64
import collections.abc
import datetime
import io
import math
import os
import random
import re
import string
try:
    import numpy
except ModuleNotFoundError:
    pass
import PIL.Image
import lxml
import inkex
import inkex.command
import urllib.request
from inkex.localization import inkex_gettext as _
from tempfile import TemporaryDirectory


# ----------------------------------------------------------------------

# The following classes are needed only until inkex gets around to
# providing its own versions.

class Animate(inkex.BaseElement):
    'Represent an <animate> element.'
    tag_name = 'animate'


class AnimateMotion(inkex.BaseElement):
    'Represent an <animateMotion> element.'
    tag_name = 'animateMotion'


class AnimateTransform(inkex.BaseElement):
    'Represent an <animateTransform> element.'
    tag_name = 'animateTransform'


# ----------------------------------------------------------------------

# The following variable, class, and function definitions are utilized by
# the user convenience functions.

# Define a prefix for all IDs we assign.  This contains randomness so
# running the same script repeatedly will be unlikely to produce
# conflicting IDs.
_id_prefix = 'simp-ink-scr-%d-' % random.randint(100000, 999999)

# Keep track of the next ID to append to _id_prefix.
_next_obj_id = 1

# Maintain all top-level SVG state in _simple_top.
_simple_top = None

# Store a stack of user-specified default styles in _default_style.
_default_style = [{}]

# Most shapes use this as their default style.
_common_shape_style = {'stroke': 'black',
                       'fill': 'none'}

# Store a stack of user-specified default transforms in _default_transform.
_default_transform = [None]

# Retain a reference to the user script's global variables.
_user_globals = {}


def _debug_print(*args):
    'Implement print in terms of inkex.utils.debug.'
    inkex.utils.debug(' '.join([str(a) for a in args]))


def _split_two_or_one(val):
    '''Split a tuple into two values and a scalar into two copies of the
    same value.'''
    try:
        a, b = val
    except TypeError:
        a, b = val, val
    return a, b


def _python_to_svg_str(val):
    'Convert a Python value to a string suitable for use in an SVG attribute.'
    if isinstance(val, str):
        # Strings are used unmodified.
        return val
    if isinstance(val, bool):
        # Booleans are converted to lowercase strings.
        return str(val).lower()
    if isinstance(val, float):
        # Floats are converted using a fair number of significant digits.
        return '%.10g' % val
    if isinstance(val, inkex.Color):
        # Colors are converted to strings even though they're iterables.
        return str(val)
    if isinstance(val, collections.abc.Iterable):
        # Iterables are converted recursively but with one special case:
        # iterables of strings are concatenated with commas and quoted if
        # they contain spaces.  This special case covers passing a list of
        # strings to the font_family attribute.
        if all([isinstance(e, str) for e in val]):
            # Special case
            str_list = [s.replace(',', '&#44').replace(';', '&#59')
                        for s in val]
            str_list = ['"' + s + '"' if ' ' in s else s
                        for s in str_list]
            return ', '.join(str_list)
        else:
            # Common case
            return ' '.join([_python_to_svg_str(v) for v in val])
    try:
        # Simple Inkscape Scripting objects are converted to a string of
        # the form "url(#id)".
        return val.get_inkex_object().get_id(as_url=2)
    except AttributeError:
        pass
    try:
        # inkex objects also are converted to a string of the form
        # "url(#id)".
        return val.get_id(as_url=2)
    except AttributeError:
        pass
    return str(val)  # Everything else is converted to a string as usual.


def _svg_str_to_python(s):
    'Convert an SVG attribute string to an appropriate Python type.'
    # Recursively convert lists.
    fields = s.replace(',', ' ').replace(';', ' ').split()
    if len(fields) > 1:
        return [_svg_str_to_python(f) for f in fields]

    # Specially handle numerical data types then fall back to strings.
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _read_image_as_base64(fname):
    "Return image data in base64 encoding and the image's MIME type."
    try:
        # See if the image is SVG.
        try:
            # Local file
            with open(fname, mode='rb') as r:
                data = r.read()
        except FileNotFoundError:
            # URL
            with urllib.request.urlopen(fname) as r:
                data = r.read()
        tree = lxml.etree.fromstring(data)
        mime = 'image/svg+xml'
        b64 = base64.b64encode(data).decode('utf-8')
        width = inkex.units.convert_unit(tree.get('width', '1'), 'px')
        height = inkex.units.convert_unit(tree.get('height', '1'), 'px')
        size = (width, height)
    except lxml.etree.XMLSyntaxError:
        # The image is not SVG.  Use PIL to interpret it as a bitmap image.
        try:
            # Local file
            img = PIL.Image.open(fname)
        except FileNotFoundError:
            # URL
            img = PIL.Image.open(urllib.request.urlopen(fname))
        data = io.BytesIO()
        img.save(data, img.format)
        mime = PIL.Image.MIME[img.format]
        b64 = base64.b64encode(data.getvalue()).decode('utf-8')
        size = img.size
    return b64, mime, size


def _run_inkscape_and_replace_svg(action_str):
    '''Invoke a set of actions in a child Inkscape then replace the current
    SVG contents with those of the child Inkscape.'''
    # Acquire references to global data.
    global _simple_top, _user_globals
    svg_root = _simple_top.svg_root

    # Work within a temporary directory.
    with TemporaryDirectory(prefix='inkscape-command-') as tmpdir:
        # Write the current image to input.svg.
        svg_file = inkex.command.write_svg(svg_root, tmpdir, 'input.svg')

        # Change to svg_file's directory to support the hard-wired action,
        # "export-filename:input.svg".
        cwd = os.getcwd()
        os.chdir(os.path.dirname(svg_file))

        # Invoke another copy of Inkscape to perform the actions.
        args = ['--batch-process']
        if action_str[0].strip().islower():
            # Newer version of Inkscape as indicated by actions beginning
            # with lowercase letters.
            instance_tag = ''.join(random.choices(string.ascii_letters, k=10))
            args.append(f'--app-id-tag={instance_tag}')
        inkex.command.inkscape(svg_file,
                               *args,
                               actions=action_str)

        # Restore the previous directory.
        os.chdir(cwd)

        # Replace the current document with the modified one.
        ext = _simple_top.extension
        ext.document = inkex.load_svg(svg_file)
        ext.svg = ext.document.getroot()
        _simple_top.svg_root = ext.svg
        _simple_top.svg_attach = _simple_top.find_attach_point()
        _user_globals['svg_root'] = ext.svg


def _abend(msg):
    'Abnormally end execution with an error message.'
    raise inkex.AbortExtension(msg)


class Mpath(inkex.Use):
    'Point to a path object.'
    tag_name = 'mpath'


class SimpleTopLevel():
    "Keep track of top-level objects, both ours and inkex's."

    def __init__(self, svg_root, ext_obj):
        self.svg_root = svg_root
        self.extension = ext_obj
        self.svg_attach = self.find_attach_point()
        self.canvas = SimpleCanvas(svg_root)
        self.simple_objs = []

    def find_attach_point(self):
        '''Return a suitable point in the SVG XML tree at which to attach
        new objects.'''
        # The Inkscape GUI automatically adds a <sodipodi:namedview> element
        # with an inkscape:current-layer attribute, and this will name either
        # an actual layer or the <svg> element itself.  In this case, we return
        # the layer pointed to by inkscape:current-layer.
        svg = self.svg_root
        try:
            namedview = svg.findone('sodipodi:namedview')
            cur_layer_name = namedview.get('inkscape:current-layer')
            cur_layer = svg.xpath('//*[@id="%s"]' % cur_layer_name)[0]
            return cur_layer
        except (AttributeError, IndexError):
            pass

        # If an extension is run from the command line, the input SVG file
        # may lack a <sodipodi:namedview> element.  (This is the case for
        # /usr/share/inkscape/templates/default.svg in my installation, for
        # example.)  Or, it may contain a <sodipodi:namedview> element that
        # lacks an inkscape:current-layer attribute.  In either of these
        # cases we return the topmost layer, assuming one exists.
        try:
            return svg.xpath('//svg:g[@inkscape:groupmode="layer"]')[-1]
        except IndexError:
            pass

        # A very minimal SVG input may contain no layers at all.  In this case,
        # we return the top-level <svg> element.
        return svg

    def append_obj(self, obj, to_root=False):
        'Append a Simple Inkscape Scripting object to the document.'
        # Check for a few error conditions.
        if not isinstance(obj, SimpleObject):
            raise ValueError('Only Simple Inkscape Scripting objects '
                             'can be appended')
        if obj in self.simple_objs:
            raise ValueError('Object has already been appended')

        # Attach the underlying inkex object to the SVG attachment point if
        # to_root is False or to the SVG root if to_root is True.  Append
        # the Simple Inkscape Scripting object to the list of simple
        # objects.
        if to_root:
            self.svg_root.append(obj._inkscape_obj)
        else:
            self.svg_attach.append(obj._inkscape_obj)
        self.simple_objs.append(obj)

    def remove_obj(self, obj):
        'Remove a Simple Inkscape Scripting object from the document.'
        # Check for a few error conditions.
        if not isinstance(obj, SimpleObject):
            raise ValueError('Only Simple Inkscape Scripting objects '
                             'can be removed')
        if obj not in self.simple_objs:
            raise ValueError('Object does not appear at the top level')

        # Elide the Simple Inkscape Scripting object and dissociate the
        # underlying inkex object from its parent.
        self.simple_objs = [o for o in self.simple_objs if o is not obj]
        if obj._inkscape_obj is not None:
            obj._inkscape_obj.delete()

    def last_obj(self):
        'Return the last Simple Inkscape Scripting object added by append_obj.'
        return self.simple_objs[-1]

    def append_def(self, obj):
        '''Append either an inkex object or a Simple Inkscape Scripting object
        to the document's <defs> section.'''
        try:
            self.svg_root.defs.append(obj._inkscape_obj)
        except AttributeError:
            self.svg_root.defs.append(obj)

    def __contains__(self, obj):
        '''Return True if a given Simple Inkscape Scripting object appears at
        the document's top level.'''
        return obj in self.simple_objs

    def get_existing_guides(self):
        '''Return a list of existing Inkscape guides as Simple Inkscape
        Scripting SimpleGuide objects.'''
        guides = []
        for iobj in self.svg_root.namedview.xpath('//sodipodi:guide'):
            guides.append(SimpleGuide._from_inkex_object(iobj))
        return guides

    def replace_all_guides(self, guides):
        'Replace all guides in the document with those in the given list.'
        for iobj in self.svg_root.namedview.xpath('//sodipodi:guide'):
            iobj.getparent().remove(iobj)
        nv = self.svg_root.namedview
        for obj in guides:
            nv.add(obj.get_inkex_object())

    def get_existing_pages(self):
        '''Return a list of existing Inkscape pages as Simple Inkscape
        Scripting SimplePage objects.'''
        pages = []
        page_iobjs = [node
                      for node in self.svg_root.xpath('//inkscape:page')
                      if isinstance(node, inkex.Page)]
        for num, pg in enumerate(page_iobjs):
            name = pg.get('inkscape:label', '')
            pos = (float(pg.get('x', '0')),
                   float(pg.get('y', '0')))
            size = (float(pg.get('width', '0')),
                    float(pg.get('height', '0')))
            pages.append(SimplePage(num, name, pos, size, pg))
        return pages

    @staticmethod
    def is_top_level(iobj):
        """Return True if an inkex object's parent is one of None, a layer,
        or <svg>."""
        p = iobj.getparent()
        if p is None:
            return True
        if p.TAG == 'svg':
            return True
        if isinstance(p, inkex.Layer):
            return True
        return False

    def all_known_objects(self, from_objs=None):
        '''Return a postorder traversal of all Simple Inkscape Scripting
        objects reachable from the top-level objects.'''
        if from_objs is None:
            from_objs = self.simple_objs
        all_objs = []
        for obj in from_objs:
            if isinstance(obj, SimpleGroup):
                all_objs.extend(self.all_known_objects(obj))
            all_objs.append(obj)
        return all_objs


class SVGOutputMixin():
    '''Provide an svg method for converting an underlying inkex object to
    a string.'''

    def svg(self, xmlns=False, pretty_print=False):
        'Return our underlying inkex object as a string.'
        obj = self.get_inkex_object()
        if xmlns or pretty_print:
            # pretty_print currently implies xmlns.
            return lxml.etree.tostring(obj,
                                       encoding='unicode',
                                       pretty_print=pretty_print)
        return obj.tostring().decode('utf-8')


class GenericReprMixin():
    '''Provide a generic __repr__ method for Simple Inkscape Scripting
    classes that don't define a more customized __repr__.'''

    def __repr__(self):
        iobj = self.get_inkex_object()
        return '<%s %s %s>' % \
            (self.__class__.__name__,
             iobj.TAG,
             iobj.get_id(1))


class SimpleObject(SVGOutputMixin):
    'Encapsulate an Inkscape object and additional metadata.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, mask_obj,
                 base_style, obj_style, track=True):
        'Wrap an Inkscape object within a SimpleObject.'
        # Combine the current and default transforms.
        ts = []
        if transform is not None:
            transform = str(transform)   # Transform may be an inkex.Transform.
            if transform != '':
                ts.append(transform)
        if _default_transform[-1] is not None and _default_transform[-1] != '':
            ts.append(_default_transform[-1])
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
                clip_str = clip_path_obj._inkscape_obj.get_id(as_url=2)
            obj.set('clip-path', clip_str)

        # Optionally employ a mask.
        if mask_obj is not None:
            if isinstance(mask_obj, str):
                mask_str = mask_obj
            else:
                if not isinstance(mask_obj, SimpleMask):
                    mask_obj = mask(mask_obj)
                mask_str = mask_obj._inkscape_obj.get_id(as_url=2)
            obj.set('mask', mask_str)

        # Combine the current and default styles.
        ext_style = self._construct_style(base_style, obj_style)
        if ext_style != '':
            obj.style = ext_style

        # Store the modified Inkscape object.  If the object is new (as
        # opposed to having been wrapped with inkex_object), attach it to
        # the top-level connection point.
        self._track = track
        self._inkscape_obj = obj
        if obj.getparent() is None and self._track:
            _simple_top.append_obj(self)
            _simple_top.svg_attach.append(obj)
        self.parent = None

    def __repr__(self):
        'Return a unique description of the object as a string.'
        iobj = self.get_inkex_object()
        bbox = iobj.bounding_box()
        if bbox is None:
            # Make empty paths produce a center of (NaN, NaN) instead
            # of crashing with an AttributeError.
            bbox = inkex.BoundingBox()
        return '<%s %s (%s) %s>' % \
            (self.__class__.__name__,
             iobj.TAG,
             bbox.center,
             iobj.get_id(1))

    def __eq__(self, other):
        '''Two SimpleObjects are equal if they encapsulate the same
        inkex object.'''
        if type(self) is not type(other):
            return NotImplemented
        return self.get_inkex_object() == other.get_inkex_object()

    def __ne__(self, other):
        '''Two SimpleObjects are unequal if they do not encapsulate the
        same inkex object.'''
        if type(self) is not type(other):
            return NotImplemented
        return self.get_inkex_object() != other.get_inkex_object()

    def __hash__(self):
        'Map the SimpleObject to an integer.'
        return hash(self.get_inkex_object())

    @staticmethod
    def _construct_style(base_style, new_style):
        '''Combine a shape default style, a global default style, and an
        object-specific style and return the result as a string.'''
        # Start with the default style for the shape type.
        style = base_style.copy()

        # Update the style according to the current global default style.
        style.update(_default_style[-1])

        # Update the style based on the object-specific style.
        for k, v in new_style.items():
            k = k.replace('_', '-')
            if v is None:
                style[k] = None
            else:
                style[k] = _python_to_svg_str(v)

        # Remove all keys whose value is None.
        style = {k: v for k, v in style.items() if v is not None}

        # Concatenate the style into a string.
        return ';'.join(['%s:%s' % kv for kv in style.items()])

    def _inkscape_bbox(self):
        """Return the object's bounding box as an inkex.transforms.BoundingBox.
        This method works by writing the object to its own file and
        spawning another copy of Inkscape to compute the bounding box.  It
        can therefore be expected to be quite slow.  The code is derived
        from inkex's get_inkscape_bbox but adapted to work with any object, not
        just text, which is a limitation at the time of this writing."""
        iobj = self.get_inkex_object()
        iobj_id = iobj.get_id()  # Force ID creation.
        with TemporaryDirectory(prefix='inkscape-command-') as tmpdir:
            svg_file = inkex.command.write_svg(iobj.root, tmpdir, 'input.svg')
            out = inkex.command.inkscape(svg_file,
                                         '-X', '-Y', '-W', '-H',
                                         query_id=iobj_id)
            out = list(map(iobj.root.viewport_to_unit, out.splitlines()))
            if len(out) != 4:
                raise ValueError('Bounding box computation failed')
            return inkex.transforms.BoundingBox.new_xywh(*out)

    def _need_inkscape_bbox(self, iobj):
        'Return True if we need Inkscape to compute a bounding box.'
        for elt in iobj.iter():
            if elt.TAG in ['text', 'use', 'image']:
                # <text> requires Inkscape.  <use> can be anything so we
                # assume pessimistally that it requires Inkscape.  <image>
                # requires Inkscape if the image is not embedded or if
                # width and height are not specified.  Rather than take
                # chances we always invoke Inkscape if given an image.
                return True
        return False

    def bounding_box(self):
        "Return the object's bounding box as an inkex.BoundingBox."
        # Ask inkex to compute a bounding box.
        iobj = self._inkscape_obj
        bbox = iobj.bounding_box()

        # Bounding boxes for text, non-embedded images, or groups
        # containing either of those are inaccurate.  In such cases, try
        # using a slow but more accurate approach.
        if self._need_inkscape_bbox(iobj):
            try:
                bbox = self._inkscape_bbox()
            except AttributeError:
                # Running from Inkscape 1.0 or 1.1 instead of Inkscape 1.2+
                pass
            except inkex.command.ProgramRunError:
                # Running from an AppImage build of Inkscape
                pass
        return bbox

    def get_parent(self):
        """Return the current object's parent or None if it lies at the
        top level."""
        return self.parent

    def remove(self):
        'Remove the current object from the list of rendered objects.'
        try:
            self.parent.ungroup(self)
        except AttributeError:
            pass  # Not within a group
        global _simple_top
        if self in _simple_top:
            # Object created by Simple Inkscape Scripting
            _simple_top.remove_obj(self)
        else:
            # Existing object wrapped by Simple Inkscape Scripting (e.g.,
            # returned by all_shapes)
            self._inkscape_obj.delete()

    def unremove(self):
        'Replace a removed object, placing it at the top level.'
        global _simple_top
        iobj = self.get_inkex_object()
        if iobj.getparent() is not None:
            raise ValueError('Only removed objects can be unremoved')
        if hasattr(self, '_self_type') and self._self_type == 'layer':
            _simple_top.append_obj(self, to_root=True)
        elif self._track:
            _simple_top.append_obj(self)
        self.parent = None

    def to_def(self):
        '''Convert the object to a definition, removing it from the list of
        rendered objects.'''
        self.remove()
        global _simple_top
        _simple_top.append_def(self)
        return self

    @staticmethod
    def _path_to_curve(pe):
        '''Convert a PathElement to a list of PathCommands that are primarily
        curves.'''
        # Convert to a CubicSuperPath and from that to a list of segments.
        csp = pe.path.to_superpath()
        segs = list(csp.to_segments())
        new_segs = []

        # Postprocess all linear curves to make them more suitable for
        # conversion to B-splines.
        prev = inkex.Vector2d()
        for seg in segs:
            if isinstance(seg, inkex.paths.Move):
                first = seg.end_point(inkex.Vector2d(), prev)
                new_segs.append(seg)
            elif isinstance(seg, inkex.paths.Curve):
                # Convert [a, a, b, b] to [a, 1/3[a, b], 2/3[a, b], b].
                pt1 = prev
                pt2 = inkex.Vector2d(seg.x2, seg.y2)
                pt3 = inkex.Vector2d(seg.x3, seg.y3)
                pt4 = inkex.Vector2d(seg.x4, seg.y4)
                if pt1.is_close(pt2) and pt3.is_close(pt4):
                    pt2 = (2*pt1 + pt4)/3
                    pt3 = (pt1 + 2*pt4)/3
                new_segs.append(inkex.paths.Curve(pt2.x, pt2.y,
                                                  pt3.x, pt3.y,
                                                  pt4.x, pt4.y))
            elif isinstance(seg, inkex.paths.Line):
                # Convert the line [a, b] to the curve [a, 1/3[a, b],
                # 2/3[a, b], b].
                pt1 = prev
                pt4 = inkex.Vector2d(seg.x, seg.y)
                pt2 = (2*pt1 + pt4)/3
                pt3 = (pt1 + 2*pt4)/3
                new_segs.append(inkex.paths.Curve(pt2.x, pt2.y,
                                                  pt3.x, pt3.y,
                                                  pt4.x, pt4.y))
            elif isinstance(seg, inkex.paths.ZoneClose):
                # Draw a line back to the first point.
                pt1 = prev
                pt4 = first
                if not pt1.is_close(pt4):
                    pt2 = (2*pt1 + pt4)/3
                    pt3 = (pt1 + 2*pt4)/3
                    new_segs.append(inkex.paths.Curve(pt2.x, pt2.y,
                                                      pt3.x, pt3.y,
                                                      pt4.x, pt4.y))
                new_segs.append(seg)
            else:
                _abend(_('internal error: unexpected path command '
                         'in _path_to_curve'))
            prev = seg.end_point(first, prev)
        return new_segs

    def to_path(self, all_curves=False):
        '''Convert the object to a path, removing it from the list of
        rendered objects.'''
        # Get a path version of the underlying object and use this to
        # construct a path SimpleObject.
        obj = self._inkscape_obj
        try:
            p = path(obj.get_path())
        except TypeError:
            _abend(_('Failed to convert object to a path'))
        p_obj = p._inkscape_obj

        # If all_curves was specified, replace the path with one created
        # from the current path's CubicSuperPath segments.
        if all_curves:
            pes = self._path_to_curve(p_obj)
            p.remove()
            p = path(pes)
            p_obj = p._inkscape_obj

        # Copy over the original object's style, transform, and parent.
        p_obj.set('style', obj.get('style'))
        xform = obj.get('transform')
        if xform is not None:
            p.transform = xform
        if self.parent is not None:
            self.parent.append(p)

        # Remove the old object and return the new object.
        self.remove()
        return p

    def style(self, **style):
        """Augment the object's current style and return the new style as a
        Python dict."""
        # Merge the old and new styles and apply these to the object.
        obj = self._inkscape_obj
        obj.style = self._construct_style(dict(obj.style.items()), style)

        # Convert the style to a dictionary with Python-compatible keys.
        new_style = {}
        for k, v in obj.style.items():
            k = k.replace('-', '_')
            v = _svg_str_to_python(v)
            new_style[k] = v
        return new_style

    def _inverse_transform(self):
        'Return an inkex.Transform that undoes the current transformation.'
        xform = self._transform
        m = numpy.array(list(xform.matrix) + [[0, 0, 1]])
        m_inv = numpy.linalg.inv(m)
        un_xform = inkex.Transform()
        un_xform.add_matrix(m_inv[0][0], m_inv[1][0],
                            m_inv[0][1], m_inv[1][1],
                            m_inv[0][2], m_inv[1][2])
        return un_xform

    def _find_transform_point(self, anchor):
        'Return the center point around which to apply a transformation.'
        if isinstance(anchor, str):
            obj = self._inkscape_obj
            un_xform = self._inverse_transform()
            bbox = obj.bounding_box(un_xform)
            if bbox is None:
                # Special case first encountered in Inkscape 1.2-dev when
                # an empty layer is selected.
                return inkex.Vector2d(0, 0)
            if anchor in ['c', 'center']:
                anchor = bbox.center
            elif anchor in ['ul', 'nw']:
                anchor = inkex.Vector2d(bbox.left, bbox.top)
            elif anchor in ['ur', 'ne']:
                anchor = inkex.Vector2d(bbox.right, bbox.top)
            elif anchor in ['ll', 'sw']:
                anchor = inkex.Vector2d(bbox.left, bbox.bottom)
            elif anchor in ['lr', 'se']:
                anchor = inkex.Vector2d(bbox.right, bbox.bottom)
            elif anchor == 'n':
                anchor = inkex.Vector2d(bbox.center_x, bbox.top)
            elif anchor == 's':
                anchor = inkex.Vector2d(bbox.center_x, bbox.bottom)
            elif anchor == 'e':
                anchor = inkex.Vector2d(bbox.right, bbox.center_y)
            elif anchor == 'w':
                anchor = inkex.Vector2d(bbox.left, bbox.center_y)
            else:
                _abend(_('Unexpected transform argument %s') % repr(anchor))
        else:
            anchor = inkex.Vector2d(anchor)
        return anchor

    def _apply_transform(self):
        "Apply the SimpleObject's transform to the underlying SVG object."
        self._inkscape_obj.set('transform', self._transform)

    def _multiply_transform(self, tr, first):
        '''Multiply an arbitrary transformation by self._transform (or vice
        versa, depending on first) then apply the transform to the underlying
        SVG object.  This method maintains code compatibility with both
        Inkscape 1.1 and Inkscape 1.2+.'''
        try:
            # Inkscape 1.2+
            if first:
                self._transform = self._transform @ tr
            else:
                self._transform = tr @ self._transform
        except TypeError:
            # Inkscape 1.1
            if first:
                self._transform = self._transform * tr
            else:
                self._transform = tr * self._transform
        self._apply_transform()

    def translate(self, dist, first=False):
        'Apply a translation transformation.'
        tr = inkex.Transform()
        tr.add_translate(dist[0], dist[1])
        self._multiply_transform(tr, first)
        return self

    def rotate(self, angle, anchor='center', first=False):
        'Apply a rotation transformation, optionally around a given point.'
        tr = inkex.Transform()
        anchor = self._find_transform_point(anchor)
        tr.add_rotate(angle, anchor.x, anchor.y)
        self._multiply_transform(tr, first)
        return self

    def scale(self, factor, anchor='center', first=False):
        'Apply a scaling transformation.'
        try:
            sx, sy = factor
        except (TypeError, ValueError):
            sx, sy = factor, factor
        anchor = inkex.Vector2d(self._find_transform_point(anchor))
        tr = inkex.Transform()
        tr.add_translate(anchor)
        tr.add_scale(sx, sy)
        tr.add_translate(-anchor)
        self._multiply_transform(tr, first)
        return self

    def skew(self, angles, anchor='center', first=False):
        'Apply a skew transformation.'
        anchor = inkex.Vector2d(self._find_transform_point(anchor))
        tr = inkex.Transform()
        tr.add_translate(anchor)
        tr.add_skewx(angles[0])
        tr.add_skewy(angles[1])
        tr.add_translate(-anchor)
        self._multiply_transform(tr, first)
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

    @property
    def tag(self):
        'Return the element type of our underlying object.'
        # Strip off the namespace prefix (e.g.,
        # "{http://www.w3.org/2000/svg}circle" --> "circle").
        return self._inkscape_obj.TAG

    def svg_get(self, attr, as_str=False):
        'Return the value of an SVG attribute.'
        v = self._inkscape_obj.get(attr)
        if v is None or as_str:
            # None and as_str=True return strings.
            return v
        if attr == 'transform':
            # Return the transform as an inkex.Transform.
            return inkex.Transform(v)
        if attr == 'style':
            # Return the style as a dictionary.
            return self.style()
        # Everything else is returned as a Python data type.
        return _svg_str_to_python(v)

    def svg_set(self, attr, val):
        'Set the value of an SVG attribute.'
        obj = self._inkscape_obj
        if attr == 'transform':
            # "transform" is a special case because we maintain a shadow
            # copy of the current transform within the SimpleObject.
            self.transform = val
        elif val is None:
            # None removes an attribute.
            obj.attrib.pop(attr, None)   # "None" suppresses a KeyError
        elif attr == 'style':
            # "style" accepts a variety of data types.
            if isinstance(val, dict):
                # Dictionary
                self.style(**val)
            else:
                # inkex.Style or other object convertible to str
                obj.set(attr, str(val))
        else:
            # All other attribute values are applied directly to the
            # underlying inkex object.
            obj.set(attr, _python_to_svg_str(val))

    @staticmethod
    def _diff_transforms(objs):
        'Return a list of transformations to animate.'
        # Determine if any object has a different transformation from any
        # other.
        xforms = [o.get('transform') for o in objs]
        if all(x is None for x in xforms):
            return []  # No transform on any object: nothing to animate.
        for i, x in enumerate(xforms):
            if x is None:
                xforms[i] = inkex.Transform()
            else:
                xforms[i] = inkex.Transform(x)
        if len({str(x) for x in xforms}) == 1:
            return []  # All transforms are identical: nothing to animate.
        hexads = [list(x.to_hexad()) for x in xforms]

        # Find changes in translation.
        xlate_values = []
        for h in hexads:
            xlate_values.append('%.5g %.5g' % (h[4], h[5]))

        # Find changes in scale.
        scale_values = []
        for i, h in enumerate(hexads):
            sx = math.sqrt(h[0]**2 + h[1]**2)
            sy = math.sqrt(h[2]**2 + h[3]**2)
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
            angles = [math.acos(h[0]), math.asin(h[1]),
                      math.asin(-h[2]), math.acos(h[3])]
            if abs(angles[0] - angles[3]) > 0.00001 or \
               abs(angles[1] - angles[2]) > 0.00001:
                return []   # Transform is too complicated for us to handle.

            # Determine the angle in the correct quadrant.
            if h[0] >= 0 and h[1] >= 0:
                ang = angles[0]
            elif h[0] < 0 and h[1] >= 0:
                ang = angles[0]
            elif h[0] < 0 and h[1] < 0:
                ang = math.pi - angles[1]
            else:
                ang = 2*math.pi + angles[1]
            rot_values.append(ang)

        # Convert changes in rotation from radians to degrees and floats to
        # strings.
        rot_values = ['%.5g' % (r*180/math.pi) for r in rot_values]

        # Return a list of transformations to apply.
        xform_list = []
        if len(set(scale_values)) > 1:
            xform_list.append(('scale', scale_values))
        if len(set(rot_values)) > 1:
            xform_list.append(('rotate', rot_values))
        if len(set(xlate_values)) > 1:
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
                target = group([target])
            anim = AnimateTransform()
            anim.set('attributeName', 'transform')
            anim.set('type', xf[0])
            anim.set('values', '; '.join(xf[1]))
            if duration is not None:
                anim.set('dur', _python_to_svg_str(duration))
            if begin_time is not None:
                anim.set('begin', _python_to_svg_str(begin_time))
            if key_times is not None:
                if len(key_times) != len(objs):
                    _abend(_('Expected %d key times but saw %d' %
                             (len(objs), len(key_times))))
                anim.set('keyTimes',
                         '; '.join([_python_to_svg_str(kt)
                                    for kt in key_times]))
            if repeat_count is not None:
                anim.set('repeatCount', _python_to_svg_str(repeat_count))
            if repeat_time is not None:
                anim.set('repeatDur', _python_to_svg_str(repeat_time))
            if keep:
                anim.set('fill', 'freeze')
            target._inkscape_obj.append(anim)

    @staticmethod
    def _diff_attributes(objs):
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
            if len(set(vs)) > 1:
                attr2vals[a] = vs

        # Handle styles specially.
        if objs[0].get('style') is not None:
            style = inkex.Style(objs[0].get('style'))
            for a in style:
                vs = []
                for o in objs:
                    obj_style = inkex.Style(o.get('style'))
                    vs.append(obj_style.get(a))
                vs = [v for v in vs if v is not None]
                if len(set(vs)) > 1:
                    attr2vals[a] = vs
        return attr2vals

    @staticmethod
    def _key_times_string(key_times, num_objs, interpolation):
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

    def animate(self, objs=None, duration=None,
                begin_time=None, key_times=None,
                repeat_count=None, repeat_time=None, keep=True,
                interpolation=None, path=None, path_rotate=None,
                at_end=False, attr_filter=None):
        "Animate the object through each of the given objects' appearance."
        # Prepare the list of objects.
        objs = objs or []
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
            anim = Animate()
            anim.set('attributeName', a)
            anim.set('values', '; '.join(vs))
            if duration is not None:
                anim.set('dur', _python_to_svg_str(duration))
            if begin_time is not None:
                anim.set('begin', _python_to_svg_str(begin_time))
            if key_times is not None:
                kt_str = self._key_times_string(key_times,
                                                len(all_iobjs),
                                                interpolation)
                anim.set('keyTimes', kt_str)
            if repeat_count is not None:
                anim.set('repeatCount', _python_to_svg_str(repeat_count))
            if repeat_time is not None:
                anim.set('repeatDur', _python_to_svg_str(repeat_time))
            if keep:
                anim.set('fill', 'freeze')
            if interpolation is not None:
                anim.set('calcMode', _python_to_svg_str(interpolation))
            self._inkscape_obj.append(anim)

        # Add an <animateMotion> element if a path was supplied.
        if path is not None:
            # Create an <animateMotion> element.
            anim_mo = AnimateMotion()
            if duration is not None:
                anim_mo.set('dur', _python_to_svg_str(duration))
            if begin_time is not None:
                anim_mo.set('begin', _python_to_svg_str(begin_time))
            if key_times is not None:
                kt_str = self._key_times_string(key_times,
                                                len(all_iobjs),
                                                interpolation)
                anim.set('keyTimes', kt_str)
            if repeat_count is not None:
                anim_mo.set('repeatCount', _python_to_svg_str(repeat_count))
            if repeat_time is not None:
                anim_mo.set('repeatDur', _python_to_svg_str(repeat_time))
            if keep:
                anim_mo.set('fill', 'freeze')
            if interpolation is not None:
                anim_mo.set('calcMode', _python_to_svg_str(interpolation))
            if path_rotate is not None:
                anim_mo.set('rotate', _python_to_svg_str(path_rotate))

            # Insert an <mpath> child under <animateMotion> that links to
            # the given path.
            mpath = Mpath()
            mpath.href = path._inkscape_obj.get_id()
            anim_mo.append(mpath)

            # Add the <animateMotion> to the target object.
            self._inkscape_obj.append(anim_mo)

        # Handle animated transforms specially because only one can apply
        # to a given object.  We therefore add levels of grouping, each
        # with one <animateTransform> applied to it, as necessary.
        self._animate_transforms(all_iobjs, duration,
                                 begin_time, key_times,
                                 repeat_count, repeat_time,
                                 keep, attr_filter)

        # Remove all given objects from the top-level set of objects.
        for o in objs:
            if o is not self:
                o.remove()

    def get_inkex_object(self):
        "Return the SimpleObject's underlying inkex object."
        return self._inkscape_obj

    def z_order(self, target, n=None):
        'Raise or lower the SimpleObject in the stacking order.'
        # These operations are performed entirely at the inkex level with
        # no reecord at the Simple Inkscape Scripting level.  We therefore
        # start by acquiring our inkex object and its parent.
        obj = self._inkscape_obj
        p_obj = obj.getparent()

        # Handle the main raising and lowering operations.
        if target == 'top':
            # Raise to top.
            p_obj.append(obj)
            return
        if target == 'bottom':
            # Lower to bottom.
            p_obj.insert(0, obj)
            return
        if target == 'raise':
            # Raise by n objects.
            for i in range(n or 1):
                next_obj = obj.getnext()
                if next_obj is not None:
                    next_obj.addnext(obj)
            return
        if target == 'lower':
            # Lower by n objects.
            for i in range(n or 1):
                prev_obj = obj.getprevious()
                if prev_obj is not None:
                    prev_obj.addprevious(obj)
            return

        # Handle moving an object to a specific stack position.
        if target == 'to':
            # Move to a specific position by inserting right *before* the
            # next position.
            if n is None:
                _abend(_("z_order('to') requires a second argument"))
            if n >= 0:
                try:
                    # Add before the next element.
                    p_obj[n + 1].addprevious(obj)
                except IndexError:
                    # No next element: raise to top.
                    p_obj.append(obj)
            else:
                n += len(p_obj)
                if n < 1:
                    # No previous element: lower to bottom.
                    p_obj.insert(0, obj)
                else:
                    # Add after the previous element.
                    p_obj[n].addnext(obj)
            return

        # Complain about any other input.
        _abend(_('Unexpected z_order argument %s' % repr(target)))


class SimplePathObject(SimpleObject):
    '''A SimplePathObject is a SimpleObject to which LPEs and other path
    effects can be applied.'''

    def apply_path_effect(self, lpe):
        'Apply one or more path effects to the path.'
        # Convert a scalar to a singleton list for consistent access.
        if isinstance(lpe, list):
            lpe_list = lpe
        else:
            lpe_list = [lpe]

        # Rename the d attribute to inkscape:original-d to notify Inkscape
        # to compute the modified d.
        obj = self._inkscape_obj
        d = obj.get('d')
        if d is not None:
            obj.set('inkscape:original-d', d)
            obj.set('d', None)

        # Apply each LPE in turn.
        for one_lpe in lpe_list:
            # If this is our first LPE, apply it.  Otherwise, append it to the
            # previous LPE.
            pe_list = obj.get('inkscape:path-effect')
            if pe_list is None:
                obj.set('inkscape:path-effect', str(one_lpe))
            else:
                obj.set('inkscape:path-effect', '%s;%s' %
                        (pe_list, str(one_lpe)))

    def reverse(self):
        'Reverse the path direction.'
        obj = self._inkscape_obj
        obj.path = obj.path.to_absolute().reverse()
        return self

    def append(self, other):
        'Append another path onto ours, deleting the other path.'
        # Convert the input to a list if it's not already one.
        if hasattr(other, '__len__'):
            others = other
        else:
            others = [other]

        # Process in turn each input path.
        for p in others:
            if not isinstance(p, SimplePathObject):
                _abend(_('Only paths can be appended to other paths'))
            path1 = self._inkscape_obj.path
            path2 = p._inkscape_obj.path
            self._inkscape_obj.path = path1 + path2
            p.remove()
        return self

    def translate_path(self, dist):
        "Translate a path's control points."
        iobj = self._inkscape_obj
        iobj.set('d', iobj.path.translate(dist[0], dist[1]))
        return self

    def rotate_path(self, angle, anchor='center'):
        "Rotate a path's control points, optionally around a given point."
        anchor = self._find_transform_point(anchor)
        iobj = self._inkscape_obj
        iobj.set('d', iobj.path.rotate(angle, anchor))
        return self

    def scale_path(self, factor, anchor='center'):
        "Scale a path's control points, optionally around a given point."
        try:
            sx, sy = factor
        except (TypeError, ValueError):
            sx, sy = factor, factor
        anchor = inkex.Vector2d(self._find_transform_point(anchor))
        iobj = self._inkscape_obj
        iobj.set('d', iobj.path.scale(sx, sy, anchor))
        return self

    def skew_path(self, angles, anchor='center'):
        "Skew a path's control points, optionally around a given point."
        anchor = inkex.Vector2d(self._find_transform_point(anchor))
        tr = inkex.Transform()
        tr.add_translate(anchor)
        tr.add_skewx(angles[0])
        tr.add_skewy(angles[1])
        tr.add_translate(-anchor)
        iobj = self._inkscape_obj
        iobj.set('d', iobj.path.transform(tr))
        return self

    def _do_path_op(self, op, other):
        '''Move the other path object into our group, raise it to the top,
        destructively apply a path operation, and return the new path.'''
        # Complain if the other object is not a path.
        if not isinstance(other, SimplePathObject):
            _abend(_('path operations can be applied only to path objects'))

        # Move the other path into our group (if any).
        parent2 = other.get_parent()
        if parent2 is not None:
            parent2.ungroup(other)
        parent1 = self.get_parent()
        if parent1 is not None:
            parent1.append(other)

        # Raise the other path above ours so the operation behaves
        # consistently and as expected.
        other.z_order('top')

        # Apply the named path operation.
        new_objs = apply_path_operation(op, [self, other])
        return new_objs

    def __add__(self, other):
        'Destructively apply a path-union operation.'
        return self._do_path_op('union', other)[0]

    def __sub__(self, other):
        'Destructively apply a path-difference operation.'
        return self._do_path_op('difference', other)[0]

    def __mul__(self, other):
        'Destructively apply a path-intersection operation.'
        return self._do_path_op('intersection', other)[0]

    def __xor__(self, other):
        'Destructively apply a path-exclusion operation.'
        return self._do_path_op('exclusion', other)[0]

    def __truediv__(self, other):
        'Destructively apply a path-division operation.'
        return self._do_path_op('division', other)

    def __floordiv__(self, other):
        'Destructively apply a path-cut operation.'
        return self._do_path_op('cut', other)


class SimpleTextObject(SimpleObject):
    '''A SimpleTextObject is a SimpleObject to which additional text can
    be added.'''

    def add_text(self, msg, base=None, **style):
        '''Append text, possibly at a non-adjacent position and possibly
        with a different style.'''
        tspan = inkex.Tspan()
        tspan.text = msg
        tspan.style = self._construct_style({}, style)
        if base is not None:
            tspan.set('x', _python_to_svg_str(base[0]))
            tspan.set('y', _python_to_svg_str(base[1]))
        self._inkscape_obj.append(tspan)
        return self

    def to_path(self, all_curves=False):
        '''Convert the text to a path, removing it from the list of
        rendered objects.'''
        # Store the text's style and transform.
        orig_style = self.svg_get('style')
        orig_xform = self.svg_get('transform')

        # Spawn a child Inkscape to convert the text to a list of paths.
        path_objs = apply_action('object-to-path', self)
        paths = []
        for p in path_objs:
            if isinstance(p, SimplePathObject):
                paths.append(p)
            elif isinstance(p, SimpleGroup):
                p.ungroup()

        # Spawn another child Inkscape to merge all paths into one.
        # Caveat: This operation will fail silently on Inkscape versions
        # earlier than 1.2.
        union = apply_path_operation('union', paths)[0]

        # Convert the path elements to curves if requested.
        if all_curves:
            union.svg_set('d', self._path_to_curve(union._inkscape_obj))

        # Restore the saved style and transform and return the new path.
        union.svg_set('style', orig_style)
        union.svg_set('transform', orig_xform)
        return union


class SimpleMarker(SimpleObject):
    'Represent a path marker, which wraps an arbitrary object.'

    def __init__(self, obj, **style):
        super().__init__(obj, transform=None, conn_avoid=False,
                         clip_path_obj=None, mask_obj=None, base_style={},
                         obj_style=style, track=True)


class SimpleGroup(SimpleObject, collections.abc.MutableSequence):
    'Represent a group of objects.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, mask_obj,
                 base_style, obj_style, track=True):
        super().__init__(obj, transform, conn_avoid, clip_path_obj, mask_obj,
                         base_style, obj_style, track)
        self._children = []
        self._self_type = 'group'

    def __len__(self):
        return len(self._children)

    def __getitem__(self, idx):
        return self._children[idx]

    def __delitem__(self, idx):
        self._children[idx].remove()
        del self._children[idx]

    def __setitem__(self, idx, obj):
        self._prepare_object(obj)
        old_obj = self._children[idx]
        self._children[idx] = obj
        self._inkscape_obj[idx] = obj._inkscape_obj
        old_obj.remove()

    def insert(self, idx, obj):
        self._prepare_object(obj)
        self._children.insert(idx, obj)
        self._inkscape_obj.insert(idx, obj._inkscape_obj)

    def _prepare_object(self, obj):
        'Prepare to add an object to the group.'
        # Check for various error conditions.
        what = self._self_type
        if not isinstance(obj, SimpleObject):
            _abend(_('only Simple Inkscape Scripting '
                     f'objects can be added to a {what}.'))
        if what == 'group' and isinstance(obj, SimpleLayer):
            _abend(_(f'layers cannot be added to {what}s.'))
        iobj = obj._inkscape_obj
        if obj not in _simple_top and not _simple_top.is_top_level(iobj):
            _abend(_('only objects not already in a group '
                     f'or layer can be added to a {what}.'))

        # Remove the object from the top-level set of objects.
        obj.remove()

        # Mark the object as belonging to the group.
        obj.parent = self

    def _append_or_extend(self, objs):
        '''Invoke append if given a single object or extend if given
        multiple objects.'''
        if isinstance(objs, collections.abc.Iterable):
            self.extend(objs)
        else:
            self.append(objs)

    def ungroup(self, objs=None, preserve_transform=True):
        '''Remove one or more objects from the group and add it to the
        top level.  Return the list of objects that were ungrouped.'''
        # Add each object to the top level.
        if objs is None:
            objs = self._children
        elif not isinstance(objs, collections.abc.Iterable):
            objs = [objs]   # Convert scalar to list
        global _simple_top
        for o in objs:
            if o.parent != self:
                _abend(_('Attempt to remove an object from a group to which '
                         'it does not belong.'))
            o.parent = None
            _simple_top.append_obj(o)

        # Apply the SimpleGroup's transform (if any) to each of the
        # objects to be removed from it.
        if preserve_transform:
            for o in objs:
                try:
                    # Inkscape 1.2+
                    o.transform = self.transform @ o.transform
                except TypeError:
                    # Inkscape 1.1
                    o.transform = o.transform * self.transform

        # Remove each object from the SimpleGroup.  It has already been
        # removed from the SVG group as a side effect of the call to
        # append_obj above.
        obj_set = set(objs)
        self._children = [ch for ch in self._children if ch not in obj_set]

        # If the group is empty, remove it entirely.
        if self._children == []:
            self.remove()

        # Return the set of objects that were ungrouped.
        return objs


class SimpleLayer(SimpleGroup):
    'Represent an Inkscape layer.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, mask_obj,
                 base_style, obj_style):
        super().__init__(obj, transform, conn_avoid, clip_path_obj, mask_obj,
                         base_style, obj_style, track=False)
        self._self_type = 'layer'
        global _simple_top
        _simple_top.append_obj(self, to_root=True)


class SimpleClippingPath(SimpleGroup):
    'Represent a clipping path.'

    def __init__(self, obj, clip_units):
        super().__init__(obj, transform=None, conn_avoid=False,
                         clip_path_obj=None, mask_obj=None, base_style={},
                         obj_style={}, track=False)
        self._self_type = 'clipping path'
        if clip_units is not None:
            self._inkscape_obj.set('clipPathUnits', clip_units)
        global _simple_top
        _simple_top.append_def(self)


class SimpleMask(SimpleGroup):
    'Represent an object mask.'

    def __init__(self, obj, mask_units):
        super().__init__(obj, transform=None, conn_avoid=False,
                         clip_path_obj=None, mask_obj=None, base_style={},
                         obj_style={}, track=False)
        self._self_type = 'mask'
        if mask_units is not None:
            self._inkscape_obj.set('maskUnits', mask_units)
        global _simple_top
        _simple_top.append_def(self)


class SimpleHyperlink(SimpleGroup):
    'Represent a hyperlink.'

    def __init__(self, obj, transform, conn_avoid, clip_path_obj, mask_obj,
                 base_style, obj_style):
        super().__init__(obj, transform, conn_avoid, clip_path_obj, mask_obj,
                         base_style, obj_style, track=True)
        self._self_type = 'hyperlink'


class SimpleFilter(SVGOutputMixin, GenericReprMixin):
    'Represent an SVG filter effect.'

    def __init__(self, name=None, pt1=None, pt2=None, filter_units=None,
                 primitive_units=None, auto_region=None, **style):
        self.filt = inkex.Filter()
        global _simple_top
        _simple_top.append_def(self.filt)
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
        if auto_region is True:
            self.filt.set('inkscape:auto-region', 'true')
        elif auto_region is False:
            self.filt.set('inkscape:auto-region', 'false')
        style_str = str(inkex.Style(**style))
        if style_str != '':
            self.filt.set('style', style_str)
        self._prim_tally = {}

    def get_inkex_object(self):
        "Return the SimpleFilter's underlying inkex object."
        return self.filt

    def __str__(self):
        return self.filt.get_id(as_url=2)

    class SimpleFilterPrimitive(SVGOutputMixin):
        'Represent one component of an SVG filter effect.'

        def __init__(self, simp_filt, ftype, **kw_args):
            # Assign a default name to the result.
            try:
                res_num = simp_filt._prim_tally[ftype] + 1
            except KeyError:
                res_num = 1
            simp_filt._prim_tally[ftype] = res_num
            self.simp_filt = simp_filt
            all_args = {'result': '%s%d' % (ftype[2:].lower(), res_num)}

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
                else:
                    all_args[k] = _python_to_svg_str(v)

            # Add a primitive to the inkex filter.
            self.prim = simp_filt.filt.add_primitive(ftype, **all_args)

        def get_inkex_object(self):
            "Return the SimpleFilterPrimitive's underlying inkex object."
            return self.prim

        class SimpleFilterPrimitiveOption(SVGOutputMixin):
            'Represent an option applied to an SVG filter primitive.'

            def __init__(self, simp_prim, ftype, **kw_args):
                attribs = {k.replace('_', '-'): v for k, v in kw_args.items()}
                elem = lxml.etree.SubElement(simp_prim.prim,
                                             inkex.addNS(ftype, 'svg'))
                elem.update(**attribs)
                simp_prim.prim.append(elem)
                self.prim_opt = elem

            def get_inkex_object(self):
                "Return the SimpleFilterPrimitive's underlying inkex object."
                return self.prim_opt

        def add(self, ftype, **kw_args):
            '''Add an option a child of an existing filter primitive and
            return an object representation.'''
            return self.SimpleFilterPrimitiveOption(self,
                                                    'fe' + ftype,
                                                    **kw_args)

    def add(self, ftype, **kw_args):
        'Add a primitive to a filter and return an object representation.'
        return self.SimpleFilterPrimitive(self, 'fe' + ftype, **kw_args)


class SimpleGradient(SVGOutputMixin, GenericReprMixin):
    'Virtual base class for an SVG linear or radial gradient pattern.'

    # Map Inkscape repetition names to SVG names.
    repeat_to_spread = {'none':      'pad',
                        'reflected': 'reflect',
                        'direct':    'repeat'}

    grad = None  # Keep pylint from complaining that self.grad is undefined.

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
        return self.grad.get_id(as_url=2)

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

    def get_inkex_object(self):
        "Return the SimpleGradient's underlying inkex object."
        return self.grad


class SimpleLinearGradient(SimpleGradient):
    'Represent an SVG linear gradient pattern.'

    def __init__(self, pt1=None, pt2=None, repeat=None,
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
        global _simple_top
        _simple_top.append_def(grad)
        self.grad = grad


class SimpleRadialGradient(SimpleGradient):
    'Represent an SVG radial gradient pattern.'

    def __init__(self, center=None, radius=None, focus=None, fr=None,
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
        global _simple_top
        _simple_top.append_def(grad)
        self.grad = grad


class SimplePathEffect(SVGOutputMixin, GenericReprMixin):
    'Represent an Inkscape live path effect.'

    def __init__(self, effect, **kwargs):
        smart_args = {k: _python_to_svg_str(v)
                      for k, v in kwargs.items()
                      if k != 'id'}
        pe = inkex.PathEffect(effect=effect, **smart_args)
        self._inkscape_obj = pe
        global _simple_top
        _simple_top.append_def(pe)

    def __str__(self):
        '''Return a path effect as a "#" and its ID.  This enables directly
        associating the path effect with a path.'''
        return '#%s' % self._inkscape_obj.get_id()

    def get_inkex_object(self):
        "Return the SimplePathEffect's underlying inkex object."
        return self._inkscape_obj


class SimpleGuide(SVGOutputMixin):
    'Represent an Inkscape guide.'

    def __init__(self, pos, angle, color=None, label=None, _inkex_object=None):
        'Create a guide at a given position and angle.'
        # pos is stored in user coordinates, and angle is clockwise.
        # In contrast, inkex expects pos to be relative to a
        # lower-left origin and angle to be counter-clockwise.
        global _simple_top
        if _inkex_object is None:
            self._inkscape_obj = inkex.elements.Guide()
            self._move_to_wrapper(pos, angle)
        else:
            self._inkscape_obj = _inkex_object
            self._pos = pos
            self._angle = angle
        self.color = color
        self.label = label

    def get_inkex_object(self):
        "Return the guide's underlying inkex object."
        return self._inkscape_obj

    def __repr__(self):
        'Return a unique description of the guide as a string.'
        iobj = self.get_inkex_object()
        return '<%s %s %s %s>' % \
            (self.__class__.__name__,
             iobj.TAG,
             self._pos,
             iobj.get_id(1))

    def _move_to_wrapper(self, pos, angle):
        "Wrap inkex's move_to with a coordinate transformation."
        global _simple_top
        self._pos = pos
        self._angle = angle
        try:
            # Inkscape 1.3+
            nv = _simple_top.svg_root.namedview
            self._inkscape_obj = nv.add_guide((pos[0], pos[1]), float(angle))
        except AttributeError:
            # Older Inkscapes
            pos = (pos[0], _simple_top.canvas.height - pos[1])
            self._inkscape_obj.move_to(pos[0], pos[1], 180 - angle)

    @property
    def position(self):
        "Return the guide's current position."
        return self._pos

    @position.setter
    def position(self, pos):
        "Set the guide's current position."
        self._move_to_wrapper(pos, self._angle)

    @property
    def angle(self):
        "Return the guide's current angle."
        return self._angle

    @angle.setter
    def angle(self, ang):
        "Set the guide's current angle."
        self._move_to_wrapper(self._pos, ang)

    @property
    def color(self):
        "Return the guide's current color."
        return self._color

    @color.setter
    def color(self, c):
        "Change the guide's color."
        if c is None:
            self._inkscape_obj.attrib.pop('inkscape:color', None)
        else:
            self._inkscape_obj.set('inkscape:color', str(c))
        self._color = c

    @property
    def label(self):
        "Return the guide's label."
        return self._label

    @label.setter
    def label(self, lbl):
        "Change the guide's label."
        if lbl is None:
            self._inkscape_obj.attrib.pop('inkscape:label', None)
        else:
            self._inkscape_obj.set('inkscape:label', str(lbl))
        self._label = lbl

    @classmethod
    def _from_inkex_object(self, iobj):
        '''Create a Simple Inkscape Scripting SimpleGuide from an inkex
        Guide object.'''
        # Find the guide's anchor point.
        try:
            # Inkscape 1.3+
            pos = iobj.position
        except AttributeError:
            # Inkscape 1.2 and earlier
            pt = iobj.point
            pos = (pt.x, _simple_top.canvas.height - pt.y)

        # Compute the angle at which the guide is oriented.
        try:
            # Inkscape 1.2+
            angle = 90 - math.degrees(iobj.orientation.angle)
        except AttributeError:
            # Inkscape 1.0 and 1.1
            orient = [float(s) for s in iobj.get('orientation').split(',')]
            angle = 180 - math.degrees(math.atan2(orient[0], orient[1]))
            angle = -angle

        # Return a Simple Inkscape Scripting SimpleGuide.
        return SimpleGuide(pos, angle, _inkex_object=iobj)


class SimpleCanvas():
    'Get and set the canvas size and viewbox.'

    def __init__(self, svg_root):
        self._svg = svg_root
        self._name_sizes()

    @property
    def true_width(self):
        '''Return the width of the viewport coordinate system in user
        units (px)'''
        try:
            # Inkscape 1.2+
            return self._svg.viewport_width
        except AttributeError:
            # Inkscape 1.1
            return self._svg.width

    @true_width.setter
    def true_width(self, wd):
        'Set the width of the viewport coordinate system.'
        self._svg.set('width', str(wd))

    @property
    def true_height(self):
        '''Return the height of the viewport coordinate system in user
        units (px)'''
        try:
            # Inkscape 1.2+
            return self._svg.viewport_height
        except AttributeError:
            # Inkscape 1.1
            return self._svg.height

    @true_height.setter
    def true_height(self, wd):
        'Set the height of the viewport coordinate system.'
        self._svg.set('height', str(wd))

    @property
    def width(self):
        '''Return the width of the viewbox coordinate system in user
        units (px)'''
        return self.viewbox[2]

    @width.setter
    def width(self, wd):
        '''Set the width of the viewbox coordinate system in user
        units (px)'''
        vbox = self.viewbox
        vbox[2] = float(wd)
        vbox_str = ' '.join([str(f) for f in vbox])
        self._svg.set('viewBox', vbox_str)

    @property
    def height(self):
        '''Return the height of the viewbox coordinate system in user
        units (px)'''
        return self.viewbox[3]

    @height.setter
    def height(self, wd):
        '''Set the height of the viewbox coordinate system in user
        units (px)'''
        vbox = self.viewbox
        vbox[3] = float(wd)
        vbox_str = ' '.join([str(f) for f in vbox])
        self._svg.set('viewBox', vbox_str)

    @property
    def viewbox(self):
        'Return the viewbox as a list of four floats.'
        vbox = self._svg.get_viewbox()
        if vbox == [0, 0, 0, 0]:
            vbox = [0, 0, self.true_width, self.true_height]
        return vbox

    @viewbox.setter
    def viewbox(self, vbox):
        '''Set the viewbox from a string, an inkex.transforms.BoundingBox,
        or a list of four floats.'''
        if isinstance(vbox, str):
            vbox_str = vbox
        elif isinstance(vbox, inkex.transforms.BoundingBox):
            vbox_str = '%.10g %.10g %.10g %.10g' % \
                (vbox.left, vbox.top, vbox.width, vbox.height)
        elif len(vbox) == 4:
            vbox_str = ' '.join([str(float(f)) for f in vbox])
        else:
            raise ValueError('viewbox must be set to either a string or'
                             ' a list of four floats')
        self._svg.set('viewBox', vbox_str)

    def bounding_box(self):
        'Return the viewbox as an inkex.transforms.BoundingBox'
        vbox = self.viewbox
        return inkex.transforms.BoundingBox((vbox[0], vbox[0] + vbox[2]),
                                            (vbox[1], vbox[1] + vbox[3]))

    def _name_sizes(self):
        'Construct a list of named page sizes.'
        # Start with various special cases.
        self._named_sizes = {
            'US Letter': ('8.5in', '11in'),
            'US Legal': ('8.5in', '14in'),
            'Ledger/Tabloid': ('11in', '17in'),
            'Video HD 720p': ('720px', '1280px'),
            'Video HD 1080p': ('1080px', '1920px'),
            'Video UHD 4k': ('2160px', '3840px'),
            'Video UHD 8k': ('4320px', '7680px')
        }

        # Programmatically define A0 through A9.
        wd, ht = 841, 1189
        for iso_a in range(10):
            self._named_sizes[f'A{iso_a}'] = ('%dmm' % wd, '%dmm' % ht)
            wd, ht = round(ht/2), wd

    def get_size_by_name(self, name, landscape=False):
        'Map a named size to a width and height in user units (pixels).'
        named_sizes_lc = {k.lower(): v for k, v in self._named_sizes.items()}
        try:
            twd, tht = named_sizes_lc[name.lower()]
            if landscape:
                twd, tht = tht, twd
            return (inkex.units.convert_unit(twd, 'px'),
                    inkex.units.convert_unit(tht, 'px'))
        except KeyError:
            pass
        raise ValueError('Unknown page format "%s"; must be one of {%s}' %
                         (name,
                          ', '.join(['"%s"' % k for k in self._named_sizes])))

    def resize_by_name(self, name, landscape=False):
        'Set true_width, true_height, and viewbox to a named page type.'
        named_sizes_lc = {k.lower(): v for k, v in self._named_sizes.items()}
        try:
            twd, tht = named_sizes_lc[name.lower()]
            if landscape:
                twd, tht = tht, twd
            self.true_width = twd
            self.true_height = tht
            self.viewbox = [0, 0, self.true_width, self.true_height]
            return
        except KeyError:
            pass
        raise ValueError('Unknown page format "%s"; must be one of {%s}' %
                         (name,
                          ', '.join(['"%s"' % k for k in self._named_sizes])))

    def resize_to_content(self, objs=None):
        '''Adjust true_width, true_height, and viewbox to fit the bounding
        boxes of a list of objects.'''
        # Handle a single object, a list of objects, or None.
        if objs is None:
            objs = all_shapes()
        elif not isinstance(objs, collections.abc.Iterable):
            objs = [objs]
        if len(objs) == 0:
            return

        # Compute the bounding box of all SimpleObjects provided.
        bbox = objs[0].bounding_box()
        left, top = bbox.left, bbox.top
        right, bottom = bbox.right, bbox.bottom
        for o in objs[1:]:
            bbox = o.bounding_box()
            left = min(left, bbox.left)
            top = min(top, bbox.top)
            right = max(right, bbox.right)
            bottom = max(bottom, bbox.bottom)
        bbox = inkex.BoundingBox((left, right), (top, bottom))

        # Resize the viewbox to the computed bounding box.
        prev_vbox = self.viewbox
        self.viewbox = bbox

        # Scale the viewport, retaining the original units.
        twd, tht = self._svg.get('width'), self._svg.get('height')
        twd, uwd = inkex.units.parse_unit(twd,
                                          default_unit='',
                                          default_value=prev_vbox[2])
        tht, uht = inkex.units.parse_unit(tht,
                                          default_unit='',
                                          default_value=prev_vbox[3])
        twd *= bbox.width/prev_vbox[2]
        tht *= bbox.height/prev_vbox[3]
        self.true_width = '%.10g%s' % (twd, uwd)
        self.true_height = '%.10g%s' % (tht, uht)


class SimplePage(SVGOutputMixin, GenericReprMixin):
    'Represent an Inkscape page.'

    def __init__(self, number, name=None, pos=None, size=None, iobj=None):
        # Acquire the SVG's viewbox and named view.
        global _simple_top
        vbox = _simple_top.canvas.viewbox
        nv = _simple_top.svg_root.namedview

        # Set the default position to the immediate right of the previous
        # page's position.
        if pos is None:
            try:
                # Not the first page: Set pos to align the new page to the
                # immediate right of the previous page.
                last_page = nv.get_pages()[-1]
                pos = (last_page.x + last_page.width, last_page.y)
            except IndexError:
                # First page: Set pos to align with the upper left of
                # the canvas's viewbox.
                pos = (vbox[0], vbox[1])

        # Extract the default size from the viewbox.
        if size is None:
            size = (vbox[2], vbox[3])

        # If an inkex object was provided, use that instead of creating a
        # new inkex Page.
        if iobj is None:
            # Create a new page and add it to the document.
            try:
                # Inkscape 1.2+
                page_obj = nv.new_page(str(pos[0]), str(pos[1]),
                                       str(size[0]), str(size[1]),
                                       str(name))
            except AttributeError:
                # Inkscape 1.1
                _abend(_('Page creation requires Inkscape 1.2 or later'))
        else:
            # Use the existing object.
            page_obj = iobj

        # Initialize the Simple Inkscape Scripting object.
        self._inkscape_obj = page_obj
        self.number = number
        self.name = str(name)
        self.pos = pos
        self.size = size

    def get_inkex_object(self):
        "Return the SimplePage's underlying inkex object."
        return self._inkscape_obj

    @property
    def viewbox(self):
        'Return a viewbox representing the current page.'
        return self.pos + self.size

    @property
    def width(self):
        "Return the page's width."
        return self.size[0]

    @property
    def height(self):
        "Return the page's height."
        return self.size[1]

    def bounding_box(self):
        "Return the page's bounding box as an inkex.BoundingBox."
        x, y = self.pos
        wd, ht = self.size
        return inkex.BoundingBox((x, x + wd), (y, y + ht))


class RectangularForeignObject(inkex.ForeignObject,
                               inkex.Rectangle):
    'Define a foreign object that honors bounding boxes.'
    pass


class SimpleMetadata(GenericReprMixin):
    'Provide a simple interface to document metadata.'

    def __init__(self):
        # Define the namespaces used by Inkscape metadata.  Although this
        # is a bit of a hack, use the namespaces from the <svg> element if
        # available.  The reason is that xmlns:cc is sometimes set to
        # http://creativecommons.org/ns# and sometimes to
        # http://web.resource.org/cc/.  Use of the wrong one causes
        # Inkscape not to recognize the metadata.
        global _simple_top
        svg = _simple_top.svg_root
        try:
            self.rdf = svg.nsmap['rdf']
        except KeyError:
            self.rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        try:
            self.cc = svg.nsmap['cc']
        except KeyError:
            self.cc = 'http://creativecommons.org/ns#'
        try:
            self.dc = svg.nsmap['dc']
        except KeyError:
            self.dc = 'http://purl.org/dc/elements/1.1/'

        # Construct a database of Creative Commons licenses that matches
        # Inkscape's Licenses dialog.
        #
        # CC Attribution
        cc_str = 'http://creativecommons.org/ns#'
        self._licenses = {}
        self._licenses['by'] = {
            'url': 'http://creativecommons.org/licenses/by/4.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution',
                cc_str + 'DerivativeWorks'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution'
            ]
        }
        self._licenses['CC Attribution'] = self._licenses['by']

        # CC Attribution-ShareAlike
        self._licenses['by-sa'] = {
            'url': 'http://creativecommons.org/licenses/by-sa/4.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution',
                cc_str + 'DerivativeWorks'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution',
                cc_str + 'ShareAlike'
            ]
        }
        self._licenses['CC Attribution-ShareAlike'] = self._licenses['by-sa']

        # CC Attribution-NoDerivs
        self._licenses['by-nd'] = {
            'url': 'http://creativecommons.org/licenses/by-nd/4.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution'
            ]
        }
        self._licenses['CC Attribution-NoDerivs'] = self._licenses['by-nd']

        # CC Attribution-NonCommercial
        self._licenses['by-nc'] = {
            'url': 'http://creativecommons.org/licenses/by-nc/4.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution',
                cc_str + 'DerivativeWorks'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution'
            ],
            'prohibits': [
                cc_str + 'CommercialUse'
            ]
        }
        self._licenses['CC Attribution-NonCommercial'] = \
            self._licenses['by-nc']

        # CC Attribution-NonCommercial-ShareAlike
        self._licenses['by-nc-sa'] = {
            'url': 'http://creativecommons.org/licenses/by-nc-sa/4.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution',
                cc_str + 'DerivativeWorks'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution',
                cc_str + 'ShareAlike'
            ],
            'prohibits': [
                cc_str + 'CommercialUse'
            ]
        }
        self._licenses['CC Attribution-NonCommercial-ShareAlike'] = \
            self._licenses['by-nc-sa']

        # CC Attribution-NonCommercial-NoDerivs
        self._licenses['by-nc-nd'] = {
            'url': 'http://creativecommons.org/licenses/by-nc-nd/4.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution',
            ],
            'prohibits': [
                cc_str + 'CommercialUse'
            ]
        }
        self._licenses['CC Attribution-NonCommercial-NoDerivs'] = \
            self._licenses['by-nc-nd']

        # CC0 Public Domain Dedication
        self._licenses['zero'] = {
            'url':
            'http://creativecommons.org/publicdomain/zero/1.0/',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution',
                cc_str + 'DerivativeWorks'
            ]
        }
        self._licenses['CC0 Public Domain Dedication'] = self._licenses['zero']

        # FreeArt
        self._licenses['lal'] = {
            'url': 'http://artlibre.org/licence/lal',
            'permits': [
                cc_str + 'Reproduction',
                cc_str + 'Distribution',
                cc_str + 'DerivativeWorks'
            ],
            'requires': [
                cc_str + 'Notice',
                cc_str + 'Attribution',
                cc_str + 'ShareAlike'
            ]
        }
        self._licenses['FreeArt'] = self._licenses['lal']

        # Open Font License
        ofl_str = 'http://scripts.sil.org/pub/OFL/'
        self._licenses['OFL'] = {
            'url': 'http://scripts.sil.org/OFL',
            'permits': [
                ofl_str + 'Reproduction',
                ofl_str + 'Distribution',
                ofl_str + 'DerivativeWorks',
                ofl_str + 'Embedding'
            ],
            'requires': [
                ofl_str + 'Notice',
                ofl_str + 'Attribution',
                ofl_str + 'ShareAlike',
                ofl_str + 'DerivativeRenaming',
                ofl_str + 'BundlingWhenSelling'
            ]
        }
        self._licenses['Open Font License'] = self._licenses['OFL']

    def get_inkex_object(self):
        '''Return the SimpleMetadata's underlying inkex object.
        Regrettably, this exhibits the side effect of creating a
        <metadata> tag if one does not already exist (tested with
        Inkscape 1.3.2.'''
        global _simple_top
        return _simple_top.svg_root.metadata

    def _search_hierarchy(self, *args):
        '''Search an XML hierarchy given tuples of (namespace, tag).
        <rdf:RDF> is the implicit first element of the hierarchy.  This
        method returns the final node.'''
        elt = self.get_inkex_object()
        for ns_tag in [(self.rdf, 'RDF')] + list(args):
            child = elt.find('./{%s}%s' % ns_tag)
            if child is None:
                return None
            elt = child
        return elt

    def _create_hierarchy(self, *args):
        '''Create an XML hierarchy given tuples of (namespace, tag).
        <rdf:RDF> is the implicit first element of the hierarchy.  This
        method returns the final node.'''
        elt = self.get_inkex_object()
        for ns_tag in [(self.rdf, 'RDF')] + list(args):
            child = elt.find('./{%s}%s' % ns_tag)
            if child is None:
                child = lxml.etree.SubElement(elt, '{%s}%s' % ns_tag)
            elt = child
        elt.clear()
        return elt

    def _agent_title(self, tag):
        'Provide a shortcut for <cc:Work><dc:TAG><cc:Agent><dc:title>.'
        return ((self.cc, 'Work'),
                (self.dc, tag),
                (self.cc, 'Agent'),
                (self.dc, 'title'))

    @property
    def title(self):
        "Return the document's title."
        global _simple_top

        # Read <dc:title> from the document's metadata.
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'title')).text
        except AttributeError:
            pass

        # Read <title> from the document's top level.
        return _simple_top.svg_root.get('title')

    @title.setter
    def title(self, title_str):
        '''Set the document's title both in the metadata and at the
        document's top level.'''
        global _simple_top
        svg_root = _simple_top.svg_root
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'title'))
        if title_str is None:
            elt.getparent().remove(elt)
            try:
                svg_root.remove(svg_root.title)
            except TypeError:
                pass   # No top-level <title> element
            return
        elt.text = title_str
        svg_root.title = title_str

    @property
    def raw_date(self):
        "Return the document's date as a string or None if not present."
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'date')).text
        except AttributeError:
            return None

    @raw_date.setter
    def raw_date(self, date_str):
        "Set the document's date to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'date'))
        if date_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = date_str

    @property
    def date(self):
        '''Return the document's date as a datetime.date or None if a date
        is either not present or not formatted in the recommended ISO 8601
        format.'''
        try:
            return datetime.date.fromisoformat(self.raw_date)
        except ValueError:
            return None

    @date.setter
    def date(self, date_obj):
        "Set the document's date to a given datetime.datetime."
        if date_obj is None:
            self.raw_date = None
        else:
            self.raw_date = date_obj.isoformat()

    @property
    def creator(self):
        "Return the document's creator as a string or None if not present."
        try:
            return self._search_hierarchy(*self._agent_title('creator')).text
        except AttributeError:
            return None

    @creator.setter
    def creator(self, creator_str):
        "Set the document's creator to a given string."
        elt = self._create_hierarchy(*self._agent_title('creator'))
        if creator_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = creator_str

    @property
    def rights(self):
        """Return the document's rights statement as a string or None if
        not present."""
        try:
            return self._search_hierarchy(*self._agent_title('rights')).text
        except AttributeError:
            return None

    @rights.setter
    def rights(self, rights_str):
        "Set the document's rights statement to a given string."
        elt = self._create_hierarchy(*self._agent_title('rights'))
        if rights_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = rights_str

    @property
    def publisher(self):
        """Return the document's publisher as a string or None if not
        present."""
        try:
            return self._search_hierarchy(*self._agent_title('publisher')).text
        except AttributeError:
            return None

    @publisher.setter
    def publisher(self, publisher_str):
        "Set the document's publisher to a given string."
        elt = self._create_hierarchy(*self._agent_title('publisher'))
        if publisher_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = publisher_str

    @property
    def identifier(self):
        """Return the document's identifier as a string or None if not
        present."""
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'identifier')).text
        except AttributeError:
            return None

    @identifier.setter
    def identifier(self, identifier_str):
        "Set the document's identifier to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'identifier'))
        if identifier_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = identifier_str

    @property
    def source(self):
        """Return the document's source as a string or None if not
        present."""
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'source')).text
        except AttributeError:
            return None

    @source.setter
    def source(self, source_str):
        "Set the document's source to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'source'))
        if source_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = source_str

    @property
    def relation(self):
        """Return the document's relation as a string or None if not
        present."""
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'relation')).text
        except AttributeError:
            return None

    @relation.setter
    def relation(self, relation_str):
        "Set the document's relation to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'relation'))
        if relation_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = relation_str

    @property
    def language(self):
        """Return the document's language as a string or None if not
        present."""
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'language')).text
        except AttributeError:
            return None

    @language.setter
    def language(self, language_str):
        "Set the document's language to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'language'))
        if language_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = language_str

    @property
    def keywords(self):
        """Return the document's keywords as a list of strings or None if
        not present."""
        bag = self._search_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'subject'),
                                     (self.rdf, 'Bag'))
        if bag is None:
            return None
        return [elt.text.strip()
                for elt in bag.findall('./{%s}li' % self.rdf)]

    @keywords.setter
    def keywords(self, kw_list):
        "Set the document's keywords from a list of strings."
        bag = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'subject'),
                                     (self.rdf, 'Bag'))
        if kw_list is None:
            elt = self._search_hierarchy((self.cc, 'Work'),
                                         (self.dc, 'subject'))
            elt.getparent().remove(elt)
            return
        for kw in kw_list:
            li = lxml.etree.SubElement(bag, '{%s}li' % self.rdf)
            li.text = kw.strip()

    @property
    def coverage(self):
        """Return the document's coverage as a string or None if not
        present."""
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'coverage')).text
        except AttributeError:
            return None

    @coverage.setter
    def coverage(self, coverage_str):
        "Set the document's coverage to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'coverage'))
        if coverage_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = coverage_str

    @property
    def description(self):
        """Return the document's description as a string or None if not
        present."""
        try:
            return self._search_hierarchy((self.cc, 'Work'),
                                          (self.dc, 'description')).text
        except AttributeError:
            return None

    @description.setter
    def description(self, description_str):
        "Set the document's description to a given string."
        elt = self._create_hierarchy((self.cc, 'Work'),
                                     (self.dc, 'description'))
        if description_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = description_str

    @property
    def contributors(self):
        """Return the document's contributors as a string or None if not
        present."""
        try:
            elt = self._search_hierarchy(*self._agent_title('contributor'))
            return elt.text
        except AttributeError:
            return None

    @contributors.setter
    def contributors(self, contributor_str):
        "Set the document's contributors to a given string."
        elt = self._create_hierarchy(*self._agent_title('contributor'))
        if contributor_str is None:
            elt.getparent().remove(elt)
            return
        elt.text = contributor_str

    @property
    def license(self):
        "Return the document's license as a dict."
        info = {}

        # Try to acquire a url value.
        elt = self._search_hierarchy((self.cc, 'Work'),
                                     (self.cc, 'license'))
        if elt is not None:
            info['url'] = elt.get('{%s}resource' % self.rdf)

        # Try to acquire permits, requires, and prohibits values.
        elt = self._search_hierarchy((self.cc, 'License'))
        known_tags = ['permits', 'requires', 'prohibits']
        if elt is not None:
            for child in elt:
                qname = lxml.etree.QName(child)
                tag = qname.localname
                if qname.namespace != self.cc or tag not in known_tags:
                    continue
                res = child.get('{%s}resource' % self.rdf)
                if res is None:
                    continue
                try:
                    info[tag].append(res)
                except KeyError:
                    info[tag] = [res]

        # Remove keys with None values and return the rest.
        return {k: v for k, v in info.items() if v is not None}

    def _remove_old_license(self):
        "Remove the document's existing license."
        elt = self._search_hierarchy((self.cc, 'Work'),
                                     (self.cc, 'license'))
        if elt is not None:
            elt.getparent().remove(elt)
        elt = self._search_hierarchy((self.cc, 'License'))
        if elt is not None:
            elt.getparent().remove(elt)

    @license.setter
    def license(self, info):
        "Set the document's license from information in a dict."
        # Start from a clean slate.
        self._remove_old_license()

        # Do nothing if passed None, leaving the document with no license.
        if info is None:
            return

        # If given a string, treat it as the name of a known license.
        if isinstance(info, str):
            info = self._licenses[info]

        # Process the permits, requires, and prohibits keys.
        elt = None
        for key in ['permits', 'requires', 'prohibits']:
            try:
                values = info[key]
                if elt is None:
                    elt = self._create_hierarchy((self.cc, 'License'))
                for v in values:
                    child = lxml.etree.SubElement(elt,
                                                  '{%s}%s' % (self.cc, key))
                    child.set('{%s}resource' % self.rdf, v)
            except KeyError:
                pass

        # Process the url key.
        try:
            url = info['url']
            elt = self._create_hierarchy((self.cc, 'Work'),
                                         (self.cc, 'license'))
            elt.set('{%s}resource' % self.rdf, url)
            elt = self._search_hierarchy((self.cc, 'License'))
            if elt is not None:
                elt.set('{%s}about' % self.rdf, url)
        except KeyError:
            pass


# ----------------------------------------------------------------------

# The following functions represent the Simple Inkscape Scripting API
# and are intended to be called by user code.

def style(**kwargs):
    'Modify the default style.'
    global _default_style
    for k, v in kwargs.items():
        k = k.replace('_', '-')
        if v is None:
            _default_style[-1][k] = None
        else:
            _default_style[-1][k] = _python_to_svg_str(v)


def transform(t):
    'Set the default transform.'
    global _default_transform
    _default_transform[-1] = str(t).strip()


def circle(center, radius, transform=None, conn_avoid=False, clip_path=None,
           mask=None, **style):
    'Draw a circle.'
    obj = inkex.Circle(cx=_python_to_svg_str(center[0]),
                       cy=_python_to_svg_str(center[1]),
                       r=_python_to_svg_str(radius))
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def ellipse(center, radii, transform=None, conn_avoid=False, clip_path=None,
            mask=None, **style):
    'Draw an ellipse.'
    rx, ry = _split_two_or_one(radii)
    obj = inkex.Ellipse(cx=_python_to_svg_str(center[0]),
                        cy=_python_to_svg_str(center[1]),
                        rx=_python_to_svg_str(rx),
                        ry=_python_to_svg_str(ry))
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def rect(pt1, pt2, round=None, transform=None, conn_avoid=False,
         clip_path=None, mask=None, **style):
    'Draw a rectangle.'
    # Convert pt1 and pt2 to an upper-left starting point plus a width and
    # height.
    x0 = min(pt1[0], pt2[0])
    y0 = min(pt1[1], pt2[1])
    x1 = max(pt1[0], pt2[0])
    y1 = max(pt1[1], pt2[1])
    wd = x1 - x0
    ht = y1 - y0

    # Draw the rectangle.
    obj = inkex.Rectangle(x=_python_to_svg_str(x0),
                          y=_python_to_svg_str(y0),
                          width=_python_to_svg_str(wd),
                          height=_python_to_svg_str(ht))

    # Optionally round the corners.
    if round is not None:
        try:
            rx, ry = round
        except TypeError:
            rx, ry = round, round
        obj.set('rx', _python_to_svg_str(rx))
        obj.set('ry', _python_to_svg_str(ry))
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def line(pt1, pt2, transform=None, conn_avoid=False, clip_path=None, mask=None,
         **style):
    'Draw a line.'
    obj = inkex.Line(x1=_python_to_svg_str(pt1[0]),
                     y1=_python_to_svg_str(pt1[1]),
                     x2=_python_to_svg_str(pt2[0]),
                     y2=_python_to_svg_str(pt2[1]))
    base_style = {'stroke': 'black'}  # No need for fill='none' here.
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        base_style, style)


def polyline(coords, transform=None, conn_avoid=False, clip_path=None,
             mask=None, **style):
    'Draw a polyline.'
    if len(coords) < 2:
        _abend(_('A polyline must contain at least two points.'))
    pts = ' '.join(["%s,%s" % (_python_to_svg_str(x), _python_to_svg_str(y))
                    for x, y in coords])
    obj = inkex.Polyline(points=pts)
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def polygon(coords, transform=None, conn_avoid=False, clip_path=None,
            mask=None, **style):
    'Draw a polygon.'
    if len(coords) < 3:
        _abend(_('A polygon must contain at least three points.'))
    pts = ' '.join(["%s,%s" % (_python_to_svg_str(x), _python_to_svg_str(y))
                    for x, y in coords])
    obj = inkex.Polygon(points=pts)
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def regular_polygon(sides, center, radius, angle=-math.pi/2, round=0.0,
                    random=0.0, transform=None, conn_avoid=False,
                    clip_path=None, mask=None, **style):
    'Draw a regular polygon.'
    if sides < 3:
        _abend(_('A regular polygon must contain at least three points.'))

    # Create a star object, which is also used for regular polygons.
    angles = [angle, angle + math.pi/sides]
    radii = [radius, radius/2]
    try:
        # Inkscape 1.2+
        obj = inkex.PathElement.star(center, radii, sides, round,
                                     angles, True, False)
    except TypeError:
        obj = inkex.PathElement.star(center, radii, sides, round)
        obj.set('sodipodi:arg1', angles[0])
        obj.set('sodipodi:arg2', angles[1])
        obj.set('inkscape:flatsided', 'true')   # Regular polygon, not star
        obj.set('inkscape:rounded', round)
    obj.set('inkscape:randomized', random)
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def star(sides, center, radii, angles=None, round=0.0, random=0.0,
         transform=None, conn_avoid=False, clip_path=None, mask=None, **style):
    'Draw a star.'
    if sides < 3:
        _abend(_('A star must contain at least three points.'))

    # If no angles were specified, point the star upwards.
    if angles is not None:
        pass
    elif radii[0] >= radii[1]:
        angles = (-math.pi/2, math.pi/sides - math.pi/2)
    else:
        angles = (math.pi/2, math.pi/sides + math.pi/2)

    # Create a star object.
    try:
        # Inkscape 1.2+
        obj = inkex.PathElement.star(center, radii, sides, round,
                                     angles, False, False)
    except TypeError:
        obj = inkex.PathElement.star(center, radii, sides, round)
        obj.set('sodipodi:arg1', angles[0])
        obj.set('sodipodi:arg2', angles[1])
        obj.set('inkscape:flatsided', 'false')   # Star, not regular polygon
        obj.set('inkscape:rounded', round)
    obj.set('inkscape:randomized', random)
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def arc(center, radii, angles, arc_type='arc',
        transform=None, conn_avoid=False, clip_path=None, mask=None, **style):
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
    ang1 %= 2*math.pi
    ang2 %= 2*math.pi
    x0 = rx*math.cos(ang1) + center[0]
    y0 = ry*math.sin(ang1) + center[1]
    p.append(inkex.paths.Move(x0, y0))
    delta_ang = (ang2 - ang1) % (2*math.pi)
    if delta_ang == 0.0:
        delta_ang = 2*math.pi   # Special case for full ellipses
    n_segs = int((delta_ang + math.pi/2) / (math.pi/2))
    for s in range(n_segs):
        a = ang1 + delta_ang*(s + 1)/n_segs
        x1 = rx*math.cos(a) + center[0]
        y1 = ry*math.sin(a) + center[1]
        p.append(inkex.paths.Arc(rx, ry, 0, False, True, x1, y1))
    if arc_type == 'arc':
        obj.set('sodipodi:open', 'true')
    elif arc_type == 'slice':
        p.append(inkex.paths.Line(center[0], center[1]))
        p.append(inkex.paths.ZoneClose())
    elif arc_type == 'chord':
        p.append(inkex.paths.ZoneClose())
    else:
        _abend(_('Invalid arc_type "%s"' % str(arc_type)))
    obj.path = inkex.Path(p)

    # Return a Simple Inkscape Scripting object.
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def path(elts, transform=None, conn_avoid=False, clip_path=None, mask=None,
         **style):
    'Draw an arbitrary path.'
    if isinstance(elts, str):
        elts = re.split(r'[\s,]+', elts)
    if len(elts) == 0:
        _abend(_('A path must contain at least one path element.'))
    d = ' '.join([_python_to_svg_str(e) for e in elts])
    obj = inkex.PathElement(d=d)
    return SimplePathObject(obj, transform, conn_avoid, clip_path, mask,
                            _common_shape_style, style)


def connector(obj1, obj2, ctype='polyline', curve=0,
              transform=None, conn_avoid=False, clip_path=None, mask=None,
              **style):
    'Connect two objects with a path.'
    # Create a path that links the two objects' centers.
    center1 = obj1.bounding_box().center
    center2 = obj2.bounding_box().center
    d = 'M %g,%g L %g,%g' % (center1[0], center1[1], center2[0], center2[1])
    path = inkex.PathElement(d=d)

    # Mark the path as a connector.
    path.set('inkscape:connector-type', _python_to_svg_str(ctype))
    path.set('inkscape:connector-curvature', _python_to_svg_str(curve))
    path.set('inkscape:connection-start', '#%s' % obj1._inkscape_obj.get_id())
    path.set('inkscape:connection-end', '#%s' % obj2._inkscape_obj.get_id())

    # Store the connector as its own object.
    return SimpleObject(path, transform, conn_avoid, clip_path, mask,
                        _common_shape_style, style)


def text(msg, base, path=None, transform=None, conn_avoid=False,
         clip_path=None, mask=None, **style):
    'Typeset a piece of text, optionally along a path.'
    # Create the basic text object.
    obj = inkex.TextElement(x=_python_to_svg_str(base[0]),
                            y=_python_to_svg_str(base[1]))
    obj.set('xml:space', 'preserve')
    obj.text = msg

    # Optionally place the text along a path.
    if path is not None:
        tp = obj.add(inkex.TextPath())
        tp.href = path._inkscape_obj.get_id()

    # Wrap the text object within a SimpleTextObject.
    return SimpleTextObject(obj, transform, conn_avoid, clip_path, mask,
                            {}, style)


def image(fname, ul, embed=True, transform=None, conn_avoid=False,
          clip_path=None, mask=None, **style):
    'Include an image, either embedded or linked.'
    # Always read the file, whether it's embedded or linked.  Doing so
    # provides the image size, which is needed to assign the width and
    # height attributes.
    b64, mime, size = _read_image_as_base64(fname)

    # Define an appropriate URI based on whether the data are embedded or
    # simply referenced.
    if embed:
        # Embed the named file.
        uri = 'data:%s;base64,%s' % (mime, b64)
    else:
        # Merely reference the named file.
        uri = fname

    # Create an inkex object and wrap it in a Simple Inkscape Scripting object.
    iobj = inkex.Image()
    iobj.set('x', ul[0])
    iobj.set('y', ul[1])
    iobj.set('width', str(size[0]))
    iobj.set('height', str(size[1]))
    iobj.set('xlink:href', uri)
    return SimpleObject(iobj,
                        transform, conn_avoid, clip_path, mask, {}, style)


def foreign(pt1, pt2, xml='', transform=None, conn_avoid=False,
            clip_path=None, mask=None, **style):
    'Insert a foreign XML object into the SVG file.'
    # Convert pt1 and pt2 to an upper-left starting point plus a width and
    # height.
    x0 = min(pt1[0], pt2[0])
    y0 = min(pt1[1], pt2[1])
    x1 = max(pt1[0], pt2[0])
    y1 = max(pt1[1], pt2[1])
    wd = x1 - x0
    ht = y1 - y0

    # Create the foreign object, wrap it in a SimpleObject, and return the
    # SimpleObject.
    obj = RectangularForeignObject(x=_python_to_svg_str(x0),
                                   y=_python_to_svg_str(y0),
                                   width=_python_to_svg_str(wd),
                                   height=_python_to_svg_str(ht))
    if xml.strip() != '':
        # The intention here is to append a raw (i.e., non-inkex-wrapped)
        # lxml.etree._Element to obj, which is an inkex object.  A
        # straightforward obj.append(xml_obj) fails because
        # inkex.BaseElement.append tries to access xml_obj.root, which does
        # not exist.  Hence, we bypass inkex.BaseElement's append method
        # and directly invoke the underlying lxml.etree._Element's append
        # method instead.
        lxml.etree._Element.append(obj, lxml.etree.fromstring(xml))
    return SimpleObject(obj, transform, conn_avoid, clip_path, mask,
                        {}, style)


def clone(obj, transform=None, conn_avoid=False, clip_path=None, mask=None,
          **style):
    'Return a linked clone of the object.'
    c = inkex.Use()
    i_obj = obj._inkscape_obj
    c.href = i_obj.get_id()
    old_style = dict(i_obj.style.items())
    return obj.__class__(c, transform, conn_avoid, clip_path, mask,
                         old_style, style)


def duplicate(obj, transform=None, conn_avoid=False, clip_path=None, mask=None,
              **style):
    'Return a duplicate of the object.'
    cpy = obj._inkscape_obj.copy()
    old_style = dict(cpy.style.items())
    return obj.__class__(cpy, transform, conn_avoid, clip_path, mask,
                         old_style, style)


def group(objs=None, transform=None, conn_avoid=False, clip_path=None,
          mask=None, **style):
    'Create a container for other objects.'
    objs = objs or []
    g = inkex.Group()
    g_obj = SimpleGroup(g, transform, conn_avoid, clip_path, mask, {}, style)
    g_obj._append_or_extend(objs)
    return g_obj


def layer(name, objs=None, transform=None, conn_avoid=False, clip_path=None,
          mask=None, **style):
    'Create a container for other objects.'
    objs = objs or []
    layer = inkex.Layer.new(name)
    l_obj = SimpleLayer(layer, transform, conn_avoid, clip_path, mask,
                        {}, style)
    l_obj._append_or_extend(objs)
    return l_obj


def hyperlink(objs, href, title=None, target=None, mime_type=None,
              transform=None, conn_avoid=False, clip_path=None, mask=None,
              **style):
    'Hyperlink one or more objects to a given URI.'
    anc = inkex.Anchor()
    anc.set('{http://www.w3.org/1999/xlink}href', href)  # Older SVG
    anc.set('href', href)                                # Newer SVG
    if title is not None:
        # Inkscape uses primarily the older SVG xlink:title attribute.
        anc.set('{http://www.w3.org/1999/xlink}title', title)

        # Newer SVG files should include a <title> element.
        t_obj = inkex.Title()
        t_obj.text = title
        anc.append(t_obj)
    if target is not None:
        anc.set('target', target)
    if mime_type is not None:
        anc.set('type', mime_type)
    anc_obj = SimpleHyperlink(anc, transform, conn_avoid, clip_path, mask,
                              {}, style)
    anc_obj._append_or_extend(objs)
    return anc_obj


def inkex_object(iobj, transform=None, conn_avoid=False, clip_path=None,
                 mask=None, **style):
    'Expose an arbitrary inkex-created object to Simple Inkscape Scripting.'
    try:
        # Inkscape 1.2+
        merged_xform = inkex.Transform(transform) @ iobj.transform
    except TypeError:
        # Inkscape 1.0 and 1.1
        merged_xform = inkex.Transform(transform) * iobj.transform
    base_style = dict(iobj.style)
    if isinstance(iobj, inkex.PathElement):
        return SimplePathObject(iobj, merged_xform, conn_avoid, clip_path,
                                mask, base_style, style)
    if isinstance(iobj, inkex.Layer):
        # Convert the layer and recursively convert and add all its children.
        lay = SimpleLayer(iobj, merged_xform, conn_avoid, clip_path, mask,
                          base_style, style)
        for o in [e for e in iobj if e is not iobj]:
            o.getparent().remove(o)
            io = inkex_object(o)
            lay.append(io)
        return lay
    if isinstance(iobj, inkex.Group):
        # Convert the group and recursively convert and add all its children.
        gr = SimpleGroup(iobj, merged_xform, conn_avoid, clip_path, mask,
                         base_style, style)
        for o in [e for e in iobj if e is not iobj]:
            o.getparent().remove(o)
            io = inkex_object(o)
            gr.append(io)
        return gr
    if isinstance(iobj, inkex.Marker):
        return SimpleMarker(iobj, **style)
    if isinstance(iobj, inkex.TextElement):
        return SimpleTextObject(iobj, merged_xform, conn_avoid, clip_path,
                                mask, base_style, style)
    if isinstance(iobj, inkex.ShapeElement):
        return SimpleObject(iobj, merged_xform, conn_avoid, clip_path, mask,
                            base_style, style)
    _abend(_('object %s could not be converted to a'
             ' Simple Inkscape Scripting object' % repr(iobj)))


def filter_effect(name=None, pt1=None, pt2=None, filter_units=None,
                  primitive_units=None, auto_region=None, **style):
    'Return an object representing an empty filter effect.'
    return SimpleFilter(name, pt1, pt2, filter_units, primitive_units,
                        auto_region, **style)


def linear_gradient(pt1=None, pt2=None, repeat=None, gradient_units=None,
                    template=None, transform=None, **style):
    'Return an object representing a linear gradient.'
    return SimpleLinearGradient(pt1, pt2, repeat,
                                gradient_units, template, transform,
                                **style)


def radial_gradient(center=None, radius=None, focus=None, fr=None,
                    repeat=None, gradient_units=None, template=None,
                    transform=None, **style):
    'Return an object representing a radial gradient.'
    return SimpleRadialGradient(center, radius, focus, fr,
                                repeat, gradient_units, template,
                                transform, **style)


def clip_path(obj, clip_units=None):
    'Convert an object or collection of objects to a clipping path.'
    clip = SimpleClippingPath(inkex.ClipPath(), clip_units)
    if isinstance(obj, collections.abc.Iterable):
        objs = obj
    else:
        objs = [obj]
    for o in objs:
        o._apply_transform()
    clip.extend(objs)
    return clip


def mask(obj, mask_units=None):
    'Convert an object or collection of objects to a mask.'
    m = SimpleMask(inkex.Mask(), mask_units)  # Requires Inkscape 1.2+.
    if isinstance(obj, collections.abc.Iterable):
        objs = obj
    else:
        objs = [obj]
    for o in objs:
        o._apply_transform()
    m.extend(objs)
    return m


def marker(obj, ref=None, orient='auto', marker_units=None,
           view_box=None, **style):
    'Convert an object to a marker.'
    obj.remove()
    m = inkex.Marker(obj._inkscape_obj.copy())  # Copy so we can reuse obj.
    if ref is not None:
        m.set('refX', _python_to_svg_str(ref[0]))
        m.set('refY', _python_to_svg_str(ref[1]))
    m.set('orient', _python_to_svg_str(orient))
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


def push_defaults():
    'Duplicate the top element of the default style and transform stacks.'
    global _default_style, _default_transform
    _default_style.append(dict(_default_style[-1].items()))
    _default_transform.append(_default_transform[-1])


def pop_defaults():
    'Discard the top element of the default style and transform stacks.'
    global _default_style, _default_transform
    _default_style.pop()
    _default_transform.pop()
    if len(_default_style) == 0 or len(_default_transform) == 0:
        raise IndexError('more defaults popped than pushed')


def path_effect(effect, **kwargs):
    'Return an object represent a live path effect.'
    return SimplePathEffect(effect, **kwargs)


def z_sort(objs):
    '''Sort a list of shape objects from bottommost to topmost in the
    Z ordering.'''
    global _simple_top
    svg_root = _simple_top.svg_root
    iobj_to_order = {o: i for i, o in enumerate(svg_root.iter())}
    return sorted(objs, key=lambda o: iobj_to_order[o.get_inkex_object()])


def selected_shapes():
    '''Return a list of all directly selected shapes as Simple Inkscape
    Scripting objects.  Layers do not count as shapes in this context.'''
    global _simple_top
    return [inkex_object(o)
            for o in _simple_top.svg_root.selection
            if not isinstance(o, inkex.Layer)]


def all_shapes():
    '''Return a list of all shapes in the image as Simple Inkscape
    Scripting objects.  Layers do not count as shapes in this context.'''
    # Acquire the root of the SVG tree.
    global _simple_top
    svg = _simple_top.svg_root

    # Find all ShapeElements whose parent is a layer.
    layers = {g
              for g in svg.xpath('//svg:g')
              if g.get('inkscape:groupmode') == 'layer'}
    layer_shapes = [inkex_object(obj)
                    for lay in layers
                    for obj in lay
                    if isinstance(obj, inkex.ShapeElement)]

    # Find all ShapeElements whose parent is the root.
    root_shapes = [inkex_object(obj)
                   for obj in svg
                   if isinstance(obj, inkex.ShapeElement) and
                   obj not in layers]

    # Return the combination of the two.
    return root_shapes + layer_shapes


def guide(pos, angle, color=None, label=None):
    'Create a new guide without adding it to the document.'
    return SimpleGuide(pos, angle, color, label)


def page(name=None, pos=None, size=None):
    global _simple_top
    page = SimplePage(len(_simple_top.simple_pages) + 1, name, pos, size)
    _simple_top.simple_pages.append(page)
    return page


def all_pages():
    '''Return a list of all pages in the image as Simple Inkscape
    Scripting page objects.'''
    global _simple_top
    return _simple_top.simple_pages


def objects_from_svg_file(file, keep_layers=False):
    '''Return a list of Simple Inkscape Scripting objects read from a
    file, either named or already opened.'''
    global _simple_top

    # Read the file's entire contents.
    if isinstance(file, str):
        # String
        with open(file, mode='rb') as r:
            tree = inkex.load_svg(r)
    else:
        # Open file (assumed)
        tree = inkex.load_svg(file)

    # Store all shape objects read in a set.  The keep_layers argument
    # determines if layers are included in this set.
    iobj_set = {iobj
                for iobj in tree.iter()
                if isinstance(iobj, inkex.ShapeElement) and
                (keep_layers or not isinstance(iobj, inkex.Layer))}

    # Construct a list of all shapes in the set whose parent is not also in
    # the set.  In the process of doing so, convert each shape from an
    # inkex shape to a Simple Inkscape Scripting shape.  Also, if layers
    # are excluded from the set, attach the shape to the top-level layer.
    objs = []
    for iobj in iobj_set:
        if iobj.getparent() in iobj_set:
            continue
        obj = inkex_object(iobj)
        if not keep_layers:
            _simple_top.append_obj(obj)
        objs.append(obj)
    return objs


def apply_action(action, obj=None):
    '''Apply a one or more Inkscape actions to the document.  This call
    launches a separate Inkscape process so it may be slow.  No checking is
    performed on the action to ensure it is acceptable to Inkscape.  The
    function returns a list of newly created Simple Inkscape Scripting
    objects.'''
    # Reject the trivial case up front.
    if isinstance(action, str):
        action_list = [action]
    else:
        # Assume we have an iterable.
        action_list = action
        if len(action_list) == 0:
            return set()

    # Acquire a list of IDs for any objects to select.
    if obj is None:
        id_list = []
    elif isinstance(obj, collections.abc.Iterable):
        id_list = [o.get_inkex_object().get_id() for o in obj]
    else:
        id_list = [obj.get_inkex_object().get_id()]

    # Store a map from all object IDs that appear in the original image to
    # the object represented by that ID.
    global _simple_top
    svg_root = _simple_top.svg_root
    id2iobj_before = {iobj.get_id(): iobj for iobj in svg_root.iter()}

    # Construct an Inkscape action string.  As a special case, if the first
    # character of the operation is uppercase, assume we're using an older
    # (pre-1.2) version of Inkscape.  In this case we prepend "Selection"
    # instead of "path-" and use different actions to save the file.
    action_chunks = []
    action_chunks.extend(['select-by-id:' + obj_id for obj_id in id_list])
    action_chunks.extend(action_list)
    old_inkscape = action_list[0].isupper()
    if old_inkscape:
        # Inkscape 1.0 or 1.1
        action_chunks.extend([f'Selection{op}', 'FileSave', 'FileQuit'])
    else:
        # Inkscape 1.2+
        action_chunks.extend(['export-filename:input.svg',
                              'export-overwrite',
                              'export-do',
                              'quit-immediate'])
    action_str = ';'.join(action_chunks)

    # Perform the actions within a child Inkscape.
    _run_inkscape_and_replace_svg(action_str)

    # Store a map from all object IDs that appear in the new image to the
    # object represented by that ID.
    svg_root = _simple_top.svg_root
    id2iobj_after = {iobj.get_id(): iobj for iobj in svg_root.iter()}

    # Replace IDs for all objects that persisted across the call but
    # changed object type.  This will cause them to appear as new objects.
    for new_id, new_iobj in id2iobj_after.items():
        new_tag = new_iobj.tag_name
        try:
            old_iobj = id2iobj_before[new_id]
            old_tag = old_iobj.tag_name
            if new_tag != old_tag:
                new_iobj.set_random_id(backlinks=True)
        except KeyError:
            pass
    ids_before = {iobj.get_id() for iobj in id2iobj_before.values()}
    ids_after = {iobj.get_id() for iobj in id2iobj_after.values()}

    # Update existing objects, removing them and setting their underlying
    # inkex object is None if the object has been deleted.  This code
    # assumes that all_known_objects uses a postorder traversal.
    all_objs = _simple_top.all_known_objects()
    for obj in all_objs:
        obj_id = obj.get_inkex_object().get_id()
        if obj_id not in ids_after:
            obj.remove()
            obj._inkscape_obj = None
        else:
            obj._inkscape_obj = svg_root.getElementById(obj_id)

    # Acquire a list of newly created objects, each converted to a Simple
    # Inkscape Scripting object.
    new_sis_objs = []
    new_ids = ids_after.difference(ids_before)
    for oid in new_ids:
        iobj = svg_root.getElementById(oid)
        try:
            if iobj.getparent().get_id() in new_ids:
                # If the object's parent is also new, inkex_object will
                # convert the object as part of converting its parent.
                continue
            new_sis_objs.append(inkex_object(iobj))
        except inkex.AbortExtension:
            # Object type is not recognized by Simple Inkscape Scripting.
            pass

    # Sort new_sis_objs by the underlying inkex objects' order in the SVG
    # file.
    svg_order = {iobj: num
                 for iobj, num in zip(svg_root.iter(), range(2**31))}
    new_sis_objs.sort(key=lambda k: svg_order[k.get_inkex_object()])

    # Assign a parent to each created object.
    iobj2obj = {o.get_inkex_object(): o for o in all_objs + new_sis_objs}
    for obj in new_sis_objs:
        # Identify a mismatch between the SIS object's parent and the SIS
        # object corresponding to the SIS object's inkex object's parent.
        try:
            # The object's parent is either None or is known to Simple
            # Inkscape Scripting.
            iobj_parent = iobj2obj[obj.get_inkex_object().getparent()]
            if obj.parent is not None and obj.parent != iobj_parent:
                # Move the parent to the top level then reparent it to its
                # proper parent.
                _simple_top.append_obj(obj)
                iobj_parent.append(obj)
        except KeyError:
            # The object's parent is not known to Simple Inkscape
            # Scripting.  It may be the default layer, for instance.  Do
            # nothing and hope for the best.
            pass

    # Return the list of newly created objects, including all of their
    # descendants.
    return _simple_top.all_known_objects(from_objs=new_sis_objs)


def apply_path_operation(op, paths):
    '''Apply a named path operation (technically, an action named without
    the initial "path-") to one or more objects.  This call launches a
    separate Inkscape process so it may be slow.  No checking is performed
    on the action to ensure it is acceptable to Inkscape.'''
    # Verify that all of the given paths are SimplePathObjects.
    try:
        paths = list(paths)
    except TypeError:
        paths = [paths]
    if len(paths) == 0:
        return   # No work to do
    for p in paths:
        if not isinstance(p, SimplePathObject):
            _abend(_('apply_path_operation was passed a non-path object'))

    # Convert op to an action string.
    old_inkscape = op[0].isupper()
    if old_inkscape:
        # Inkscape 1.0 or 1.1
        action_str = 'Selection' + op
    else:
        # Inkscape 1.2+
        action_str = 'path-' + op

    # Invoke the more general apply_action function to perform the bulk of
    # the work.
    new_objs = apply_action(action_str, paths)

    # Return the subset of old path objects that still exist plus the
    # subset of new objects that represent paths.
    old_paths = [obj for obj in paths if obj.get_inkex_object() is not None]
    new_paths = [obj for obj in new_objs if isinstance(obj, SimplePathObject)]
    return old_paths + new_paths


def save_file(file=None):
    'Save the current image to a file.'
    # Determine the filename if one was not provided.
    global _simple_top
    if file is None:
        ext = _simple_top.extension
        file = ext.document_path()
        if file == "":
            raise RuntimeError('No filename is associated with the'
                               ' current document')

    # Save the file.
    svg = _simple_top.svg_root
    if isinstance(file, str):
        # We were given a file name as a string.
        with open(file, 'w') as w:
            w.write(svg.tostring().decode('utf-8'))
    else:
        # We were given something other than a string.  Assume it's an
        # open file object.
        file.write(svg.tostring().decode('utf-8'))


def randcolor(range1=None, range2=None, range3=None, space='rgb'):
    'Generate a color at random from a specified color space.'
    # Define a helper function that converts a scalar to a singleton list.
    def to_list(e):
        if isinstance(e, collections.abc.Iterable) and not isinstance(e, str):
            return e
        else:
            return [e]

    # Consider each color space in sequence.
    if space == 'rgb':
        # RGB
        if range1 is None:
            range1 = range(256)
        if range2 is None:
            range2 = range1
        if range3 is None:
            range3 = range2
        color = [random.choice(to_list(range1)),
                 random.choice(to_list(range2)),
                 random.choice(to_list(range3))]
    elif space == 'named':
        # Named color
        if range1 is None:
            # Drop the final "none".
            range1 = list(inkex.colors.SVG_COLOR)[:-1]
        color = random.choice(to_list(range1))
    else:
        # Other
        raise ValueError('Unknown color space "%s"' % space)
    return inkex.colors.Color(color, space)


# ----------------------------------------------------------------------

class SimpleInkscapeScripting(inkex.EffectExtension):
    'Help the user create Inkscape objects with a simple API.'

    def __init__(self, svg=None):
        super().__init__()
        self.options.user_args = []
        self.options.encoding = ''
        self.options.py_source = None
        self.options.program = None
        self.svg = svg

    def filename_arg(self, name):
        """Existing file to read or option used in script arguments"""
        if name == '-':
            return None  # Read from standard input.
        return inkex.utils.filename_arg(name)

    def reconfigure_input_file_argument(self, pars):
        target_action = None
        for action in pars._actions:
            if 'input_file' == action.dest:
                target_action = action
                break
        target_action.container._remove_action(target_action)
        pars.add_argument('input_file', nargs='?', metavar='INPUT_FILE',
                          type=self.filename_arg,
                          help='Filename of the input file or "-" for stdin '
                               ' (default is stdin)')

    def add_arguments(self, pars):
        'Process program parameters passed in from the UI.'
        self.reconfigure_input_file_argument(pars)
        pars.add_argument('--tab', dest='tab',
                          help='The selected UI tab when OK was pressed')
        pars.add_argument('--program', type=str,
                          help='Python code to execute')
        pars.add_argument('--py-source', type=str,
                          help='Python source file to execute')
        pars.add_argument('--encoding', type=str,
                          help='Character encoding for input code')
        pars.add_argument('user_args', nargs='*', metavar='USER_ARGS',
                          help='Additional arguments to pass to Python code'
                               ' via the user_args global variable')

    def find_attach_point(self):
        '''Return a suitable point in the SVG XML tree at which to attach
        new objects.'''
        # The Inkscape GUI automatically adds a <sodipodi:namedview> element
        # with an inkscape:current-layer attribute, and this will name either
        # an actual layer or the <svg> element itself.  In this case, we return
        # the layer pointed to by inkscape:current-layer.
        try:
            namedview = self.svg.findone('sodipodi:namedview')
            cur_layer_name = namedview.get('inkscape:current-layer')
            cur_layer = self.svg.xpath('//*[@id="%s"]' % cur_layer_name)[0]
            return cur_layer
        except AttributeError:
            pass

        # If an extension is run from the command line, the input SVG file may
        # lack a <sodipodi:namedview> element.  (This is the case for
        # /usr/share/inkscape/templates/default.svg in my installation, for
        # example.)  In this case, we return the topmost layer.
        try:
            return self.svg.xpath('//svg:g[@inkscape:groupmode="layer"]')[-1]
        except IndexError:
            pass

        # A very minimal SVG input may contain no layers at all.  In this case,
        # we return the top-level <svg> element.
        return self.svg

    @property
    def script_globals(self):
        '''Return all global variables that are passed to user scripts.
        This is intended for use by extensions that want to utilize
        SimpleInkscapeScripting features.'''
        global _user_globals
        return _user_globals

    def effect(self):
        'Generate objects from user-provided Python code.'
        # Prepare global values we use internally.
        global _simple_top, _simple_pages, _user_globals
        _simple_top = SimpleTopLevel(self.svg, self)

        # The following must be executed after _simple_top has been
        # initialized because SimplePage explicitly accesses
        # _simple_top.canvas.viewbox.
        _simple_top.simple_pages = _simple_top.get_existing_pages()

        # Prepare global values we want to export.
        _user_globals = globals().copy()
        _user_globals['svg_root'] = self.svg
        _user_globals['guides'] = _simple_top.get_existing_guides()
        _user_globals['print'] = _debug_print
        _user_globals['user_args'] = self.options.user_args
        _user_globals['extension'] = self
        _user_globals['canvas'] = _simple_top.canvas
        _user_globals['metadata'] = SimpleMetadata()
        _user_globals['script_filename'] = None    # Modified below.
        try:
            # Inkscape 1.2+
            convert_unit = self.svg.viewport_to_unit
        except AttributeError:
            # Inkscape 1.0 and 1.1
            convert_unit = self.svg.unittouu
        for unit in ['mm', 'cm', 'pt', 'px']:
            _user_globals[unit] = convert_unit('1' + unit)
        _user_globals['inch'] = \
            convert_unit('1in')  # "in" is a keyword.

        # Construct a string of code to execute by combining code read
        # from a file (--py-source) and entered literally (--program).
        enc = self.options.encoding or None
        code = '''
# The following imports are provided for user convenience.
from math import *
from random import *
from inkex.paths import Arc, Curve, Horz, Line, Move, Quadratic, Smooth, \
    TepidQuadratic, Vert, ZoneClose
from inkex.paths import curve, horz, move, quadratic, smooth, \
    tepidQuadratic, vert, zoneClose
'''
        py_source = self.options.py_source
        if py_source is not None and not os.path.isdir(py_source):
            # The preceding test for isdir is explained in
            # https://gitlab.com/inkscape/inkscape/-/issues/2822
            with open(self.options.py_source, encoding=enc) as fd:
                code += fd.read()
            code += '\n'
            _user_globals['script_filename'] = os.path.abspath(py_source)
        if self.options.program is not None:
            code += self.options.program.replace(r'\n', '\n')

        # Remove an unnecessary import that may be introduced when
        # running from Visual Studio Code.
        pattern = r"^[ \t]*(import\s+(inkex|simpinkscr).*|" \
            r"(from\s+(inkex|simpinkscr)\s+import).*)[\r\n]"
        code = re.sub(pattern, "", code, flags=re.MULTILINE)

        # Launch the user's script.
        try:
            exec(code, _user_globals)
        except SystemExit:
            pass
        _simple_top.replace_all_guides(_user_globals['guides'])


def main():
    SimpleInkscapeScripting().run()


if __name__ == '__main__':
    main()
