from simple_inkscape_scripting import SimpleInkscapeScripting
from svg_to_simp_ink_script import SvgToPythonScript
from inkex.tester import ComparisonMixin, InkscapeExtensionTestMixin, TestCase
from inkex.tester.filters import CompareOrderIndependentStyle

class SimpInkScrBasicTest(ComparisonMixin, InkscapeExtensionTestMixin, TestCase):
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a few helper strings.
    animation_base = '''\
def make_rect(center, fill, edge=100):
    return rect(inkex.Vector2d(-edge/2, -edge/2) + center,
                inkex.Vector2d(edge/2, edge/2) + center,
                fill=fill)

r1 = make_rect((50, 50), '#aade87')
r2 = make_rect((width/2, height/2), '#9955ff')
r3 = make_rect((width - 50, height - 50), '#d35f5f')
'''
    blue_red = '''
blue = rect((90, 0), (170, 50), fill='#55ddff')
red = rect((0, 0), (80, 50), fill='#ff5555')
'''
    z_order = '''
boxes = []
ul = inkex.Vector2d()
for c in ['beige', 'maroon', 'mediumslateblue', 'mediumseagreen', 'tan']:
    boxes.append(rect(ul, ul + (100, 60), fill=c, opacity=0.9))
    ul += (10, 10)
'''

    # Define all of the tests to run.  Simple Inkscape Scripting is a
    # large, featureful extension so many tests are needed to achieve even
    # modest coverage of all the code paths.
    comparisons = [
        # The following tests come from the Shape Construction wiki page.
        ('--program=circle((width/2, height/2), 50)',),
        ('--program=ellipse((width/2, height/2), (75, 50))',),
        ('--program=rect((width/2 - 50, height/2 - 30), (width/2 + 50, height/2 + 30))',),
        ('--program=line((width, 0), (0, height))',),
        ('--program=polyline([(0, 300), (150, 0), (300, 300), (150, 200)])',),
        ('--program=polygon([(0, 300), (150, 0), (300, 300), (150, 200)])',),
        ('--program=regular_polygon(5, (100, 100), 80)',),
        ('--program=star(5, (100, 100), (80, 30))',),
        ("--program=arc((width/2, height/2), 100, (pi/5, 9*pi/5), 'slice', fill='yellow', stroke_width=2)",),
        ("--program=path(['M', 226, 34, 'V', 237, 'L', 32, 185, 'C', 32, 185, 45, -9, 226, 34, 'Z'])",),
        ('''--program=
path([Move(226, 34),
      Vert(237),
      Line(32, 185),
      Curve(32, 185, 45, -9, 226, 34),
      ZoneClose()])
''',),
        ('''--program=
r = rect((50, 50), (100, 100))
c = circle((200, 200), 25)
connector(r, c, ctype='orthogonal', curve=15)
''',),
        ("--program=text('Simple Inkscape Scripting', (0, height), font_size='36pt')",),
        ('''--program=
text('Hello, ', (width/2, height/2), font_size='24pt', text_anchor='middle')
more_text('Inkscape', font_weight='bold', fill='#800000')
more_text('!!!')
''',),
        ("--program=image('https://media.inkscape.org/static/images/inkscape-logo.png', (0, 0), embed=False)",),

        # The following tests come from the Path Operations wiki page.
        ('''--program=
c1 = circle((50, 50), 50, fill='#005500', fill_rule='evenodd').to_path()
c2 = circle((100, 50), 50).to_path()
c1.append(c2)
''',),
        ('''--program=
box = rect((0, 0), (200, 100), fill='#d4aa00').to_path()
hole1 = rect((25, 25), (75, 75)).to_path()
hole2 = rect((125, 25), (175, 75)).to_path()
box.append([hole1.reverse(), hole2.reverse()])
''',),

        # The following tests come from the Common Arguments wiki page.
        ('''--program=
tr = inkex.Transform()
tr.add_translate(30*pt, -12*pt)
tr.add_rotate(-15, width/2, height/2)
text('Transform', (width/2, height/2),
     transform=tr,
     font_family='URW Bookman, serif',
     font_weight='bold',
     font_size=24*pt,
     text_align='center',
     text_anchor='middle',
     fill='#003380')
''',),
        ('''--program=
r1 = rect((100, 0), (150, 50), fill='#fff6d5')
r2 = rect((200, 400), (250, 450), fill='#fff6d5')
connector(r1, r2, ctype='orthogonal', curve=100)
circle((225, 225), 25, fill='red', conn_avoid=True)
''',),
        ('''--program=
polyline([(64,128), (320,64), (384,128), (640, 64)],
         stroke='#005544',
         stroke_width=32,
         stroke_linecap='round',
         stroke_linejoin='round',
         stroke_dasharray=[32, 32, 64, 32])
''',),

        # The following tests come from the Effects wiki page.
        ('''--program=
grad = linear_gradient((0, 0), (0, 1))
for i in range(5):
    r, g, b = randint(0, 255), randint(0, 255), randint(0, 255)
    grad.add_stop(i/4.0, '#%02X%02X%02X' % (r, g, b))
ellipse((200, 150), (200, 150), fill=grad)
''',),
        ('''--program=
arrowhead = path([Move(0, 0),
                  Line(4, 2),
                  Line(0, 4),
                  Curve(0, 4, 1, 3, 1, 2),
                  Curve(1, 1, 0, 0, 0, 0),
                  ZoneClose()],
                 fill=None, stroke=None)

orange_arrowhead = marker(arrowhead, (1, 2), fill='orange')
line((20, 20), (120, 20), stroke='orange', stroke_width=4, stroke_linecap='round', marker_end=orange_arrowhead)

blue_arrowhead = marker(arrowhead, (1, 2), fill='blue')
line((120, 40), (20, 40), stroke='blue', stroke_width=4, stroke_linecap='round', marker_end=blue_arrowhead)
''',),
        ('''--program=
blur = filter_effect('Make Blurry')
blur.add('GaussianBlur', stdDeviation=10, edgeMode='duplicate')
circle((width/2, height/2), 100, fill='yellow', stroke='black',
       stroke_width=5, filter=blur)
''',),
        ('''--program=
roughen = path_effect('rough_hatches',
                      do_bend=False,
                      fat_output=False,
                      dist_rdm=[0, 1])
e = ellipse((150, 100), (150, 100), stroke='#7f2aff', stroke_width=2)
p = e.to_path()
p.apply_path_effect(roughen)
''',),

        # The following tests come from the Animation wiki page.
        ("--program=%s\nr1.animate([r2, r3], duration='3s', key_times=[0, 0.75, 1])" % animation_base,),
        ('''--program=
def make_rect(center, fill, edge=100):
    return rect(inkex.Vector2d(-edge/2, -edge/2) + center,
                inkex.Vector2d(edge/2, edge/2) + center,
                fill=fill)

r1 = make_rect((50, 50), '#aade87')
r4 = make_rect((0, 0), '#5599ff')
r4.transform = 'translate(%.5f, %.5f) rotate(200) scale(2)' % (width/2, height/2)
r1.animate(r4, duration='3s')
''',),

        # The following tests come from the Modifying Existing Objects wiki
        # page.
        ('--program=%s\nred.translate((50, 30))' % blue_red,),
        ('--program=%s\nred.rotate(30)' % blue_red,),
        ('--program=%s\nred.rotate(30, (85, 25))' % blue_red,),
        ("--program=%s\nred.rotate(30, 'll')" % blue_red,),
        ('--program=%s\nred.scale(1.5)' % blue_red,),
        ('--program=%s\nred.scale((0.75, 1.5))' % blue_red,),
        ("--program=%s\nred.scale(1.5, 'ur')" % blue_red,),
        ('--program=%s\nred.skew((10, 0))' % blue_red,),
        ("--program=%s\nred.skew((0, 10), 'lr')" % blue_red,),

        # The following tests come from the Other Features wiki page.
        ('''--program=
house = rect((32, 64), (96, 112), fill='#ff0000', stroke_width=2)
roof = polygon([(16, 64), (64, 16), (112, 64)], fill='#008000', stroke_width=2)
hyperlink([house, roof], 'https://www.pakin.org/', title='My home page')
''',),
        ("--program=%s\nboxes[0].z_order('top')" % z_order,),
        ("--program=%s\nboxes[-1].z_order('bottom')" % z_order,),
        ("--program=%s\nboxes[2].z_order('raise')" % z_order,),
        ("--program=%s\nboxes[3].z_order('lower', 2)" % z_order,),
        ("--program=%s\nboxes[1].z_order('to', 3)" % z_order,),

        # The following are additional tests intended to increase coverage.
        ('''--program=
p = path(['M', 150, 50,
          'C', 100, 50, 50, 100, 50, 192,
          'V', 300,
          'H', 250,
          'V', 192,
          'C', 250, 100, 200, 50, 150, 50,
          'Z'],
         fill='#0055d4', stroke_width=3)
p.to_path(all_curves=True)
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrModifyTest(ComparisonMixin, InkscapeExtensionTestMixin, TestCase):
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]
    compare_file = 'svg/shapes.svg'
    comparisons = [
        ('''--program=
for obj in all_shapes():
    obj.rotate(15, 'center', first=True)
''',)
    ]


class SimpInkScrOutputBasicTest(ComparisonMixin, TestCase):
    effect_class = SvgToPythonScript
    compare_file = 'svg/shapes.svg'
    comparisons = [()]
