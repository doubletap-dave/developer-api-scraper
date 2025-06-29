#!/usr/bin/env python3
"""
Line Audit Tool for Wyrm Project
Generates comprehensive line count reports for all Python files in the project.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime


def count_lines_in_file(file_path: Path) -> Tuple[int, int, int]:
    """
    Count total, code, and comment lines in a Python file.

    Returns:
        Tuple of (total_lines, code_lines, comment_lines)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, IOError):
        return 0, 0, 0

    total_lines = len(lines)
    code_lines = 0
    comment_lines = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        elif stripped.startswith('#'):
            comment_lines += 1
        elif '"""' in stripped or "'''" in stripped:
            # Simple docstring detection (not perfect but adequate)
            comment_lines += 1
        else:
            code_lines += 1

    return total_lines, code_lines, comment_lines


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    try:
        return file_path.stat().st_size
    except OSError:
        return 0


def scan_directory(directory: Path, extensions: List[str] = None) -> Dict:
    """
    Scan directory for files and collect line counts.

    Args:
        directory: Directory to scan
        extensions: List of file extensions to include (default: ['.py'])

    Returns:
        Dictionary with file analysis results
    """
    if extensions is None:
        extensions = ['.py']

    results = {
        'files': [],
        'summary': {
            'total_files': 0,
            'total_lines': 0,
            'total_code_lines': 0,
            'total_comment_lines': 0,
            'total_size_bytes': 0
        }
    }

    for root, dirs, files in os.walk(directory):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and
                   d not in ['__pycache__', 'node_modules', 'venv', '.venv']]

        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in extensions:
                total_lines, code_lines, comment_lines = count_lines_in_file(file_path)
                file_size = get_file_size(file_path)

                relative_path = file_path.relative_to(directory)

                file_data = {
                    'path': str(relative_path),
                    'size_bytes': file_size,
                    'total_lines': total_lines,
                    'code_lines': code_lines,
                    'comment_lines': comment_lines,
                    'blank_lines': total_lines - code_lines - comment_lines
                }

                results['files'].append(file_data)
                results['summary']['total_files'] += 1
                results['summary']['total_lines'] += total_lines
                results['summary']['total_code_lines'] += code_lines
                results['summary']['total_comment_lines'] += comment_lines
                results['summary']['total_size_bytes'] += file_size

    # Sort files by line count (descending)
    results['files'].sort(key=lambda x: x['total_lines'], reverse=True)

    return results


def identify_oversized_modules(results: Dict, threshold: int = 500) -> List[Dict]:
    """
    Identify modules that exceed the line count threshold.

    Args:
        results: Results from scan_directory
        threshold: Line count threshold for "oversized" classification

    Returns:
        List of oversized modules
    """
    oversized = []
    for file_data in results['files']:
        if file_data['total_lines'] > threshold:
            oversized.append(file_data)

    return oversized


def generate_report(results: Dict, output_file: str = None) -> str:
    """
    Generate a comprehensive line count report.

    Args:
        results: Results from scan_directory
        output_file: Optional file to write report to

    Returns:
        Report string
    """
    report_lines = []

    # Header
    report_lines.append("=" * 80)
    report_lines.append("WYRM PROJECT LINE COUNT AUDIT REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Summary
    summary = results['summary']
    report_lines.append("SUMMARY")
    report_lines.append("-" * 40)
    report_lines.append(f"Total Python files: {summary['total_files']}")
    report_lines.append(f"Total lines: {summary['total_lines']:,}")
    report_lines.append(f"Total code lines: {summary['total_code_lines']:,}")
    report_lines.append(f"Total comment lines: {summary['total_comment_lines']:,}")
    size_kb = summary['total_size_bytes']/1024
    report_lines.append(f"Total size: {summary['total_size_bytes']:,} bytes ({size_kb:.1f} KB)")
    report_lines.append("")

    # Oversized modules
    oversized = identify_oversized_modules(results, threshold=500)
    report_lines.append("OVERSIZED MODULES (>500 lines)")
    report_lines.append("-" * 40)
    if oversized:
        for i, module in enumerate(oversized, 1):
            report_lines.append(f"{i:2d}. {module['path']}")
            report_lines.append(
                f"    Lines: {module['total_lines']:,} | "
                f"Code: {module['code_lines']:,} | "
                f"Size: {module['size_bytes']:,} bytes"
            )
        report_lines.append("")
        report_lines.append(f"Total oversized modules: {len(oversized)}")
    else:
        report_lines.append("No modules exceed 500 lines.")
    report_lines.append("")

    # Top 20 largest files
    report_lines.append("TOP 20 LARGEST FILES BY LINE COUNT")
    report_lines.append("-" * 60)
    report_lines.append(
        f"{'Rank':<4} {'Lines':<6} {'Code':<6} {'Size (KB)':<10} {'File'}"
    )
    report_lines.append("-" * 60)

    for i, file_data in enumerate(results['files'][:20], 1):
        size_kb = file_data['size_bytes'] / 1024
        report_lines.append(
            f"{i:<4} {file_data['total_lines']:<6} {file_data['code_lines']:<6} "
            f"{size_kb:<10.1f} {file_data['path']}"
        )

    report_lines.append("")

    # All files details
    report_lines.append("ALL FILES DETAILED BREAKDOWN")
    report_lines.append("-" * 80)
    report_lines.append(
        f"{'Lines':<6} {'Code':<6} {'Comments':<8} "
        f"{'Blank':<6} {'Size (KB)':<10} {'File'}"
    )
    report_lines.append("-" * 80)

    for file_data in results['files']:
        size_kb = file_data['size_bytes'] / 1024
        report_lines.append(
            f"{file_data['total_lines']:<6} {file_data['code_lines']:<6} "
            f"{file_data['comment_lines']:<8} {file_data['blank_lines']:<6} "
            f"{size_kb:<10.1f} {file_data['path']}"
        )

    report = '\n'.join(report_lines)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report written to: {output_file}")

    return report


def main():
    """Main function to run the line audit."""
    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"Scanning project at: {project_root}")
    print("Analyzing Python files...")

    # Scan the project
    results = scan_directory(project_root)

    # Generate timestamp for output files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Generate and save report
    report_file = project_root / f"line_count_report_{timestamp}.txt"
    generate_report(results, str(report_file))

    # Save JSON data for programmatic access
    json_file = project_root / f"line_count_data_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"JSON data saved to: {json_file}")

    # Print summary to console
    print("\n" + "=" * 50)
    print("QUICK SUMMARY")
    print("=" * 50)
    summary = results['summary']
    print(f"Total Python files: {summary['total_files']}")
    print(f"Total lines: {summary['total_lines']:,}")
    print(f"Total code lines: {summary['total_code_lines']:,}")

    oversized = identify_oversized_modules(results, threshold=500)
    print(f"Oversized modules (>500 lines): {len(oversized)}")

    if oversized:
        print("\nOversized modules:")
        for module in oversized:
            print(f"  - {module['path']}: {module['total_lines']} lines")


if __name__ == "__main__":
    main()
