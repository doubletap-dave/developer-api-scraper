#!/usr/bin/env python3
"""Script to generate golden file outputs for the structure parser."""

import json
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from wyrm.services.structure_parser.structure_parser import StructureParser


def generate_golden_files():
    """Generate golden file outputs from test HTML."""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    parser = StructureParser()
    test_data_dir = project_root / "tests" / "test_data"
    
    # Test hierarchical structure
    hierarchical_html_path = test_data_dir / "sample_hierarchical.html"
    with open(hierarchical_html_path, 'r', encoding='utf-8') as f:
        hierarchical_html = f.read()
    
    hierarchical_output = parser.parse(hierarchical_html)
    hierarchical_flattened = parser.flatten_sidebar_structure(hierarchical_output)
    
    # Save hierarchical outputs
    with open(test_data_dir / "expected_hierarchical_structured.json", 'w') as f:
        json.dump(hierarchical_output, f, indent=2)
    
    with open(test_data_dir / "expected_hierarchical_flattened.json", 'w') as f:
        json.dump(hierarchical_flattened, f, indent=2)
    
    # Test flat structure
    flat_html_path = test_data_dir / "sample_flat.html"
    with open(flat_html_path, 'r', encoding='utf-8') as f:
        flat_html = f.read()
    
    # Force flat structure detection
    soup = parser.html_cleaner.parse_html(flat_html)
    sidebar_root = parser.html_cleaner.find_sidebar_root(soup)
    flat_output = parser._parse_flat_structure_with_trailing_header(sidebar_root)
    flat_flattened = parser.flatten_sidebar_structure(flat_output)
    
    # Save flat outputs
    with open(test_data_dir / "expected_flat_structured.json", 'w') as f:
        json.dump(flat_output, f, indent=2)
    
    with open(test_data_dir / "expected_flat_flattened.json", 'w') as f:
        json.dump(flat_flattened, f, indent=2)
    
    print("Golden files generated successfully!")
    print(f"Hierarchical structured: {len(hierarchical_output)} header groups")
    print(f"Hierarchical flattened: {len(hierarchical_flattened)} items")
    print(f"Flat structured: {len(flat_output)} header groups")
    print(f"Flat flattened: {len(flat_flattened)} items")


if __name__ == "__main__":
    generate_golden_files()
