#############################################################
# Define a set of unit tests for Simple Inkscape Scripting. #
# Author: Scott Pakin <scott-ink@pakin.org>                 #
#############################################################

from simpinkscr.simple_inkscape_scripting import SimpleInkscapeScripting
from inkex.tester import ComparisonMixin, InkscapeExtensionTestMixin, TestCase
from inkex.tester.filters import CompareOrderIndependentStyle
from unittest.mock import patch
from io import StringIO
import hashlib
import re


class CustomComparisonMixin(ComparisonMixin):
    def get_compare_cmpfile(self, args, addout=None):
        """Generate an output file for the arguments given"""
        if addout is not None:
            args = list(args) + [str(addout)]
        opstr = (
            "__".join(args)
            .replace(self.tempdir, "TMP_DIR")
            .replace(self.datadir(), "DAT_DIR")
        )
        opstr = re.sub(r"[^\w-]", "__", opstr)
        if opstr:
            # Modification from ComparisonMixin: always hash.
            opstr = hashlib.md5(opstr.encode("latin1")).hexdigest()
            opstr = "__" + opstr
        return self.data_file(
            "refs", f"sis{opstr}.out", check_exists=False
        )


class SimpInkScrTestShapeConst(CustomComparisonMixin,
                               InkscapeExtensionTestMixin,
                               TestCase):
    'Test examples from the Shape Construction wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ('--program=circle((canvas.width/2, canvas.height/2), 50)',),
        ('--program=ellipse((canvas.width/2, canvas.height/2), (75, 50))',),
        ('--program=rect((canvas.width/2 - 50, canvas.height/2 - 30),'
         ' (canvas.width/2 + 50, canvas.height/2 + 30))',),
        ('--program=line((canvas.width, 0), (0, canvas.height))',),
        ('--program=polyline([(0, 300), (150, 0), (300, 300), (150, 200)])',),
        ('--program=polygon([(0, 300), (150, 0), (300, 300), (150, 200)])',),
        ('--program=regular_polygon(5, (100, 100), 80)',),
        ('--program=star(5, (100, 100), (80, 30))',),
        ("--program=arc((canvas.width/2, canvas.height/2), 100,"
         " (pi/5, 9*pi/5), 'slice', fill='yellow', stroke_width=2)",),
        ("--program=path(['M', 226, 34, 'V', 237, 'L', 32, 185,"
         " 'C', 32, 185, 45, -9, 226, 34, 'Z'])",),
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
        ("--program=text('Simple Inkscape Scripting', (0, canvas.height),"
         " font_size='36pt')",),
        ('''--program=
t = text('Hello, ', (canvas.width/2, canvas.height/2), font_size='24pt',
         text_anchor='middle')
t.add_text('Inkscape', font_weight='bold', fill='#800000')
t.add_text('!!!')
''',),
        ("--program="
         "image('https://media.inkscape.org/static/images/inkscape-logo.png',"
         " (0, 0), embed=False)",)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestPathOps(CustomComparisonMixin,
                            InkscapeExtensionTestMixin,
                            TestCase):
    'Test examples from the Path Operations wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
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
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestCommonArgs(CustomComparisonMixin,
                               InkscapeExtensionTestMixin,
                               TestCase):
    'Test examples from the Common Arguments wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ('''--program=
tr = inkex.Transform()
tr.add_translate(30*pt, -12*pt)
tr.add_rotate(-15, canvas.width/2, canvas.height/2)
text('Transform', (canvas.width/2, canvas.height/2),
     transform=tr,
     font_family='"URW Bookman", serif',
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
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestCollections(CustomComparisonMixin,
                                InkscapeExtensionTestMixin,
                                TestCase):
    'Test examples from the Object Collections wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ('''--program=
colors = ['red', 'orange', 'yellow', 'green', 'blue']
diag = []
for j in range(5):
    gr = group()
    for i in range(5):
        c = circle((i*20 + 20, j*20 + 20), 8, fill=colors[j])
        gr.append(c)
        if i == j:
            diag.append(c)

diag_gr = group()
for c in diag:
    c.get_parent().ungroup(c)
    diag_gr.append(c)
diag_gr.translate((120, 0))
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestEffects(CustomComparisonMixin,
                            InkscapeExtensionTestMixin,
                            TestCase):
    'Test examples from the Effects wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
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
line((20, 20), (120, 20), stroke='orange', stroke_width=4,
     stroke_linecap='round', marker_end=orange_arrowhead)

blue_arrowhead = marker(arrowhead, (1, 2), fill='blue')
line((120, 40), (20, 40), stroke='blue', stroke_width=4,
     stroke_linecap='round', marker_end=blue_arrowhead)
''',),
        ('''--program=
blur = filter_effect('Make Blurry')
blur.add('GaussianBlur', stdDeviation=10, edgeMode='duplicate')
circle((canvas.width/2, canvas.height/2), 100, fill='yellow', stroke='black',
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
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestAnimation(CustomComparisonMixin,
                              InkscapeExtensionTestMixin,
                              TestCase):
    'Test examples from the Animation wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a helper string.
    animation_base = '''\
def make_rect(center, fill, edge=100):
    return rect(inkex.Vector2d(-edge/2, -edge/2) + center,
                inkex.Vector2d(edge/2, edge/2) + center,
                fill=fill)

r1 = make_rect((50, 50), '#aade87')
r2 = make_rect((canvas.width/2, canvas.height/2), '#9955ff')
r3 = make_rect((canvas.width - 50, canvas.height - 50), '#d35f5f')
'''

    # Define a sequence of tests.
    comparisons = [
        ("--program=%s\nr1.animate([r2, r3], duration='3s',"
         " key_times=[0, 0.75, 1])" % animation_base,),
        ('''--program=
def make_rect(center, fill, edge=100):
    return rect(inkex.Vector2d(-edge/2, -edge/2) + center,
                inkex.Vector2d(edge/2, edge/2) + center,
                fill=fill)

r1 = make_rect((50, 50), '#aade87')
r4 = make_rect((0, 0), '#5599ff')
r4.transform = 'translate(%.5f, %.5f) rotate(200) scale(2)' % \
               (canvas.width/2, canvas.height/2)
r1.animate(r4, duration='3s')
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestModExObjs(CustomComparisonMixin,
                              InkscapeExtensionTestMixin,
                              TestCase):
    'Test examples from the Modifying Existing Objects wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a few helper strings.
    blue_red = '''
blue = rect((90, 0), (170, 50), fill='#55ddff')
red = rect((0, 0), (80, 50), fill='#ff5555')
'''
    s_path = '''
S = path([Move(57, 13),
          Vert(28),
          Quadratic(52, 25, 46, 24),
          Quadratic(41, 23, 36, 23),
          Quadratic(29, 23, 26, 25),
          Quadratic(23, 26, 23, 30),
          Quadratic(23, 33, 25, 35),
          Quadratic(27, 36, 33, 37),
          Line(40, 39),
          Quadratic(52, 41, 57, 46),
          Quadratic(62, 51, 62, 60),
          Quadratic(62, 71, 55, 77),
          Quadratic(48, 82, 34, 82),
          Quadratic(27, 82, 21, 81),
          Quadratic(14, 80, 7, 77),
          Vert(62),
          Quadratic(14, 66, 20, 68),
          Quadratic(26, 69, 32, 69),
          Quadratic(38, 69, 41, 67),
          Quadratic(44, 65, 44, 62),
          Quadratic(44, 58, 42, 57),
          Quadratic(40, 55, 34, 53),
          Line(27, 52),
          Quadratic(16, 50, 11, 45),
          Quadratic(7, 40, 7, 31),
          Quadratic(7, 21, 13, 15),
          Quadratic(20, 10, 33, 10),
          Quadratic(39, 10, 45, 11),
          Quadratic(51, 12, 57, 13),
          ZoneClose()],
         fill='#decd87', stroke_width=5)
'''
    z_order = '''
boxes = []
ul = inkex.Vector2d()
for c in ['beige', 'maroon', 'mediumslateblue', 'mediumseagreen', 'tan']:
    boxes.append(rect(ul, ul + (100, 60), fill=c, opacity=0.9))
    ul += (10, 10)
'''

    # Define a sequence of tests.
    comparisons = [
        ('--program=%s\nred.translate((50, 30))' % blue_red,),
        ('--program=%s\nred.rotate(30)' % blue_red,),
        ('--program=%s\nred.rotate(30, (85, 25))' % blue_red,),
        ("--program=%s\nred.rotate(30, 'll')" % blue_red,),
        ('--program=%s\nred.scale(1.5)' % blue_red,),
        ('--program=%s\nred.scale((0.75, 1.5))' % blue_red,),
        ("--program=%s\nred.scale(1.5, 'ur')" % blue_red,),
        ('--program=%s\nred.skew((10, 0))' % blue_red,),
        ("--program=%s\nred.skew((0, 10), 'lr')" % blue_red,),
        ("--program=%s\nred.scale(1.5, 'ul').rotate(14, 'ul')" % blue_red,),
        ("--program=%s\nS.translate_path((100, 100))" % s_path,),
        ("--program=%s\nS.rotate_path(-25)" % s_path,),
        ("--program=%s\nS.scale_path((0.75, 1.5), 'ul')" % s_path,),
        ("--program=%s\nS.skew_path((0, 30), 'ul')" % s_path,),
        ('''--program=
c = circle((75, 75), 38, fill='darkturquoise', stroke_width=2)
rect((0, 0), (75, 75), fill='aquamarine', stroke_width=2)
c.remove()
c.unremove()
''',),
        ("--program=%s\nboxes[0].z_order('top')" % z_order,),
        ("--program=%s\nboxes[-1].z_order('bottom')" % z_order,),
        ("--program=%s\nboxes[2].z_order('raise')" % z_order,),
        ("--program=%s\nboxes[3].z_order('lower', 2)" % z_order,),
        ("--program=%s\nboxes[1].z_order('to', 3)" % z_order,),
        (f'''--program=
{z_order}
for obj in z_sort(boxes):
    obj.z_order('bottom')
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestOtherFeatures(CustomComparisonMixin,
                                  InkscapeExtensionTestMixin,
                                  TestCase):
    'Test examples from the Other Features wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ('''--program=
house = rect((32, 64), (96, 112), fill='#ff0000', stroke_width=2)
roof = polygon([(16, 64), (64, 16), (112, 64)], fill='#008000', stroke_width=2)
hyperlink([house, roof], 'https://www.pakin.org/', title='My home page')
''',),
        ('''--program=
g1 = guide((0, 0), 10)
g2 = guide((canvas.width, canvas.height), 10, color='#00ff00')
guides.extend([g1, g2])
''',),
        ('''--program=
r = rect((100, 100), (200, 200), stroke_width=16, stroke='#000080', fill='#add8e6')
new_objs = apply_action('object-stroke-to-path', r)
for obj in new_objs:
    try:
        if obj.style()['fill'] == '#000080':
            obj.translate_path((50, 50))
    except KeyError:
        pass
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestDocLayout(CustomComparisonMixin,
                              InkscapeExtensionTestMixin,
                              TestCase):
    'Test examples from the Document Layout wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ('''--program=
r1 = rect((100, 100), (200, 200), fill='firebrick', stroke_width='6pt')
r2 = rect((300, 150), (400, 250), fill='gold', stroke_width='6pt')
r3 = rect((200, 300), (300, 400), fill='royalblue', stroke_width='6pt')
canvas.resize_to_content([r1, r2, r3])
''',),
        ('''--program=
import string
push_defaults()
canvas.resize_by_name('A6')
style(font_family='"DejaVu Serif", serif', font_weight='bold',
      font_size='200pt', text_anchor='middle', fill='#330080')
for y in range(2):
    for x in range(2):
        i = y*2 + x
        pg = page(i + 1, (x*canvas.width, y*canvas.height))
        bbox = pg.bounding_box()
        text(string.ascii_uppercase[i], (bbox.center_x, bbox.center_y + 72*pt))
pop_defaults()
''',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestAdvanced(CustomComparisonMixin,
                             InkscapeExtensionTestMixin,
                             TestCase):
    'Test examples from the Advanced Usage wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ("""--program=
rect((10, 10), (390, 210), round=25, fill='#e7e8e3', stroke_width='2px')
foreign((20, 20), (380, 200), '''\
<div xmlns="http://www.w3.org/1999/xhtml">
  <h1>Test of foreign XML</h1>

  <table border="1px">
    <tbody>
      <tr><td>Did</td> <td>this</td> <td>work?</td></tr>
      <tr><td>Yes,</td> <td>it</td> <td>did!</td></tr>
      <tr><td>Hurrah!</td> <td>Hurrah!</td> <td>Hooray!</td></tr>
    </tbody>
  </table>
</div>
''')
""",)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestMetadata(CustomComparisonMixin,
                             InkscapeExtensionTestMixin,
                             TestCase):
    'Test examples from the Metadata wiki page.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
        ("""--program=
import datetime

now = datetime.datetime.now()
metadata.title = 'This, Too, is Not a Pipe'
metadata.date = datetime.datetime(2024, 1, 9, 22, 2)
metadata.creator = 'John Doe'
metadata.rights = 'Copyright (C) 2024 John Doe'
metadata.publisher = 'Awesome Artwork, Inc.'
metadata.identifier = '10.5555/12345678'
metadata.source = 'https://collections.lacma.org/node/239578'
metadata.relation = 'isVersionOf "La Trahison des Images"'
metadata.language = 'fr.BE'
metadata.keywords = [
    'tobacco pipe',
    'painting',
    'cursive writing'
]
metadata.coverage = 'Lessines, Belgium'
metadata.description = 'Painting of a tobacco pipe on a solid' \\
    ' background with the French phrase,' \\
    ' "Ce n\\'est pas non plus un tuyau" handwritten beneath it'
metadata.contributors = 'Fred Nerk'
metadata.license = 'CC Attribution-ShareAlike'
""",)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'


class SimpInkScrTestAdditional(CustomComparisonMixin,
                               InkscapeExtensionTestMixin,
                               TestCase):
    'Test additional snippets of code to increase coverage.'
    # Indicate how testing should be performed.
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]

    # Define a sequence of tests.
    comparisons = [
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


class SimpInkScrModifyTest(CustomComparisonMixin,
                           InkscapeExtensionTestMixin,
                           TestCase):
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]
    compare_file = 'svg/shapes.svg'
    comparisons = [
        ('''--program=
for obj in all_shapes():
    obj.rotate(15, 'center', first=True)
''',)
    ]


class SimpInkScrCmdlineArgsTest(TestCase):
    effect_class = SimpleInkscapeScripting

    def test_argparse_input_file_with_svg_and_user_args(self):
        args = ["--program", "pass", self.empty_svg,
                "--", "-a", "1", "--b", "2", "3"]
        effect = self.effect_class()
        effect.parse_arguments(args)
        assert effect.options.input_file == self.empty_svg
        assert ['-a', '1', '--b', '2', '3'] == effect.options.user_args

    def test_argparse_input_file_with_dash_and_user_args(self):
        args = ["--program", "pass", "-", "--", "-a", "1", "--b", "2", "3"]
        effect = self.effect_class()
        effect.parse_arguments(args)
        # input_file is set to None to read stdin.
        assert effect.options.input_file is None
        assert ['-a', '1', '--b', '2', '3'] == effect.options.user_args


class SimpInkScrRestArgsTest(TestCase):
    effect_class = SimpleInkscapeScripting

    @patch('sys.stderr', new_callable=StringIO)
    def test_user_args_with_inputfile_and_no_user_args(self, _stderr):
        args = ["--program", "print(user_args)", self.empty_svg]
        effect = self.effect_class()
        effect.run(args)
        output = _stderr.getvalue().rstrip()
        assert "[]" == output

    @patch('sys.stderr', new_callable=StringIO)
    def test_user_args_without_inputfile_and_user_args(self, _stderr):
        args = ["--program", "print(user_args)"]
        effect = self.effect_class()

        with patch('sys.stdin', StringIO("<svg />")):
            effect.run(args)
            output = _stderr.getvalue().rstrip()
        assert "[]" == output

    @patch('sys.stderr', new_callable=StringIO)
    def test_user_args_with_dash_and_no_user_args(self, _stderr):
        args = ["--program", "print(user_args)", "-"]
        effect = self.effect_class()

        with patch('sys.stdin', StringIO("<svg />")):
            effect.run(args)
            output = _stderr.getvalue().rstrip()
        assert "[]" == output

    @patch('sys.stderr', new_callable=StringIO)
    def test_user_args_with_inputfile_and_user_args(self, _stderr):
        args = ["--program", "print(user_args)", self.empty_svg,
                "--", "-a", "1", "--b", "2", "3"]
        effect = self.effect_class()
        effect.run(args)
        output = _stderr.getvalue().rstrip()
        assert "['-a', '1', '--b', '2', '3']" == output

    @patch('sys.stderr', new_callable=StringIO)
    def test_user_args_with_dash_and_user_args(self, _stderr):
        args = ["--program", "print(user_args)", "-",
                "--", "-a", "1", "--b", "2", "3"]
        effect = self.effect_class()

        with patch('sys.stdin', StringIO("<svg />")):
            effect.run(args)
            output = _stderr.getvalue().rstrip()

        assert "['-a', '1', '--b', '2', '3']" == output
