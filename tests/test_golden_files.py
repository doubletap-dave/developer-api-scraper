#!/usr/bin/env python3
"""Golden-file tests for structure parser validation.

These tests ensure that the structure parser produces identical outputs
before and after refactoring by comparing against known-good golden files.
"""

import json
import pytest
from pathlib import Path

from wyrm.services.structure_parser.structure_parser import StructureParser


class TestGoldenFiles:
    """Test suite for golden-file validation of structure parser outputs."""

    @pytest.fixture
    def test_data_dir(self):
        """Return path to test data directory."""
        return Path(__file__).parent / "test_data"

    @pytest.fixture
    def parser(self):
        """Return a configured StructureParser instance."""
        return StructureParser()

    def load_expected_output(self, test_data_dir: Path, filename: str):
        """Load expected output from golden file."""
        golden_file_path = test_data_dir / filename
        with open(golden_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_test_html(self, test_data_dir: Path, filename: str):
        """Load test HTML from file."""
        html_file_path = test_data_dir / filename
        with open(html_file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_hierarchical_structure_parsing(self, parser, test_data_dir):
        """Test hierarchical structure parsing against golden file."""
        # Load test HTML and expected output
        html_content = self.load_test_html(test_data_dir, "sample_hierarchical.html")
        expected_structured = self.load_expected_output(test_data_dir, "expected_hierarchical_structured.json")
        
        # Parse the HTML
        actual_output = parser.parse(html_content)
        
        # Compare against golden file
        assert actual_output == expected_structured, (
            f"Hierarchical structure parsing output differs from golden file.\n"
            f"Expected: {json.dumps(expected_structured, indent=2)}\n"
            f"Actual: {json.dumps(actual_output, indent=2)}"
        )

    def test_hierarchical_structure_flattening(self, parser, test_data_dir):
        """Test hierarchical structure flattening against golden file."""
        # Load test HTML and expected output
        html_content = self.load_test_html(test_data_dir, "sample_hierarchical.html")
        expected_flattened = self.load_expected_output(test_data_dir, "expected_hierarchical_flattened.json")
        
        # Parse and flatten the HTML
        structured_output = parser.parse(html_content)
        actual_flattened = parser.flatten_sidebar_structure(structured_output)
        
        # Compare against golden file
        assert actual_flattened == expected_flattened, (
            f"Hierarchical structure flattening output differs from golden file.\n"
            f"Expected: {json.dumps(expected_flattened, indent=2)}\n"
            f"Actual: {json.dumps(actual_flattened, indent=2)}"
        )

    def test_flat_structure_parsing(self, parser, test_data_dir):
        """Test flat structure parsing against golden file."""
        # Load test HTML and expected output
        html_content = self.load_test_html(test_data_dir, "sample_flat.html")
        expected_structured = self.load_expected_output(test_data_dir, "expected_flat_structured.json")
        
        # Force flat structure parsing (as the auto-detection might classify it differently)
        soup = parser.html_cleaner.parse_html(html_content)
        sidebar_root = parser.html_cleaner.find_sidebar_root(soup)
        actual_output = parser._parse_flat_structure_with_trailing_header(sidebar_root)
        
        # Compare against golden file
        assert actual_output == expected_structured, (
            f"Flat structure parsing output differs from golden file.\n"
            f"Expected: {json.dumps(expected_structured, indent=2)}\n"
            f"Actual: {json.dumps(actual_output, indent=2)}"
        )

    def test_flat_structure_flattening(self, parser, test_data_dir):
        """Test flat structure flattening against golden file."""
        # Load test HTML and expected output
        html_content = self.load_test_html(test_data_dir, "sample_flat.html")
        expected_flattened = self.load_expected_output(test_data_dir, "expected_flat_flattened.json")
        
        # Force flat structure parsing and flatten
        soup = parser.html_cleaner.parse_html(html_content)
        sidebar_root = parser.html_cleaner.find_sidebar_root(soup)
        structured_output = parser._parse_flat_structure_with_trailing_header(sidebar_root)
        actual_flattened = parser.flatten_sidebar_structure(structured_output)
        
        # Compare against golden file
        assert actual_flattened == expected_flattened, (
            f"Flat structure flattening output differs from golden file.\n"
            f"Expected: {json.dumps(expected_flattened, indent=2)}\n"
            f"Actual: {json.dumps(actual_flattened, indent=2)}"
        )

    def test_empty_html_handling(self, parser):
        """Test that empty HTML is handled gracefully."""
        result = parser.parse("")
        assert result == []

    def test_malformed_html_handling(self, parser):
        """Test that malformed HTML is handled gracefully."""
        malformed_html = "<div><ul><li>Incomplete"
        result = parser.parse(malformed_html)
        assert result == []

    def test_html_without_sidebar_wrapper(self, parser):
        """Test HTML that lacks the expected sidebar wrapper."""
        html_without_wrapper = "<ul><li>No wrapper</li></ul>"
        result = parser.parse(html_without_wrapper)
        assert result == []

    @pytest.mark.parametrize("test_case", [
        ("sample_hierarchical.html", "expected_hierarchical_structured.json"),
        ("sample_flat.html", "expected_flat_structured.json"),
    ])
    def test_parser_idempotency(self, parser, test_data_dir, test_case):
        """Test that parsing the same HTML multiple times produces identical results."""
        html_file, expected_file = test_case
        html_content = self.load_test_html(test_data_dir, html_file)
        
        # Parse multiple times
        if "flat" in html_file:
            # Use forced flat parsing for consistency
            soup = parser.html_cleaner.parse_html(html_content)
            sidebar_root = parser.html_cleaner.find_sidebar_root(soup)
            result1 = parser._parse_flat_structure_with_trailing_header(sidebar_root)
            result2 = parser._parse_flat_structure_with_trailing_header(sidebar_root)
        else:
            result1 = parser.parse(html_content)
            result2 = parser.parse(html_content)
        
        # Results should be identical
        assert result1 == result2, "Parser should produce identical results on repeated parsing"

    def test_component_isolation(self, test_data_dir):
        """Test that individual components can be tested in isolation."""
        from wyrm.services.structure_parser.html_cleaner import HtmlCleaner
        from wyrm.services.structure_parser.markdown_converter import MarkdownConverter
        from wyrm.services.structure_parser.link_resolver import LinkResolver
        
        # Test that components can be instantiated independently
        html_cleaner = HtmlCleaner()
        markdown_converter = MarkdownConverter()
        link_resolver = LinkResolver()
        
        # Load test HTML
        html_content = self.load_test_html(test_data_dir, "sample_hierarchical.html")
        
        # Test HTML cleaning
        soup = html_cleaner.parse_html(html_content)
        assert soup is not None
        
        sidebar_root = html_cleaner.find_sidebar_root(soup)
        assert sidebar_root is not None
        
        # Test structure type detection
        structure_type = html_cleaner.detect_structure_type(soup)
        assert structure_type in ["hierarchical_with_leading_header", "flat_with_trailing_header", "unknown"]
