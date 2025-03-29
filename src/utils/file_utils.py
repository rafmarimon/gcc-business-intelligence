#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File Utilities Module

This module provides helper functions for working with files and directories.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def ensure_dir_exists(dir_path: str) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        dir_path: Path to the directory
        
    Returns:
        True if the directory exists or was created successfully, False otherwise
    """
    if not dir_path:
        return False
        
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"Created directory: {dir_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {dir_path}: {str(e)}")
        return False

def get_file_content(file_path: str, default_content: str = "", encoding: str = 'utf-8') -> str:
    """
    Read the contents of a file.
    
    Args:
        file_path: Path to the file
        default_content: Content to return if the file doesn't exist or can't be read
        encoding: File encoding
        
    Returns:
        The contents of the file or the default content if the file doesn't exist
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return default_content

def save_file_content(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    Save content to a file.
    
    Args:
        file_path: Path to the file
        content: Content to save
        encoding: File encoding
        
    Returns:
        True if the file was saved successfully, False otherwise
    """
    try:
        # Ensure the directory exists
        ensure_dir_exists(os.path.dirname(file_path))
        
        # Write the content
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {str(e)}")
        return False

def append_file_content(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    Append content to a file.
    
    Args:
        file_path: Path to the file
        content: Content to append
        encoding: File encoding
        
    Returns:
        True if the file was appended successfully, False otherwise
    """
    try:
        # Ensure the directory exists
        ensure_dir_exists(os.path.dirname(file_path))
        
        # Append the content
        with open(file_path, 'a', encoding=encoding) as f:
            f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"Error appending to file {file_path}: {str(e)}")
        return False

def file_exists(file_path: str) -> bool:
    """
    Check if a file exists.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file exists, False otherwise
    """
    return os.path.isfile(file_path)

def list_files(dir_path: str, pattern: Optional[str] = None, recursive: bool = False) -> List[str]:
    """
    List files in a directory, optionally filtered by a pattern.
    
    Args:
        dir_path: Path to the directory
        pattern: Optional glob pattern to filter files
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    try:
        import glob
        
        if not os.path.exists(dir_path):
            return []
            
        if pattern:
            if recursive:
                search_pattern = os.path.join(dir_path, "**", pattern)
                return glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(dir_path, pattern)
                return glob.glob(search_pattern)
        else:
            if recursive:
                result = []
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        result.append(os.path.join(root, file))
                return result
            else:
                return [
                    os.path.join(dir_path, f) 
                    for f in os.listdir(dir_path) 
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
    except Exception as e:
        logger.error(f"Error listing files in {dir_path}: {str(e)}")
        return []

def get_newest_file(dir_path: str, pattern: Optional[str] = None) -> Optional[str]:
    """
    Get the newest file in a directory, optionally filtered by a pattern.
    
    Args:
        dir_path: Path to the directory
        pattern: Optional glob pattern to filter files
        
    Returns:
        Path to the newest file, or None if no files found
    """
    files = list_files(dir_path, pattern)
    
    if not files:
        return None
        
    return max(files, key=os.path.getmtime)

def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Size of the file in bytes, or 0 if the file does not exist
    """
    try:
        if not os.path.exists(file_path):
            return 0
            
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting size of file {file_path}: {str(e)}")
        return 0

def delete_file(file_path: str) -> bool:
    """
    Delete a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file was deleted successfully, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return True
            
        os.remove(file_path)
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False 