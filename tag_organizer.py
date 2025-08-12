#!/usr/bin/env python3
"""
Tag and Model Organizer Script
Processes tag and model pages to create organized folders with symlinks to videos.
Handles pagination and case        log_with_timestamp(f"Found {len(video_titles)} video titles on page")
        
        # Debug: show ALL titles found
        if video_titles:
            log_with_timestamp("All titles found on this page:")
            for i, title in enumerate(video_titles):
                log_with_timestamp(f"  {i+1:3d}. '{title}'")
        else:tive matching.
"""

import os
import sys
import time
import re
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urljoin

def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def setup_headless_browser():
    """Setup headless Chrome browser for scraping"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        return driver
    except Exception as e:
        log_with_timestamp(f"Error setting up browser: {e}")
        return None

def normalize_title_for_matching(title):
    """Normalize title for better matching"""
    # Convert to lowercase
    normalized = title.lower()
    
    # Remove common punctuation and replace with spaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Strip leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized

def find_matching_video(title, video_files):
    """Find matching video file with fuzzy matching"""
    title_normalized = normalize_title_for_matching(title)
    
    # Direct match first
    if title_normalized in video_files:
        return video_files[title_normalized]
    
    # Try variations
    for video_key, video_filename in video_files.items():
        video_normalized = normalize_title_for_matching(video_key)
        
        # Check if titles match after normalization
        if title_normalized == video_normalized:
            return video_filename
        
        # Check if one contains the other (for partial matches)
        if len(title_normalized) > 5 and len(video_normalized) > 5:
            if title_normalized in video_normalized or video_normalized in title_normalized:
                return video_filename
    
    return None

def get_video_files():
    """Get all video files from ./videos/ directory with normalized mapping"""
    videos_dir = "./videos"
    video_files = {}  # normalized_title -> actual_filename
    
    if not os.path.exists(videos_dir):
        log_with_timestamp("./videos/ directory not found!")
        return video_files
    
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    try:
        for file in os.listdir(videos_dir):
            if os.path.isfile(os.path.join(videos_dir, file)):
                for ext in video_extensions:
                    if file.lower().endswith(ext.lower()):
                        # Extract filename without extension and normalize for matching
                        title_without_ext = os.path.splitext(file)[0]
                        normalized_title = normalize_title_for_matching(title_without_ext)
                        video_files[normalized_title] = file
                        break
        
        log_with_timestamp(f"Found {len(video_files)} video files in ./videos/")
        return video_files
        
    except Exception as e:
        log_with_timestamp(f"Error reading videos directory: {e}")
        return video_files

def clean_folder_name(name):
    """Clean folder name by removing invalid characters"""
    # Replace invalid characters for folder names
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    # Replace multiple underscores with single one
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores and spaces
    name = name.strip('_ ')
    
    return name

def extract_video_titles_from_page(driver, url):
    """Extract video titles from a single page"""
    video_titles = []
    
    try:
        log_with_timestamp(f"Extracting video titles from: {url}")
        driver.get(url)
        time.sleep(3)  # Give page time to load
        
        # Try multiple selectors to find video titles
        selectors_to_try = [
            "div.videoBlock h3 a",         # Most specific - titles are in anchor tags inside h3
            "div.videoBlock h3",           # Fallback - h3 elements themselves
            ".videoBlock h3 a",            # Without div prefix
            ".videoBlock h3",              # Without div prefix, no anchor
        ]
        
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    log_with_timestamp(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Get text from the element - try multiple methods
                            title = element.text.strip()
                            
                            # If element.text is empty (common for non-displayed elements), try other methods
                            if not title:
                                title = element.get_attribute("textContent")
                                if title:
                                    title = title.strip()
                                    
                            if not title:
                                title = element.get_attribute("innerText")
                                if title:
                                    title = title.strip()
                            
                            if title:
                                # Decode HTML entities
                                import html
                                title = html.unescape(title)
                                if title not in video_titles:
                                    video_titles.append(title)
                                
                        except Exception as e:
                            continue
                    
                    # If we found titles with this selector, use them and stop trying other selectors
                    if video_titles:
                        log_with_timestamp(f"Successfully extracted {len(video_titles)} titles from selector: {selector}")
                        break
                        
            except Exception as e:
                continue
        
        log_with_timestamp(f"Found {len(video_titles)} video titles on page")
        
        # Debug: show ALL titles found
        if video_titles:
            log_with_timestamp("All titles found on this page:")
            for i, title in enumerate(video_titles):
                log_with_timestamp(f"  {i+1:3d}. '{title}'")
        else:
            log_with_timestamp("WARNING: No video titles found on this page!")
            # Additional debugging
            try:
                # Check if we can find any videoBlock elements
                video_blocks = driver.find_elements(By.CSS_SELECTOR, "div.videoBlock")
                log_with_timestamp(f"Found {len(video_blocks)} videoBlock elements")
                
                if video_blocks:
                    # Try to see what's in the first block
                    first_block = video_blocks[0]
                    h3_elements = first_block.find_elements(By.TAG_NAME, "h3")
                    log_with_timestamp(f"Found {len(h3_elements)} h3 elements in first block")
                    
                    if h3_elements:
                        h3_text = h3_elements[0].text.strip()
                        log_with_timestamp(f"First h3 text: '{h3_text}'")
                        
                        # Check for anchor tags
                        a_elements = h3_elements[0].find_elements(By.TAG_NAME, "a")
                        if a_elements:
                            a_text = a_elements[0].text.strip()
                            log_with_timestamp(f"First anchor text: '{a_text}'")
                
            except Exception as debug_e:
                log_with_timestamp(f"Debug error: {debug_e}")
        
        return video_titles
        
    except Exception as e:
        log_with_timestamp(f"Error extracting titles from {url}: {e}")
        return video_titles

def get_pagination_urls(driver, base_url):
    """Get all pagination URLs for a tag/model page"""
    pagination_urls = [base_url]  # Always include the first page
    
    try:
        # Find pagination div
        pagination_div = driver.find_element(By.CSS_SELECTOR, "div.pagination")
        
        # Find all pagination links
        pagination_links = pagination_div.find_elements(By.CSS_SELECTOR, "a")
        
        for link in pagination_links:
            try:
                href = link.get_attribute("href")
                if href and href != "#" and "page=" in href:
                    # Only add if it's a valid pagination URL and not already in list
                    if href not in pagination_urls:
                        pagination_urls.append(href)
            except Exception as e:
                continue
        
        # Sort pagination URLs by page number
        def get_page_number(url):
            try:
                if "page=" in url:
                    return int(url.split("page=")[1].split("&")[0])
                return 1
            except:
                return 1
        
        pagination_urls.sort(key=get_page_number)
        log_with_timestamp(f"Found {len(pagination_urls)} pages for {base_url}")
        return pagination_urls
        
    except Exception as e:
        log_with_timestamp(f"No pagination found for {base_url} (single page)")
        return pagination_urls

def extract_all_video_titles(driver, base_url):
    """Extract video titles from all pages of a tag/model"""
    all_titles = []
    
    # First, visit the base URL to get pagination info
    driver.get(base_url)
    time.sleep(2)
    
    # Get all pagination URLs
    pagination_urls = get_pagination_urls(driver, base_url)
    
    # Extract titles from each page
    for url in pagination_urls:
        titles = extract_video_titles_from_page(driver, url)
        all_titles.extend(titles)
        time.sleep(1)
    
    # Remove duplicates while preserving order
    unique_titles = []
    seen = set()
    for title in all_titles:
        title_lower = title.lower()
        if title_lower not in seen:
            unique_titles.append(title)
            seen.add(title_lower)
    
    log_with_timestamp(f"Total unique video titles found: {len(unique_titles)}")
    return unique_titles

def debug_matching(video_titles, video_files):
    """Debug function to show matching issues"""
    log_with_timestamp("=== DEBUG: Video Title Matching ===")
    log_with_timestamp(f"Found {len(video_titles)} titles from web, {len(video_files)} video files")
    
    # Show first few web titles
    log_with_timestamp("Web titles (first 5):")
    for i, title in enumerate(video_titles[:5]):
        normalized = normalize_title_for_matching(title)
        log_with_timestamp(f"  {i+1}. '{title}' -> normalized: '{normalized}'")
    
    # Show first few video files
    log_with_timestamp("Video files (first 5):")
    for i, (key, filename) in enumerate(list(video_files.items())[:5]):
        log_with_timestamp(f"  {i+1}. '{key}' -> '{filename}'")
    
    # Check for matches using new matching function
    matches = []
    for title in video_titles[:5]:  # Check first 5 for debugging
        matched_file = find_matching_video(title, video_files)
        if matched_file:
            matches.append((title, matched_file))
    
    log_with_timestamp(f"Matches found: {len(matches)}")
    for title, filename in matches:
        log_with_timestamp(f"  MATCH: '{title}' -> '{filename}'")
    log_with_timestamp("=== END DEBUG ===")

def create_symlinks(folder_path, video_titles, video_files, debug=False):
    """Create symlinks for matching videos in the specified folder"""
    # Don't create folder if no videos found
    if not video_titles:
        log_with_timestamp("No video titles provided - skipping folder creation")
        return 0
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        log_with_timestamp(f"Created folder: {folder_path}")
    
    # Add debug info for first folder processed
    if debug:
        debug_matching(video_titles, video_files)
    
    symlinks_created = 0
    
    for title in video_titles:
        # Use improved matching function
        matched_filename = find_matching_video(title, video_files)
        
        if matched_filename:
            # Use absolute paths for better compatibility
            source_abs_path = os.path.abspath(os.path.join("./videos", matched_filename))
            symlink_path = os.path.join(folder_path, matched_filename)
            
            # Create symlink if it doesn't exist
            if not os.path.exists(symlink_path):
                success = False
                
                # Method 1: Standard Unix symlink with absolute path
                try:
                    os.symlink(source_abs_path, symlink_path)
                    log_with_timestamp(f"Created symlink: {matched_filename}")
                    symlinks_created += 1
                    success = True
                except OSError:
                    pass
                
                if not success:
                    # Method 2: Relative symlink
                    try:
                        rel_path = os.path.relpath(source_abs_path, os.path.dirname(symlink_path))
                        os.symlink(rel_path, symlink_path)
                        log_with_timestamp(f"Created relative symlink: {matched_filename}")
                        symlinks_created += 1
                        success = True
                    except OSError:
                        pass
                
                if not success:
                    # Method 3: Hard link (same filesystem only)
                    try:
                        os.link(source_abs_path, symlink_path)
                        log_with_timestamp(f"Created hard link: {matched_filename}")
                        symlinks_created += 1
                        success = True
                    except OSError:
                        log_with_timestamp(f"All symlink methods failed for {matched_filename}")
            else:
                log_with_timestamp(f"Link already exists: {matched_filename}")
        else:
            # Debug: Show what we're looking for vs what we have
            if debug:
                log_with_timestamp(f"No match found for title: '{title}'")
                # Show what normalized version we're looking for
                normalized = normalize_title_for_matching(title)
                log_with_timestamp(f"  Normalized: '{normalized}'")
    
    log_with_timestamp(f"Created {symlinks_created} links in {folder_path}")
    
    # If no symlinks were created, remove the empty folder
    if symlinks_created == 0:
        try:
            os.rmdir(folder_path)
            log_with_timestamp(f"Removed empty folder: {folder_path}")
        except:
            pass
    
    return symlinks_created

def process_tag_or_model_page(driver, url, video_files, cached_titles=None, debug=False):
    """Process a single tag or model page"""
    try:
        # Determine if it's a tag or model
        if "/tags/" in url:
            folder_prefix = "tag "
            tag_name = url.split("/tags/")[1].split("?")[0]  # Remove query params
        elif "/models/" in url:
            folder_prefix = "model "
            tag_name = url.split("/models/")[1].split("?")[0]  # Remove query params
        else:
            log_with_timestamp(f"Unknown URL type: {url}")
            return 0
        
        # Clean and create folder name
        clean_tag_name = clean_folder_name(tag_name.replace("-", " ").title())
        folder_name = folder_prefix + clean_tag_name
        folder_path = os.path.join("./tags", folder_name)
        
        log_with_timestamp(f"Processing: {folder_name}")
        
        # Use cached titles if provided, otherwise extract them
        if cached_titles is not None:
            video_titles = cached_titles
            log_with_timestamp(f"Using cached titles: {len(video_titles)} videos")
        else:
            # Extract all video titles from all pages
            video_titles = extract_all_video_titles(driver, url)
        
        if not video_titles:
            log_with_timestamp(f"No video titles found for {url} - skipping folder creation")
            return 0
        
        # Create symlinks for matching videos - only creates folder if videos found
        symlinks_created = create_symlinks(folder_path, video_titles, video_files, debug=debug)
        
        if symlinks_created == 0:
            log_with_timestamp(f"No matching videos found for {folder_name}")
        
        return symlinks_created
        
    except Exception as e:
        log_with_timestamp(f"Error processing {url}: {e}")
        return 0

def create_no_tag_folder(video_files, all_tagged_videos):
    """Create 'tag no tag' folder for videos without any tags"""
    no_tag_folder = "./tags/tag no tag"
    
    if not os.path.exists(no_tag_folder):
        os.makedirs(no_tag_folder)
        log_with_timestamp("Created 'tag no tag' folder")
    
    symlinks_created = 0
    
    for normalized_title, video_filename in video_files.items():
        if normalized_title not in all_tagged_videos:
            source_abs_path = os.path.abspath(os.path.join("./videos", video_filename))
            symlink_path = os.path.join(no_tag_folder, video_filename)
            
            if not os.path.exists(symlink_path):
                try:
                    # Try symbolic link with absolute path first
                    os.symlink(source_abs_path, symlink_path)
                    log_with_timestamp(f"Added to 'no tag': {video_filename}")
                    symlinks_created += 1
                except OSError:
                    try:
                        # Fallback to hard link
                        os.link(source_abs_path, symlink_path)
                        log_with_timestamp(f"Added to 'no tag' (hard link): {video_filename}")
                        symlinks_created += 1
                    except OSError:
                        log_with_timestamp(f"Error creating link for {video_filename}")
    
    log_with_timestamp(f"Added {symlinks_created} videos to 'tag no tag' folder")
    return symlinks_created

def create_source_folder(video_files):
    """Create 'source videos' folder containing all videos"""
    # Get the actual folder name of the videos directory
    videos_dir_name = os.path.basename(os.path.abspath("./videos"))
    source_folder = f"./tags/source {videos_dir_name}"
    
    if not os.path.exists(source_folder):
        os.makedirs(source_folder)
        log_with_timestamp(f"Created source folder: {source_folder}")
    
    symlinks_created = 0
    
    for normalized_title, video_filename in video_files.items():
        source_abs_path = os.path.abspath(os.path.join("./videos", video_filename))
        symlink_path = os.path.join(source_folder, video_filename)
        
        if not os.path.exists(symlink_path):
            try:
                # Try symbolic link with absolute path first
                os.symlink(source_abs_path, symlink_path)
                symlinks_created += 1
            except OSError:
                try:
                    # Fallback to hard link
                    os.link(source_abs_path, symlink_path)
                    symlinks_created += 1
                except OSError:
                    log_with_timestamp(f"Error creating link for {video_filename}")
    
    log_with_timestamp(f"Created {symlinks_created} links in source folder")
    return symlinks_created

def main():
    """Main function"""
    log_with_timestamp("Starting tag and model organizer...")
    
    # Check if list_tag.txt exists
    if not os.path.exists("list_tag.txt"):
        log_with_timestamp("list_tag.txt not found in the current directory.")
        sys.exit(1)
    
    # Get all video files
    video_files = get_video_files()
    if not video_files:
        log_with_timestamp("No video files found in ./videos/ directory.")
        sys.exit(1)
    
    # Create tags directory if it doesn't exist
    if not os.path.exists("./tags"):
        os.makedirs("./tags")
        log_with_timestamp("Created ./tags/ directory")
    
    # Setup browser
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("Failed to setup browser")
        sys.exit(1)
    
    # Read tag/model URLs
    with open("list_tag.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    log_with_timestamp(f"Found {len(urls)} tag/model URLs to process")
    
    # Track all tagged videos (for creating 'no tag' folder)
    all_tagged_videos = set()
    total_symlinks = 0
    
    # Cache for video titles to avoid duplicate scraping
    titles_cache = {}
    
    try:
        for i, url in enumerate(urls, 1):
            log_with_timestamp(f"Processing {i}/{len(urls)}: {url}")
            
            # Extract video titles only once per URL
            if url not in titles_cache:
                video_titles = extract_all_video_titles(driver, url)
                titles_cache[url] = video_titles
            else:
                video_titles = titles_cache[url]
                log_with_timestamp(f"Using cached titles for {url}")
            
            # Add to tagged videos set (normalized)
            for title in video_titles:
                all_tagged_videos.add(normalize_title_for_matching(title))
            
            # Process the page using cached titles
            debug_first = (i == 1)  # Debug for first folder only
            symlinks_created = process_tag_or_model_page(driver, url, video_files, video_titles, debug=debug_first)
            total_symlinks += symlinks_created
            
            # Small delay between requests
            time.sleep(1)
            
        # Create 'no tag' folder for untagged videos
        no_tag_symlinks = create_no_tag_folder(video_files, all_tagged_videos)
        total_symlinks += no_tag_symlinks
        
        # Create source folder with all videos
        source_symlinks = create_source_folder(video_files)
        total_symlinks += source_symlinks
        
        log_with_timestamp(f"Processing completed!")
        log_with_timestamp(f"Total symlinks created: {total_symlinks}")
        log_with_timestamp(f"Processed {len(urls)} tag/model pages")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()