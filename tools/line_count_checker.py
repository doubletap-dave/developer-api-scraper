#!/usr/bin/env python3
"""
Custom line count checker to enforce Python modular design standards.

This script enforces the line count limits defined in python_modular_design.md:
- Python Modules (.py files): Target ~250 lines, acceptable up to ~300
- Python Classes: Target ~150 lines, acceptable up to ~200
- Python Functions/Methods: Target ~40 lines, acceptable up to ~60

Usage:
    python tools/line_count_checker.py [--strict] [--exclude pattern1,pattern2]
"""

import ast
import argparse
import glob
import os
import sys
from typing import List, Dict, Tuple, Optional


class LineCountViolation:
    """Represents a line count violation."""
    
    def __init__(self, filepath: str, item_type: str, item_name: str, 
                 line_count: int, limit: int, target: int):
        self.filepath = filepath
        self.item_type = item_type
        self.item_name = item_name
        self.line_count = line_count
        self.limit = limit
        self.target = target
    
    def __str__(self):
        return (f"{self.filepath}:{self.item_name} ({self.item_type}) "
                f"has {self.line_count} lines (target: {self.target}, limit: {self.limit})")


class LineCountChecker:
    """Line count checker that analyzes Python files for compliance."""
    
    # Limits from python_modular_design.md
    MODULE_TARGET = 250
    MODULE_LIMIT = 300
    CLASS_TARGET = 150
    CLASS_LIMIT = 200
    FUNCTION_TARGET = 40
    FUNCTION_LIMIT = 60
    
    def __init__(self, strict: bool = False, exclude_patterns: List[str] = None):
        self.strict = strict
        self.exclude_patterns = exclude_patterns or []
        self.violations: List[LineCountViolation] = []
    
    def should_exclude_file(self, filepath: str) -> bool:
        """Check if file should be excluded based on patterns."""
        for pattern in self.exclude_patterns:
            if pattern in filepath:
                return True
        return False
    
    def count_lines(self, node: ast.AST, source_lines: List[str]) -> int:
        """Count actual lines of code for an AST node."""
        if not hasattr(node, 'lineno') or not hasattr(node, 'end_lineno'):
            return 0
        
        start_line = node.lineno
        end_line = node.end_lineno or node.lineno
        
        # Count non-empty, non-comment lines
        line_count = 0
        for i in range(start_line - 1, min(end_line, len(source_lines))):
            line = source_lines[i].strip()
            if line and not line.startswith('#'):
                line_count += 1
                
        return line_count
    
    def check_file(self, filepath: str) -> List[LineCountViolation]:
        """Check a single Python file for line count violations."""
        violations = []
        
        if self.should_exclude_file(filepath):
            return violations
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                source_lines = content.splitlines()
            
            # Parse the AST
            tree = ast.parse(content, filename=filepath)
            
            # Check module-level line count
            module_lines = len([line for line in source_lines 
                              if line.strip() and not line.strip().startswith('#')])
            
            limit = self.MODULE_LIMIT if not self.strict else self.MODULE_TARGET
            if module_lines > limit:
                violations.append(LineCountViolation(
                    filepath, "Module", os.path.basename(filepath),
                    module_lines, self.MODULE_LIMIT, self.MODULE_TARGET
                ))
            
            # Check classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_lines = self.count_lines(node, source_lines)
                    limit = self.CLASS_LIMIT if not self.strict else self.CLASS_TARGET
                    if class_lines > limit:
                        violations.append(LineCountViolation(
                            filepath, "Class", node.name,
                            class_lines, self.CLASS_LIMIT, self.CLASS_TARGET
                        ))
                
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = self.count_lines(node, source_lines)
                    limit = self.FUNCTION_LIMIT if not self.strict else self.FUNCTION_TARGET
                    if func_lines > limit:
                        violations.append(LineCountViolation(
                            filepath, "Function", node.name,
                            func_lines, self.FUNCTION_LIMIT, self.FUNCTION_TARGET
                        ))
        
        except Exception as e:
            print(f"Warning: Could not analyze {filepath}: {e}", file=sys.stderr)
        
        return violations
    
    def check_directory(self, directory: str = ".") -> List[LineCountViolation]:
        """Check all Python files in a directory recursively."""
        all_violations = []
        
        # Find all Python files
        python_files = glob.glob(os.path.join(directory, "**", "*.py"), recursive=True)
        
        for filepath in python_files:
            violations = self.check_file(filepath)
            all_violations.extend(violations)
        
        self.violations = all_violations
        return all_violations
    
    def print_report(self):
        """Print a detailed report of violations."""
        if not self.violations:
            print("✅ All files comply with line count limits!")
            return
        
        print(f"❌ Found {len(self.violations)} line count violations:")
        print()
        
        # Group by type
        violations_by_type = {}
        for violation in self.violations:
            if violation.item_type not in violations_by_type:
                violations_by_type[violation.item_type] = []
            violations_by_type[violation.item_type].append(violation)
        
        for item_type, violations in violations_by_type.items():
            print(f"{item_type} violations ({len(violations)}):")
            for violation in violations:
                excess = violation.line_count - violation.limit
                print(f"  • {violation} (+{excess} over limit)")
            print()
        
        print("📖 Modular Design Guidelines:")
        print(f"  • Modules: Target {self.MODULE_TARGET} lines, limit {self.MODULE_LIMIT}")
        print(f"  • Classes: Target {self.CLASS_TARGET} lines, limit {self.CLASS_LIMIT}")
        print(f"  • Functions: Target {self.FUNCTION_TARGET} lines, limit {self.FUNCTION_LIMIT}")
        print("\nSee plan/python_modular_design.md for detailed guidance on refactoring.")


def main():
    parser = argparse.ArgumentParser(
        description="Check Python files for line count compliance with modular design standards"
    )
    parser.add_argument(
        "--strict", 
        action="store_true",
        help="Use target limits instead of acceptable limits"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated list of path patterns to exclude"
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Directory to check (default: current directory)"
    )
    
    args = parser.parse_args()
    
    exclude_patterns = []
    if args.exclude:
        exclude_patterns = [pattern.strip() for pattern in args.exclude.split(",")]
    
    # Add common exclusions
    exclude_patterns.extend([
        "__pycache__",
        ".git/",
        ".venv/",
        "venv/",
        ".pytest_cache/",
        "build/",
        "dist/",
        ".mypy_cache/"
    ])
    
    checker = LineCountChecker(strict=args.strict, exclude_patterns=exclude_patterns)
    violations = checker.check_directory(args.directory)
    
    checker.print_report()
    
    # Exit with error code if violations found
    if violations:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
