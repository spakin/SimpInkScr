##################################################
# Define a set of unit tests for Simple Inkscape #
# Scripting's Python output                      #
#                                                #
# Author: Scott Pakin <scott-ink@pakin.org>      #
##################################################

from simpinkscr.svg_to_simp_ink_script import SvgToPythonScript
from inkex.tester import ComparisonMixin, TestCase
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
            "refs", f"sispy{opstr}.out", check_exists=False
        )


class SimpInkScrOutputBasicTest(CustomComparisonMixin, TestCase):
    effect_class = SvgToPythonScript
    compare_file = 'svg/shapes.svg'
    comparisons = [()]
