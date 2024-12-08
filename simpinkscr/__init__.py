from math import *
from random import *
from inkex import Transform
from inkex.paths import Arc, Curve, Horz, Line, Move, Quadratic, Smooth, \
    TepidQuadratic, Vert, ZoneClose
from .simple_inkscape_scripting import all_pages, all_shapes, \
    apply_action, apply_path_operation, arc, circle, clip_path, clone, \
    connector, duplicate, ellipse, filter_effect, foreign, group, \
    guide, hyperlink, image, inkex_object, layer, linear_gradient, \
    line, main, marker, mask, objects_from_svg_file, page, \
    path_effect, path, polygon, polyline, pop_defaults, push_defaults, \
    radial_gradient, randcolor, rect, regular_polygon, save_file, \
    selected_shapes, SimpleInkscapeScripting, star, style, text, transform, \
    z_sort
