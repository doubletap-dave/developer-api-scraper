"""File writer module for Wyrm application.

This module handles atomic file writing operations, resume functionality,
and checksum validation for reliable file operations.
"""

import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Optional


class FileWriter:
    """Service for atomic file writing with resume and checksum support.
    
    Provides atomic write operations, resume functionality, and checksum
    validation to ensure reliable file operations.
    """
    
    def __init__(self) -> None:
        """Initialize the FileWriter service."""
        pass
    
    def write_file_atomic(
        self,
        content: str,
        output_path: Path,
        item_info: Optional[str] = None,
        verify_checksum: bool = True
    ) -> bool:
        """Write content to file atomically with checksum verification.
        
        Performs atomic write operation by writing to a temporary file first,
        then moving it to the final location. Optionally verifies content
        integrity using checksums.
        
        Args:
            content: Content string to save to file.
            output_path: Path where the content should be saved.
            item_info: Optional information about the item for logging.
            verify_checksum: Whether to verify content integrity.
            
        Returns:
            bool: True if write was successful, False otherwise.
        """
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Calculate checksum before writing if verification is enabled
            expected_checksum = None
            if verify_checksum:
                expected_checksum = self._calculate_checksum(content)
            
            # Write to temporary file first (atomic operation)
            temp_file = None
            try:
                # Create temporary file in the same directory as the target
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    encoding='utf-8',
                    dir=output_path.parent,
                    delete=False,
                    suffix='.tmp'
                ) as f:
                    temp_file = Path(f.name)
                    f.write(content)
                
                # Verify checksum if enabled
                if verify_checksum and expected_checksum:
                    if not self._verify_file_checksum(temp_file, expected_checksum):
                        logging.error(f"Checksum verification failed for {output_path}")
                        return False
                
                # Atomic move to final location
                temp_file.replace(output_path)
                
                logging.info(f"Content saved atomically to: {output_path}")
                return True
                
            except Exception as e:
                # Clean up temporary file if it exists
                if temp_file and temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception as cleanup_error:
                        logging.warning(f"Failed to cleanup temp file {temp_file}: {cleanup_error}")
                raise e
                
        except Exception as e:
            error_msg = f"Failed to save content to {output_path}: {e}"
            if item_info:
                error_msg = f"Failed to save {item_info} to {output_path}: {e}"
            logging.error(error_msg)
            return False
    
    def check_file_exists(self, file_path: Path) -> bool:
        """Check if a file exists.
        
        Simple utility to check file existence with proper error handling.
        
        Args:
            file_path: Path to check for existence.
            
        Returns:
            bool: True if file exists, False otherwise.
        """
        try:
            return file_path.exists() and file_path.is_file()
        except Exception as e:
            logging.error(f"Error checking file existence {file_path}: {e}")
            return False
    
    def can_resume_write(self, file_path: Path, expected_content: str) -> bool:
        """Check if a file write can be resumed by comparing content.
        
        Determines if an existing file matches the expected content,
        allowing for resume functionality.
        
        Args:
            file_path: Path to the existing file.
            expected_content: Content that should be in the file.
            
        Returns:
            bool: True if file exists and matches expected content.
        """
        try:
            if not self.check_file_exists(file_path):
                return False
            
            # Read existing file content
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Compare checksums for efficiency
            existing_checksum = self._calculate_checksum(existing_content)
            expected_checksum = self._calculate_checksum(expected_content)
            
            return existing_checksum == expected_checksum
            
        except Exception as e:
            logging.error(f"Error checking resume capability for {file_path}: {e}")
            return False
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content.
        
        Args:
            content: String content to checksum.
            
        Returns:
            str: SHA-256 checksum as hex string.
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _verify_file_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file content matches expected checksum.
        
        Args:
            file_path: Path to file to verify.
            expected_checksum: Expected SHA-256 checksum.
            
        Returns:
            bool: True if checksums match, False otherwise.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            actual_checksum = self._calculate_checksum(content)
            return actual_checksum == expected_checksum
            
        except Exception as e:
            logging.error(f"Error verifying checksum for {file_path}: {e}")
            return False
