#!/usr/bin/env python3
"""
Sort CSS properties alphabetically within each rule.

This script processes CSS files and ensures that all properties
within each CSS rule are sorted in alphabetical order.
This helps satisfy code quality scanners that enforce
alphabetical property ordering.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def parse_css_rule(rule_text: str) -> Tuple[str, List[str], str]:
    """
    Parse a CSS rule into selector, properties, and trailing content.

    Args:
        rule_text: A CSS rule as a string

    Returns:
        A tuple of (selector, properties_list, trailing_content)
    """
    # Match the selector and the content between braces
    match = re.match(r'([^{]+)\{([^}]*)\}(.*)$', rule_text, re.DOTALL)
    if not match:
        return rule_text, [], ''

    selector = match.group(1)
    properties_block = match.group(2)
    trailing = match.group(3)

    # Split properties by semicolon
    properties = [
        prop.strip()
        for prop in properties_block.split(';')
        if prop.strip()
    ]

    return selector, properties, trailing


def sort_css_properties(properties: List[str]) -> List[str]:
    """
    Sort CSS properties alphabetically by property name.

    Args:
        properties: List of CSS property declarations

    Returns:
        Sorted list of CSS properties
    """
    # Sort by the property name (before the colon)
    return sorted(
        properties,
        key=lambda prop: prop.split(':')[0].strip().lower()
    )


def format_css_rule(
    selector: str,
    properties: List[str],
    trailing: str
) -> str:
    """
    Format a CSS rule with sorted properties.

    Args:
        selector: CSS selector
        properties: List of CSS properties
        trailing: Any content after the closing brace

    Returns:
        Formatted CSS rule as a string
    """
    if not properties:
        return f"{selector}{{{trailing}"

    properties_str = '; '.join(properties)
    return f"{selector}{{ {properties_str} }}{trailing}"


def process_css_file(css_content: str) -> str:
    """
    Process CSS content and sort properties in all rules.

    Args:
        css_content: The entire CSS file content

    Returns:
        Processed CSS content with sorted properties
    """
    # Split by newlines but preserve them
    lines = css_content.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if line contains a complete CSS rule (has both { and })
        if '{' in line and '}' in line:
            selector, properties, trailing = parse_css_rule(line)
            if properties:
                sorted_properties = sort_css_properties(properties)
                result_lines.append(
                    format_css_rule(selector, sorted_properties, trailing)
                )
            else:
                result_lines.append(line)
        else:
            # For multi-line rules or non-rule content, keep as-is
            result_lines.append(line)

        i += 1

    return '\n'.join(result_lines)


def main():
    """Main function to process CSS files."""
    if len(sys.argv) < 2:
        print("Usage: python sort_css_properties.py <css_file> [css_file ...]")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File {file_path} not found")
            continue

        print(f"Processing {file_path}...")

        # Read the CSS file
        with open(path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        # Process and sort properties
        processed_content = process_css_file(css_content)

        # Write back to the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(processed_content)

        print(f"✓ Processed {file_path}")


if __name__ == '__main__':
    main()
