"""Path builder module for Wyrm application.

This module handles the generation of deterministic file paths from item metadata,
ensuring consistent and predictable file organization.
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional, List

from wyrm.models.scrape import SidebarItem


class PathBuilder:
    """Service for building deterministic file paths from item metadata.
    
    Generates consistent file paths and names based on item metadata such as
    header, menu, and item text. Ensures paths are filesystem-safe and predictable.
    """
    
    def __init__(self) -> None:
        """Initialize the PathBuilder service."""
        pass
    
    def get_output_file_path(
        self,
        header: Optional[str],
        menu: Optional[str],
        item_text: str,
        base_output_dir: Path,
    ) -> Path:
        """Generate output file path based on item metadata.
        
        Creates a deterministic file path using header, menu, and item text
        to organize files in a hierarchical structure.
        
        Args:
            header: Header text for directory structure
            menu: Menu text for directory structure
            item_text: Item text for filename
            base_output_dir: Base output directory
            
        Returns:
            Complete file path for the output file
        """
        # Start with base directory
        path_parts = [base_output_dir]
        
        # Add header if available
        if header and header.strip():
            header_slug = self._slugify(header)
            if header_slug:
                path_parts.append(header_slug)
        
        # Add menu if available and different from header
        if menu and menu.strip() and menu != header:
            menu_slug = self._slugify(menu)
            if menu_slug:
                path_parts.append(menu_slug)
        
        # Create the directory path
        directory_path = Path(*path_parts)
        
        # Generate filename from item text
        filename_slug = self._slugify(item_text)
        if not filename_slug:
            filename_slug = "untitled"
            
        # Ensure .md extension
        if not filename_slug.endswith('.md'):
            filename_slug += '.md'
            
        return directory_path / filename_slug
    
    def get_output_filename(self, item: SidebarItem) -> str:
        """Generate output filename for a sidebar item.
        
        Creates a safe filename based on the item's text and ID,
        ensuring compatibility across different file systems.
        
        Args:
            item: SidebarItem to generate filename for.
            
        Returns:
            str: Safe filename for the item.
        """
        # Use item text and ID to create filename
        text = item.text if hasattr(item, 'text') else str(item.get('text', 'unknown'))
        item_id = item.id if hasattr(item, 'id') else item.get('id', 'unknown')
        
        # Clean text for filename
        safe_text = "".join(c for c in text if c.isalnum()
                           or c in (' ', '-', '_')).rstrip()
        safe_text = safe_text.replace(' ', '_')
        
        # Limit length and add ID
        if len(safe_text) > 50:
            safe_text = safe_text[:50]
            
        return f"{safe_text}_{item_id}.md"
    
    def build_structure_path(
        self,
        base_output_dir: Path,
        structure_name: str = "sidebar_structure.json"
    ) -> Path:
        """Build path for saving sidebar structure files.
        
        Args:
            base_output_dir: Base output directory
            structure_name: Name of the structure file
            
        Returns:
            Path to the structure file
        """
        return base_output_dir / structure_name
    
    def build_debug_path(
        self,
        debug_output_dir: Path,
        item_id: str,
        file_type: str = "html"
    ) -> Path:
        """Build path for debug files.
        
        Args:
            debug_output_dir: Debug output directory
            item_id: Unique identifier for the item
            file_type: Type of debug file (html, json, etc.)
            
        Returns:
            Path to the debug file
        """
        safe_item_id = self._slugify(item_id)
        return debug_output_dir / f"page_content_{safe_item_id}.{file_type}"
    
    def _slugify(self, value: str, allow_unicode: bool = False) -> str:
        """Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
        Remove characters that aren't alphanumerics, underscores, or hyphens.
        Convert to lowercase. Also strip leading and trailing whitespace.
        
        Args:
            value: String to slugify
            allow_unicode: Whether to allow unicode characters
            
        Returns:
            Slugified string suitable for file/directory names
        """
        if not value:
            return ""
            
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode(
                'ascii', 'ignore').decode('ascii')
        
        # Replace spaces and other separators with hyphens
        value = re.sub(r'[-\s_/\\]+', '-', value)
        
        # Remove characters that aren't alphanumerics, underscores, hyphens, or dots
        value = re.sub(r'[^\w\-\.]', '', value)
        
        # Convert to lowercase and strip
        value = value.lower().strip('-_.')
        
        # Limit length to reasonable filename size
        if len(value) > 100:
            value = value[:100].rstrip('-_.')
            
        return value
    
    def normalize_path_component(self, component: str) -> str:
        """Normalize a single path component for consistent naming.
        
        Args:
            component: Path component to normalize
            
        Returns:
            Normalized path component
        """
        return self._slugify(component)
    
    def validate_path_safety(self, path: Path) -> bool:
        """Validate that a path is safe for file operations.
        
        Checks for potentially dangerous path components and ensures
        the path doesn't escape the intended directory structure.
        
        Args:
            path: Path to validate
            
        Returns:
            bool: True if path is safe, False otherwise
        """
        try:
            # Convert to string for analysis
            path_str = str(path.resolve())
            
            # Check for dangerous patterns
            dangerous_patterns = [
                '..',  # Parent directory traversal
                '~',   # Home directory shortcuts
                '//',  # Double slashes
            ]
            
            for pattern in dangerous_patterns:
                if pattern in path_str:
                    return False
            
            # Check that path components are reasonable
            for part in path.parts:
                if not part or part.startswith('.') and part != '.':
                    return False
                    
                # Check for excessively long components
                if len(part) > 255:  # Most filesystems have 255 char limit
                    return False
            
            return True
            
        except Exception:
            # If any error occurs during validation, consider it unsafe
            return False
    
    def get_existing_files(self, directory: Path, items: List[SidebarItem]) -> List[Path]:
        """Get list of existing files for given items.
        
        Checks which items already have corresponding output files in the
        specified directory.
        
        Args:
            directory: Directory to check for existing files.
            items: List of sidebar items to check.
            
        Returns:
            List[Path]: List of existing file paths.
        """
        from .file_writer import FileWriter
        file_writer = FileWriter()
        existing_files = []
        
        for item in items:
            filename = self.get_output_filename(item)
            file_path = directory / filename
            
            if file_writer.check_file_exists(file_path):
                existing_files.append(file_path)
        
        return existing_files
