#!/usr/bin/env python3
"""
Test for issue #27: summary must mark values as out of spec when min is 0.

When tran.yaml has min: 0 and max: 100, a value of 104 must be marked out of spec
(OK() False, markdown() returns styled span), not treated as in-spec because 0 is falsy.
"""

import unittest

import cicsim as cs


class TestSpecMinZero(unittest.TestCase):
    """Spec with min=0 must still flag values above max as out of spec."""

    def test_ok_false_when_above_max_and_min_is_zero(self):
        spec = cs.SpecMinMax({
            "src": ["i_vdd_70"],
            "name": "Active current at 70 C",
            "min": 0,
            "max": 100,
            "digits": 3,
            "scale": -1e6,
            "unit": "µA",
        })
        self.assertEqual(spec.min, 0)
        self.assertEqual(spec.max, 100)
        # 104 > max → out of spec
        self.assertFalse(spec.OK(104), "104 > max 100 should be out of spec when min=0")

    def test_ok_true_when_in_range_and_min_is_zero(self):
        spec = cs.SpecMinMax({
            "min": 0,
            "max": 100,
            "digits": 3,
            "unit": "µA",
        })
        self.assertTrue(spec.OK(50))
        self.assertTrue(spec.OK(0))
        self.assertTrue(spec.OK(100))

    def test_markdown_marks_out_of_spec_when_min_is_zero(self):
        spec = cs.SpecMinMax({
            "min": 0,
            "max": 100,
            "digits": 3,
            "unit": "µA",
        })
        # Value above max must be marked (red or orange span)
        out = spec.markdown(104)
        self.assertIn("color:", out, "104 > max should be marked with color when min=0")
        self.assertIn("104", out)

    def test_markdown_plain_when_in_spec_and_min_is_zero(self):
        spec = cs.SpecMinMax({
            "min": 0,
            "max": 100,
            "digits": 3,
            "unit": "µA",
        })
        out = spec.markdown(50)
        self.assertNotIn("color:", out, "50 in [0,100] should not be marked")
        self.assertIn("50", out)


if __name__ == "__main__":
    unittest.main()
