#!/usr/bin/env python3
"""
Test script to validate metadata extraction with the new selectors
"""

import sys
from unified_video_organizer import setup_headless_browser, extract_video_metadata, log_with_timestamp

def test_extraction():
    """Test metadata extraction on a single video page"""
    
    # Get test URL from user
    domain = input("Enter domain (e.g., https://shinybound.com): ").strip()
    if not domain:
        print("❌ Domain required")
        return
    
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    domain = domain.rstrip('/')
    
    test_url = input("Enter a test video URL: ").strip()
    if not test_url:
        print("❌ Test URL required")
        return
    
    # Setup browser
    log_with_timestamp("🔧 Setting up browser...")
    driver = setup_headless_browser()
    if not driver:
        print("❌ Failed to setup browser")
        return
    
    try:
        # Extract metadata
        log_with_timestamp(f"🧪 Testing metadata extraction on: {test_url}")
        metadata = extract_video_metadata(driver, test_url)
        
        if metadata:
            print("\n" + "="*60)
            print("EXTRACTION RESULTS:")
            print("="*60)
            print(f"Title: {metadata.get('title', 'NOT FOUND')}")
            print(f"Model: {metadata.get('model', 'NOT FOUND')}")
            print(f"Tags ({len(metadata.get('tags', []))}): {', '.join(metadata.get('tags', []))}")
            print(f"Description: {metadata.get('description', 'NOT FOUND')[:100]}...")
            print(f"Thumbnail: {metadata.get('thumbnail', 'NOT FOUND')}")
            print(f"Duration: {metadata.get('duration', 'NOT FOUND')}")
            print(f"Date: {metadata.get('date', 'NOT FOUND')}")
            print(f"Related Videos ({len(metadata.get('related_videos', []))}): ")
            for i, related in enumerate(metadata.get('related_videos', []), 1):
                print(f"  {i}. {related.get('title', 'Unknown')}")
            print("="*60)
            
            # Check what was successfully extracted
            success_count = 0
            if metadata.get('title'): success_count += 1
            if metadata.get('model'): success_count += 1
            if metadata.get('tags'): success_count += 1
            if metadata.get('description'): success_count += 1
            if metadata.get('thumbnail'): success_count += 1
            if metadata.get('related_videos'): success_count += 1
            
            print(f"\n✅ Successfully extracted {success_count}/6 metadata fields")
            
            if not metadata.get('model'):
                print("⚠️  Model extraction failed - check selectors")
            if not metadata.get('tags'):
                print("⚠️  Tags extraction failed - check selectors")
            if not metadata.get('related_videos'):
                print("⚠️  Related videos extraction failed - check selectors")
        else:
            print("❌ Metadata extraction completely failed")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_extraction()
