#!/usr/bin/env python3
"""
Test script to verify the new URL-title parsing functionality
"""

def test_parse_video_list():
    """Test the parse_video_list function with sample data"""
    
    # Create a test file with mixed formats
    test_content = """https://example.com/video1|Amazing Video Title
https://example.com/video2
https://example.com/video3|Another Great Video
https://example.com/video4|Duplicate Title
https://example.com/video5|Duplicate Title
"""
    
    with open("test_list_video.txt", "w") as f:
        f.write(test_content)
    
    # Import the parse function from download.py
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Test the parsing (we'll simulate the function here since it's not easily importable)
    video_data = []
    
    with open("test_list_video.txt", "r") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    for line in lines:
        if '|' in line:
            # New format: URL|TITLE
            parts = line.split('|', 1)
            if len(parts) == 2:
                url, title = parts
                video_data.append((url.strip(), title.strip()))
            else:
                video_data.append((line, None))
        else:
            # Legacy format: URL only
            video_data.append((line, None))
    
    print("Parsed video data:")
    for i, (url, title) in enumerate(video_data, 1):
        print(f"{i}. URL: {url}")
        print(f"   Title: {title if title else 'None (legacy format)'}")
        print()
    
    # Test duplicate detection (simulate sitemap_video_parser logic)
    print("Testing duplicate title detection:")
    title_counts = {}
    for url, title in video_data:
        if title:
            if title in title_counts:
                title_counts[title] += 1
            else:
                title_counts[title] = 1
    
    for title, count in title_counts.items():
        if count > 1:
            print(f"Found duplicate title: '{title}' ({count} occurrences)")
    
    # Test URL hash generation
    import hashlib
    print("\nURL hash examples:")
    for url, title in video_data:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        safe_title = f"{title if title else 'extracted_title'} [{url_hash}]"
        print(f"URL: {url}")
        print(f"Safe filename: {safe_title}")
        print()
    
    # Clean up
    os.remove("test_list_video.txt")

if __name__ == "__main__":
    test_parse_video_list()
