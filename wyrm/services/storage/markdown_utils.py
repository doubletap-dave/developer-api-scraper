"""Markdown sanitization utility functions.

This module provides functions for sanitizing and cleaning markdown content.
"""

import re


def apply_cleanup_patterns(content: str, patterns: list) -> str:
    """Apply regex cleanup patterns to content.

    Args:
        content: Content to clean
        patterns: List of pattern dictionaries {'pattern': str, 'replacement': str}
    
    Returns:
        Cleaned content
    """
    for pattern_info in patterns:
        content = re.sub(
            pattern_info['pattern'],
            pattern_info['replacement'],
            content,
            flags=re.MULTILINE
        )
    return content


def build_cleanup_patterns() -> list:
    """Build list of regex patterns for content cleanup.
    
    Returns:
        List of pattern dictionaries with 'pattern' and 'replacement'
    """
    return [
        # Remove excessive Unicode whitespace
        {'pattern': r'[\u200b\u200c\u200d\ufeff]+', 'replacement': ''},
        
        # Fix smart quotes
        {'pattern': r'[\u201c\u201d]', 'replacement': '"'},
        {'pattern': r'[\u2018\u2019]', 'replacement': "'"},
        
        # Fix em dashes and en dashes
        {'pattern': r'[\u2013\u2014]', 'replacement': '--'},
        
        # Remove invisible characters
        {'pattern': r'[\u00ad\u061c\u1680\u2000-\u200f\u2028-\u202f\u205f-\u206f]', 'replacement': ''},
        
        # Fix common HTML entities that slipped through
        {'pattern': r'&nbsp;', 'replacement': ' '},
        {'pattern': r'&amp;', 'replacement': '&'},
        {'pattern': r'&lt;', 'replacement': '<'},
        {'pattern': r'&gt;', 'replacement': '>'},
        {'pattern': r'&quot;', 'replacement': '"'},
        
        # Clean up broken markdown links
        {'pattern': r'\[([^\]]+)\]\(\s*\)', 'replacement': r'\1'},
        
        # Remove empty emphasis
        {'pattern': r'\*\*\s*\*\*', 'replacement': ''},
        {'pattern': r'__\s*__', 'replacement': ''},
        {'pattern': r'\*\s*\*', 'replacement': ''},
        {'pattern': r'_\s*_', 'replacement': ''},
    ]
