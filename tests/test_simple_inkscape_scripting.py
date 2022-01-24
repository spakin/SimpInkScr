from simple_inkscape_scripting import SimpleInkscapeScripting
from inkex.tester import ComparisonMixin, InkscapeExtensionTestMixin, TestCase
from inkex.tester.filters import CompareOrderIndependentStyle

class SimpInkScrTrivial(ComparisonMixin, InkscapeExtensionTestMixin, TestCase):
    effect_class = SimpleInkscapeScripting
    compare_filters = [CompareOrderIndependentStyle()]
    comparisons = [
        ('--program=circle((100, 100), 75)',)
    ]
    compare_file = 'svg/default-inkscape-SVG.svg'
