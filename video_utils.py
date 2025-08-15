#!/usr/bin/env python3
"""
Shared utilities for video processing scripts
Contains common functions used across sitemap_video_parser.py, download.py, and unified_video_organizer.py
"""

import re
import hashlib

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Strip whitespace
    filename = filename.strip()
    return filename

def truncate_title_smart(title, max_length=200):
    """
    Smart truncation that preserves meaning while staying under filename limits.
    Leaves room for file extensions and temporary filenames created by downloaders.
    """
    if not title:
        return "UNTITLED_VIDEO"
    
    # First sanitize the title
    clean_title = sanitize_filename(title)
    
    # If already short enough, return as-is
    if len(clean_title) <= max_length:
        return clean_title
    
    # For very long titles, create a shortened version with hash
    # This ensures uniqueness even when truncated
    
    # Create hash of original title for uniqueness
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()[:8]
    
    # Calculate available space for the title part
    # Reserve space for: " [HASH]" = 11 characters
    available_length = max_length - 11
    
    if available_length < 20:
        # If we have very little space, just use hash-based name
        return f"VIDEO_{title_hash.upper()}"
    
    # Try to find a good breaking point (word boundary)
    truncated = clean_title[:available_length]
    
    # Try to break at word boundary if possible
    last_space = truncated.rfind(' ')
    if last_space > available_length * 0.7:  # If we can save at least 70% of the length
        truncated = truncated[:last_space]
    
    # Add hash for uniqueness
    result = f"{truncated} [{title_hash.upper()}]"
    
    return result

def create_url_title_from_url(url):
    """Create a title from URL (consistent across all scripts)"""
    try:
        if "/updates/" in url:
            url_part = url.split("/updates/")[1]
            # Remove any trailing slashes and parameters
            url_part = url_part.split('?')[0].rstrip('/')
            # Convert hyphens to spaces and make uppercase
            url_title = url_part.replace('-', ' ').upper()
            return truncate_title_smart(url_title)
    except Exception:
        pass
    return "UNKNOWN_VIDEO"

def normalize_title_for_matching(title):
    """Normalize title for case-insensitive matching"""
    if not title:
        return ""
    
    # Convert to lowercase and remove extra spaces
    normalized = re.sub(r'\s+', ' ', title.lower().strip())
    # Remove special characters for matching
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized

def get_consistent_filename(title, url=None):
    """
    Get a consistent filename that all scripts will use.
    This ensures the same video gets the same filename across all scripts.
    """
    if not title and url:
        title = create_url_title_from_url(url)
    elif not title:
        title = "UNKNOWN_VIDEO"
    
    # Apply smart truncation
    clean_title = truncate_title_smart(title)
    
    return clean_title

# Test the function if run directly
if __name__ == "__main__":
    # Test cases
    test_titles = [
        "Short Title",
        "Scheming Bar Maids Vivica Lase and Natalie Charm stage a robbery to clean out the safe and screw over the Boss Part 1 The Foolproof plan Natalie gets worked over zip tied stripped and toy fucked orgasm to make it look real",
        "ANOTHER EXTREMELY LONG TITLE THAT GOES ON AND ON AND ON WITH LOTS OF DETAILS AND SPECIFIC INFORMATION THAT MAKES IT WAY TOO LONG FOR FILESYSTEM",
        "",
        "Normal Title With Some Details"
    ]
    
    print("Testing title truncation:")
    for title in test_titles:
        result = get_consistent_filename(title)
        print(f"Original ({len(title)}): {title}")
        print(f"Result   ({len(result)}): {result}")
        print()
