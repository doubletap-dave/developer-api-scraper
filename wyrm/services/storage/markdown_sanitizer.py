"""Markdown sanitizer module for Wyrm application.

This module handles cleaning and post-processing of markdown content,
ensuring consistent formatting and removing problematic elements.
"""

import logging
import re
from typing import Dict, List, Optional


class MarkdownSanitizer:
    """Service for cleaning and post-processing markdown content.
    
    Provides functionality to sanitize markdown content by removing
    problematic elements, fixing formatting issues, and ensuring
    consistent output quality.
    """
    
    def __init__(self) -> None:
        """Initialize the MarkdownSanitizer service."""
        self._cleanup_patterns = self._build_cleanup_patterns()
    
    def sanitize_content(
        self,
        content: str,
        remove_empty_lines: bool = True,
        fix_headers: bool = True,
        clean_tables: bool = True,
        normalize_whitespace: bool = True
    ) -> str:
        """Sanitize markdown content with various cleaning options.
        
        Args:
            content: Raw markdown content to sanitize
            remove_empty_lines: Whether to remove excessive empty lines
            fix_headers: Whether to fix header formatting
            clean_tables: Whether to clean up table formatting
            normalize_whitespace: Whether to normalize whitespace
            
        Returns:
            Cleaned markdown content
        """
        if not content or not content.strip():
            return ""
        
        sanitized = content
        
        try:
            # Apply cleanup patterns
            sanitized = self._apply_cleanup_patterns(sanitized)
            
            # Fix header formatting if requested
            if fix_headers:
                sanitized = self._fix_header_formatting(sanitized)
            
            # Clean table formatting if requested
            if clean_tables:
                sanitized = self._clean_table_formatting(sanitized)
            
            # Normalize whitespace if requested
            if normalize_whitespace:
                sanitized = self._normalize_whitespace(sanitized)
            
            # Remove excessive empty lines if requested
            if remove_empty_lines:
                sanitized = self._remove_excessive_empty_lines(sanitized)
            
            # Final cleanup
            sanitized = sanitized.strip()
            
            logging.debug(f"Sanitized content: {len(content)} -> {len(sanitized)} chars")
            return sanitized
            
        except Exception as e:
            logging.error(f"Error sanitizing markdown content: {e}")
            # Return original content if sanitization fails
            return content
    
    def remove_html_comments(self, content: str) -> str:
        """Remove HTML comments from markdown content.
        
        Args:
            content: Markdown content with potential HTML comments
            
        Returns:
            Content with HTML comments removed
        """
        # Remove HTML comments
        return re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    def fix_code_blocks(self, content: str) -> str:
        """Fix common code block formatting issues.
        
        Args:
            content: Markdown content with potential code block issues
            
        Returns:
            Content with fixed code blocks
        """
        # Fix incomplete code blocks
        content = re.sub(r'^```([^`\n]*)\n(.*?)\n(?!```)$', r'```\1\n\2\n```', 
                        content, flags=re.MULTILINE | re.DOTALL)
        
        # Ensure code blocks have proper spacing
        content = re.sub(r'(\n```[^\n]*\n)', r'\n\1', content)
        content = re.sub(r'(\n```\n)', r'\1\n', content)
        
        return content
    
    def standardize_headers(self, content: str) -> str:
        """Standardize header formatting to ATX style.
        
        Args:
            content: Markdown content with various header styles
            
        Returns:
            Content with standardized ATX headers
        """
        lines = content.split('\n')
        processed_lines = []
        
        for i, line in enumerate(lines):
            # Convert setext headers to ATX
            if i > 0 and line.strip() and all(c in '=-' for c in line.strip()):
                # Check if previous line could be a header
                prev_line = lines[i-1].strip()
                if prev_line and not prev_line.startswith('#'):
                    # Convert to ATX header
                    level = 1 if '=' in line else 2
                    header = '#' * level + ' ' + prev_line
                    processed_lines[-1] = header  # Replace previous line
                    continue  # Skip the underline
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _build_cleanup_patterns(self) -> List[Dict]:
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
    
    def _apply_cleanup_patterns(self, content: str) -> str:
        """Apply regex cleanup patterns to content.
        
        Args:
            content: Content to clean
            
        Returns:
            Cleaned content
        """
        for pattern_info in self._cleanup_patterns:
            content = re.sub(
                pattern_info['pattern'],
                pattern_info['replacement'],
                content,
                flags=re.MULTILINE
            )
        return content
    
    def _fix_header_formatting(self, content: str) -> str:
        """Fix common header formatting issues.
        
        Args:
            content: Content with potential header issues
            
        Returns:
            Content with fixed headers
        """
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Fix headers with missing space after #
            if line.strip().startswith('#') and not line.strip().startswith('# '):
                # Count the number of # at the start
                match = re.match(r'^(\s*)(#+)(.*)$', line)
                if match:
                    indent, hashes, rest = match.groups()
                    if rest and not rest.startswith(' '):
                        line = f"{indent}{hashes} {rest.lstrip()}"
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _clean_table_formatting(self, content: str) -> str:
        """Clean up table formatting issues.
        
        Args:
            content: Content with potential table issues
            
        Returns:
            Content with cleaned tables
        """
        # Fix table separators
        content = re.sub(r'\|\s*-+\s*\|', lambda m: '|' + '-' * (len(m.group()) - 2) + '|', content)
        
        # Ensure tables have proper spacing
        lines = content.split('\n')
        processed_lines = []
        in_table = False
        
        for i, line in enumerate(lines):
            is_table_line = '|' in line.strip() and line.strip().startswith('|') and line.strip().endswith('|')
            
            if is_table_line and not in_table:
                # Starting a table - add space before if needed
                if processed_lines and processed_lines[-1].strip():
                    processed_lines.append('')
                in_table = True
            elif not is_table_line and in_table:
                # Ending a table - add space after if needed
                in_table = False
                processed_lines.append(line)
                if i < len(lines) - 1 and lines[i + 1].strip():
                    processed_lines.append('')
                continue
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace in content.
        
        Args:
            content: Content to normalize
            
        Returns:
            Content with normalized whitespace
        """
        # Convert tabs to spaces
        content = content.expandtabs(4)
        
        # Remove trailing whitespace from lines
        lines = content.split('\n')
        lines = [line.rstrip() for line in lines]
        
        return '\n'.join(lines)
    
    def _remove_excessive_empty_lines(self, content: str) -> str:
        """Remove excessive empty lines (more than 2 consecutive).
        
        Args:
            content: Content with potential excessive empty lines
            
        Returns:
            Content with reduced empty lines
        """
        # Replace 3+ consecutive newlines with 2
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def validate_markdown_structure(self, content: str) -> Dict[str, bool]:
        """Validate markdown structure and report issues.
        
        Args:
            content: Markdown content to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'has_headers': bool(re.search(r'^#+\s+.+', content, re.MULTILINE)),
            'has_proper_code_blocks': self._validate_code_blocks(content),
            'has_balanced_emphasis': self._validate_emphasis(content),
            'has_valid_links': self._validate_links(content),
            'has_clean_tables': self._validate_tables(content),
        }
        
        return validation_results
    
    def _validate_code_blocks(self, content: str) -> bool:
        """Validate code block structure."""
        # Count opening and closing code blocks
        opening_blocks = len(re.findall(r'^```', content, re.MULTILINE))
        return opening_blocks % 2 == 0  # Should be even (pairs)
    
    def _validate_emphasis(self, content: str) -> bool:
        """Validate emphasis markers are balanced."""
        # Count various emphasis markers
        bold_double = content.count('**')
        bold_under = content.count('__')
        italic_single = content.count('*') - (bold_double * 2)  # Subtract bold asterisks
        italic_under = content.count('_') - (bold_under * 2)   # Subtract bold underscores
        
        return (bold_double % 2 == 0 and bold_under % 2 == 0 and 
                italic_single % 2 == 0 and italic_under % 2 == 0)
    
    def _validate_links(self, content: str) -> bool:
        """Validate link structure."""
        # Check for broken links (empty href)
        broken_links = re.findall(r'\[([^\]]+)\]\(\s*\)', content)
        return len(broken_links) == 0
    
    def _validate_tables(self, content: str) -> bool:
        """Validate table structure."""
        table_lines = [line for line in content.split('\n') if '|' in line]
        
        for line in table_lines:
            # Check if table lines start and end with |
            stripped = line.strip()
            if stripped and not (stripped.startswith('|') and stripped.endswith('|')):
                return False
        
        return True
