"""
Unit tests for CSS property sorting functionality.

Tests the sort_css_properties module to ensure it correctly
sorts CSS properties in alphabetical order.
"""

import unittest
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sort_css_properties import (  # noqa: E402
    parse_css_rule,
    sort_css_properties,
    format_css_rule,
    process_css_file
)


class TestCSSPropertySorting(unittest.TestCase):
    """Test cases for CSS property sorting."""

    def test_parse_css_rule(self):
        """Test parsing of CSS rules."""
        css_rule = ".test { color: red; background: blue }"
        selector, properties, trailing = parse_css_rule(css_rule)

        self.assertEqual(selector, ".test ")
        self.assertEqual(len(properties), 2)
        self.assertIn("color: red", properties)
        self.assertIn("background: blue", properties)
        self.assertEqual(trailing, "")

    def test_sort_css_properties(self):
        """Test sorting of CSS properties alphabetically."""
        properties = ["color: red", "background: blue", "padding: 10px"]
        sorted_props = sort_css_properties(properties)

        self.assertEqual(sorted_props[0], "background: blue")
        self.assertEqual(sorted_props[1], "color: red")
        self.assertEqual(sorted_props[2], "padding: 10px")

    def test_sort_properties_with_vendor_prefixes(self):
        """Test sorting with vendor prefixes."""
        properties = [
            "color: red",
            "-webkit-transform: rotate(0)",
            "background: blue"
        ]
        sorted_props = sort_css_properties(properties)

        # Vendor prefixes should be sorted correctly
        self.assertEqual(sorted_props[0], "-webkit-transform: rotate(0)")
        self.assertEqual(sorted_props[1], "background: blue")
        self.assertEqual(sorted_props[2], "color: red")

    def test_format_css_rule(self):
        """Test formatting of CSS rules."""
        selector = ".test "
        properties = ["background: blue", "color: red"]
        trailing = ""

        result = format_css_rule(selector, properties, trailing)
        expected = ".test { background: blue; color: red }"

        self.assertEqual(result, expected)

    def test_process_css_file_single_line(self):
        """Test processing a CSS file with single-line rules."""
        css_content = (
            ".class1 { color: red; background: blue }\n"
            ".class2 { padding: 10px; margin: 5px }"
        )

        result = process_css_file(css_content)

        # Check that properties are sorted
        self.assertIn("background: blue; color: red", result)
        self.assertIn("margin: 5px; padding: 10px", result)

    def test_process_css_file_with_comments(self):
        """Test processing CSS with comments."""
        css_content = ".highlight .err { color: #a40000; border: 1px solid }"

        result = process_css_file(css_content)

        # Border should come before color alphabetically
        self.assertIn("border: 1px solid; color: #a40000", result)

    def test_empty_properties(self):
        """Test handling of rules with no properties."""
        css_rule = ".test {}"
        selector, properties, trailing = parse_css_rule(css_rule)

        self.assertEqual(selector, ".test ")
        self.assertEqual(len(properties), 0)

    def test_process_preserves_structure(self):
        """Test that processing preserves overall CSS structure."""
        css_content = (
            "/* Comment */\n"
            ".class1 { color: red; background: blue }\n"
            "\n"
            ".class2 { padding: 10px }"
        )

        result = process_css_file(css_content)

        # Should preserve comments and blank lines
        self.assertIn("/* Comment */", result)
        self.assertEqual(result.count('\n'), css_content.count('\n'))

    def test_process_multiline_css_rules(self):
        """Test processing multi-line CSS rules."""
        css_content = (
            "body {\n"
            "    font-family: Georgia, serif;\n"
            "    font-size: 17px;\n"
            "    background-color: #fff;\n"
            "    color: #000;\n"
            "    margin: 0;\n"
            "    padding: 0;\n"
            "}"
        )

        result = process_css_file(css_content)

        # Check that properties are sorted alphabetically
        lines = result.split('\n')
        prop_lines = [
            line.strip().rstrip(';')
            for line in lines
            if ':' in line
        ]

        # Properties should be in alphabetical order
        self.assertEqual(prop_lines[0], "background-color: #fff")
        self.assertEqual(prop_lines[1], "color: #000")
        self.assertEqual(prop_lines[2], "font-family: Georgia, serif")
        self.assertEqual(prop_lines[3], "font-size: 17px")
        self.assertEqual(prop_lines[4], "margin: 0")
        self.assertEqual(prop_lines[5], "padding: 0")


if __name__ == '__main__':
    unittest.main()
