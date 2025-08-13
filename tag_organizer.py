#!/usr/bin/env python3
"""
Tag and Model Organizer Script
Reads tag/model URLs from list_tag.txt, crawls each page to find videos,
and creates organized folders with symlinks to videos in a user-selected folder.
"""

import os
import re
import glob
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def select_video_folder():
    """Let user select the video folder to search for files"""
    print("Please select the video folder:")
    print("1. Current directory (./)")
    print("2. Custom folder")
    
    while True:
        choice = input("Enter your choice (1-2): ").strip()
        
        if choice == "1":
            folder = "./"
        elif choice == "2":
            folder = input("Enter the custom folder path: ").strip()
        else:
            print("Invalid choice. Please enter 1 or 2.")
            continue
        
        # Convert to absolute path
        folder = os.path.abspath(folder)
        
        if os.path.exists(folder) and os.path.isdir(folder):
            log_with_timestamp(f"Selected video folder: {folder}")
            return folder
        else:
            print(f"Folder '{folder}' does not exist. Please try again.")

def setup_driver():
    """Setup Chrome driver for web scraping"""
    try:
        log_with_timestamp("Setting up Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        log_with_timestamp("✅ Chrome driver ready")
        return driver
        
    except Exception as e:
        log_with_timestamp(f"❌ Error setting up Chrome driver: {e}")
        return None

def crawl_tag_model_page(driver, url):
    """Crawl a single tag/model page to extract video titles"""
    try:
        log_with_timestamp(f"🔍 Crawling: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Wait for dynamic content to load (in case videos are loaded via JavaScript)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.videoBlock"))
            )
            # Give it a bit more time for all videos to load
            time.sleep(2)
        except:
            log_with_timestamp("   ⚠️ Timeout waiting for videoBlock elements, proceeding anyway")
        
        all_video_titles = []
        
        # Extract videos from current page
        def extract_videos_from_current_page():
            video_titles = []
            
            # Use the most specific selector that works for this site
            selector = "div.videoBlock h3 a"
            
            try:
                # First, let's see how many videoBlock divs exist total
                all_video_blocks = driver.find_elements(By.CSS_SELECTOR, "div.videoBlock")
                log_with_timestamp(f"   Found {len(all_video_blocks)} total videoBlock elements on page")
                
                # Now find the h3 a elements within those blocks
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                log_with_timestamp(f"   Trying selector '{selector}': found {len(elements)} elements")
                
                if len(elements) != len(all_video_blocks):
                    log_with_timestamp(f"   ⚠️ Mismatch: {len(all_video_blocks)} videoBlocks but only {len(elements)} h3 a elements")
                
                for i, element in enumerate(elements):
                    log_with_timestamp(f"     Processing element {i+1}/{len(elements)}...")
                    try:
                        # Get all possible title sources for debugging
                        text_content = element.text.strip() if element.text else ""
                        title_attr = element.get_attribute("title") if element.get_attribute("title") else ""
                        alt_attr = element.get_attribute("alt") if element.get_attribute("alt") else ""
                        href_attr = element.get_attribute("href") if element.get_attribute("href") else ""
                        
                        log_with_timestamp(f"       text='{text_content}', title='{title_attr}', alt='{alt_attr}', href='{href_attr}'")
                        
                        # Get title from text content first (most reliable)
                        title = text_content
                        if not title:
                            title = title_attr
                        if not title:
                            title = alt_attr
                        
                        # If still no title, try to extract from href as fallback
                        if not title and href_attr:
                            try:
                                # Extract title from URL like "/updates/adara-jordin-living-doll-training"
                                url_parts = href_attr.split('/')
                                if len(url_parts) > 0:
                                    url_title = url_parts[-1]  # Get the last part
                                    # Convert URL slug to title
                                    title = url_title.replace('-', ' ').replace('_', ' ').title()
                                    log_with_timestamp(f"       Extracted title from URL: '{title}'")
                            except:
                                pass
                        
                        log_with_timestamp(f"       Final title selected: '{title}'")
                        
                        if title and len(title) > 3:  # Skip very short titles
                            video_titles.append(title.strip())
                            log_with_timestamp(f"     ✅ Video {len(video_titles)}: '{title.strip()}'")
                        else:
                            log_with_timestamp(f"     ❌ Element {i+1}: Title too short or empty: '{title}'")
                            
                    except Exception as e:
                        log_with_timestamp(f"     ❌ Error processing element {i+1}: {e}")
                        import traceback
                        log_with_timestamp(f"     Full error: {traceback.format_exc()}")
                        continue
                
                log_with_timestamp(f"   ✅ Successfully extracted {len(video_titles)} videos with selector: {selector}")
                log_with_timestamp(f"   📋 Video titles: {video_titles}")
                
            except Exception as e:
                log_with_timestamp(f"   ❌ Error with selector '{selector}': {e}")
                import traceback
                log_with_timestamp(f"   Full error: {traceback.format_exc()}")
            
            return video_titles
        
        # Extract videos from the first page
        page_videos = extract_videos_from_current_page()
        all_video_titles.extend(page_videos)
        log_with_timestamp(f"   Page 1: Found {len(page_videos)} videos")
        
        # Check for pagination and crawl additional pages
        try:
            # Look for pagination in multiple ways
            pagination_selectors = [
                "div.pagination a",
                ".pagination a", 
                "nav.pagination a",
                ".page-numbers a",
                ".paging a",
                ".page-nav a",
                "a[href*='page=']",
                "a[href*='?page=']"
            ]
            
            last_page = 1
            pagination_found = False
            
            # Try to find the highest page number from visible pagination
            for selector in pagination_selectors:
                try:
                    page_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    if page_links:
                        log_with_timestamp(f"   Checking pagination with selector: {selector}")
                        for link in page_links:
                            # Check link text for page numbers
                            text = link.text.strip()
                            if text.isdigit():
                                last_page = max(last_page, int(text))
                                pagination_found = True
                            
                            # Also check href for page numbers to find the real last page
                            href = link.get_attribute("href") or ""
                            if "page=" in href:
                                try:
                                    page_match = re.search(r'page=(\d+)', href)
                                    if page_match:
                                        page_num = int(page_match.group(1))
                                        last_page = max(last_page, page_num)
                                        pagination_found = True
                                except:
                                    pass
                        
                        if pagination_found:
                            break
                            
                except Exception as e:
                    log_with_timestamp(f"   ⚠️ Error checking pagination selector '{selector}': {e}")
                    continue
            
            # Enhanced pagination detection - probe for actual last page
            if pagination_found:
                log_with_timestamp(f"   🔍 Found pagination, last visible page: {last_page}. Probing for actual last page...")
                
                # Probe beyond the visible last page to find the real last page
                probe_page = last_page + 1
                max_probe = last_page + 20  # Don't probe too far
                actual_last_page = last_page
                
                while probe_page <= max_probe:
                    probe_urls = [
                        f"{url}?page={probe_page}",
                        f"{url}/page/{probe_page}",
                        f"{url}&page={probe_page}" if "?" in url else f"{url}?page={probe_page}"
                    ]
                    
                    page_found = False
                    for probe_url in probe_urls:
                        try:
                            log_with_timestamp(f"   🔍 Probing page {probe_page}: {probe_url}")
                            driver.get(probe_url)
                            time.sleep(1)
                            
                            # Check if this page has videos using the same logic as main extraction
                            test_videos = []
                            try:
                                elements = driver.find_elements(By.CSS_SELECTOR, "div.videoBlock h3 a")
                                test_videos = [elem.text.strip() for elem in elements if elem.text.strip() and len(elem.text.strip()) > 3]
                            except:
                                pass
                            
                            if test_videos:
                                actual_last_page = probe_page
                                page_found = True
                                log_with_timestamp(f"   ✅ Page {probe_page} exists with {len(test_videos)} videos")
                                break
                            else:
                                # Check if we get a 404 or empty page
                                page_title = driver.title.lower()
                                if "404" in page_title or "not found" in page_title or "error" in page_title:
                                    log_with_timestamp(f"   ❌ Page {probe_page} returned 404/error")
                                    break
                                else:
                                    log_with_timestamp(f"   ⚠️ Page {probe_page} exists but has no videos")
                                    break
                                
                        except Exception as e:
                            log_with_timestamp(f"   ⚠️ Error probing page {probe_page}: {e}")
                            continue
                    
                    if not page_found:
                        break
                    
                    probe_page += 1
                
                last_page = actual_last_page
                log_with_timestamp(f"   📄 Actual last page determined: {last_page}")
            
            # Try alternative pagination detection if no standard pagination found
            if not pagination_found:
                try:
                    # Check for next/more pages by looking for common pagination patterns
                    next_selectors = ["a[href*='page=2']", "a[href*='?page=2']", ".next", ".more", "a[title*='Next']", "a[title*='next']"]
                    for selector in next_selectors:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            pagination_found = True
                            # Start with conservative estimate and probe for actual last page
                            last_page = 2
                            log_with_timestamp(f"   Found 'Next' pagination indicator with: {selector}")
                            
                            # Probe to find actual last page
                            probe_page = 2
                            max_probe = 50  # Higher limit when we don't know the range
                            
                            while probe_page <= max_probe:
                                probe_urls = [
                                    f"{url}?page={probe_page}",
                                    f"{url}/page/{probe_page}",
                                    f"{url}&page={probe_page}" if "?" in url else f"{url}?page={probe_page}"
                                ]
                                
                                page_found = False
                                for probe_url in probe_urls:
                                    try:
                                        driver.get(probe_url)
                                        time.sleep(1)
                                        
                                        # Check if this page has videos using consistent logic
                                        test_videos = []
                                        try:
                                            elements = driver.find_elements(By.CSS_SELECTOR, "div.videoBlock h3 a")
                                            test_videos = [elem.text.strip() for elem in elements if elem.text.strip() and len(elem.text.strip()) > 3]
                                        except:
                                            pass
                                        
                                        if test_videos:
                                            last_page = probe_page
                                            page_found = True
                                            break
                                        else:
                                            # No videos found, we've reached the end
                                            break
                                            
                                    except Exception:
                                        continue
                                
                                if not page_found:
                                    break
                                
                                probe_page += 1
                                
                                # Safety check - if we're finding too many pages, something might be wrong
                                if probe_page > 100:
                                    log_with_timestamp(f"   ⚠️ Safety limit reached at page {probe_page}, stopping probe")
                                    break
                            
                            log_with_timestamp(f"   📄 Probed pagination: found {last_page} total pages")
                            break
                except:
                    pass
            
            # Crawl additional pages if pagination exists
            if pagination_found and last_page > 1:
                log_with_timestamp(f"   📄 Found pagination: crawling pages 2 to {last_page}")
                
                # Go back to page 1 to start fresh
                driver.get(url)
                time.sleep(1)
                
                for page_num in range(2, last_page + 1):
                    # Try different URL formats for pagination
                    page_urls = [
                        f"{url}?page={page_num}",
                        f"{url}/page/{page_num}",
                        f"{url}&page={page_num}" if "?" in url else f"{url}?page={page_num}"
                    ]
                    
                    page_success = False
                    for page_url in page_urls:
                        try:
                            log_with_timestamp(f"   🔄 Crawling page {page_num}: {page_url}")
                            driver.get(page_url)
                            time.sleep(2)
                            
                            page_videos = extract_videos_from_current_page()
                            if page_videos:
                                all_video_titles.extend(page_videos)
                                log_with_timestamp(f"   Page {page_num}: Found {len(page_videos)} videos")
                                page_success = True
                                break
                            else:
                                log_with_timestamp(f"   Page {page_num}: No videos found")
                                
                        except Exception as e:
                            log_with_timestamp(f"   ⚠️ Error crawling page {page_num} with URL {page_url}: {e}")
                            continue
                    
                    # If this page failed, continue to next page (don't break the loop)
                    if not page_success:
                        log_with_timestamp(f"   ⚠️ Failed to load page {page_num}, continuing to next page")
            else:
                log_with_timestamp(f"   📄 No pagination detected - single page only")
        
        except Exception as e:
            log_with_timestamp(f"   ⚠️ Error during pagination handling: {e}")
        
        # Remove duplicates while preserving order
        unique_titles = []
        seen = set()
        for title in all_video_titles:
            if title not in seen:
                unique_titles.append(title)
                seen.add(title)
        
        log_with_timestamp(f"   ✅ Total videos found across all pages: {len(unique_titles)}")
        return unique_titles
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error crawling {url}: {e}")
        return []
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
    
    # Try partial matching
    for video_key, video_path in video_files.items():
        # Check if title words are in video filename
        title_words = title_normalized.split()
        video_words = video_key.split()
        
        # If most title words are in video filename, consider it a match
        matching_words = sum(1 for word in title_words if word in video_key)
        if len(title_words) > 0 and matching_words / len(title_words) >= 0.7:
            return video_path
        
        # Also check reverse - if most video words are in title
        matching_words = sum(1 for word in video_words if word in title_normalized)
        if len(video_words) > 0 and matching_words / len(video_words) >= 0.7:
            return video_path
    
    return None

def get_video_files(video_folder):
    log_with_timestamp(f"Scanning video folder: {video_folder}")
    
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    video_files = {}
    
    for ext in video_extensions:
        pattern = os.path.join(video_folder, f"*{ext}")
        files = glob.glob(pattern, recursive=False)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]
            normalized_name = normalize_title_for_matching(name_without_ext)
            video_files[normalized_name] = file_path
    
    log_with_timestamp(f"Found {len(video_files)} video files")
    return video_files

def extract_tag_name_from_url(url):
    """Extract tag/model name from URL"""
    try:
        # Remove domain and get the path
        if '/tags/' in url:
            tag_name = url.split('/tags/')[-1].rstrip('/')
        elif '/models/' in url:
            tag_name = url.split('/models/')[-1].rstrip('/')
        else:
            # Fallback - use last part of URL
            tag_name = url.rstrip('/').split('/')[-1]
        
        # Clean up the tag name
        tag_name = tag_name.replace('-', ' ').replace('_', ' ')
        tag_name = re.sub(r'[^\w\s]', '', tag_name)
        tag_name = ' '.join(tag_name.split())  # Normalize whitespace
        
        return tag_name.title() if tag_name else "Unknown"
        
    except Exception as e:
        log_with_timestamp(f"Error extracting tag name from {url}: {e}")
        return "Unknown"

def download_model_image(url, folder_path):
    """Download model preview image for model folders only"""
    try:
        # Only download images for model folders
        if '/models/' not in url:
            return False
            
        log_with_timestamp(f"   🖼️ Downloading model image from {url}")
        
        # Create a new webdriver instance for image downloading
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        try:
            driver.get(url)
            time.sleep(3)  # Wait for page to load
            
            # Look for model image using the provided HTML structure
            img_selectors = [
                '.modelPic img',  # From your example
                '.modelBlock img',  # Alternative from your example
                'img[alt*="model"]',  # Images with "model" in alt text
                '.performer-image img',  # Common performer image class
                '.model-photo img',  # Another common pattern
                'img[src*="performer"]',  # Images with "performer" in src
                'img[src*="model"]'  # Images with "model" in src
            ]
            
            for selector in img_selectors:
                try:
                    img_element = driver.find_element(By.CSS_SELECTOR, selector)
                    img_url = img_element.get_attribute('src')
                    
                    if img_url and img_url.startswith(('http', '//')):
                        # Ensure full URL
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            # Relative URL - build full URL
                            base_url = url.split('/models/')[0] if '/models/' in url else url.rsplit('/', 1)[0]
                            img_url = base_url + img_url
                        
                        # Download the image
                        response = requests.get(img_url, timeout=10)
                        if response.status_code == 200:
                            img_path = os.path.join(folder_path, 'folder.jpg')
                            with open(img_path, 'wb') as f:
                                f.write(response.content)
                            log_with_timestamp(f"   ✅ Model image saved: folder.jpg")
                            return True
                        
                except Exception as selector_error:
                    continue  # Try next selector
            
            log_with_timestamp(f"   ⚠️ No model image found with standard selectors")
            return False
            
        finally:
            driver.quit()
            
    except Exception as e:
        log_with_timestamp(f"   ❌ Error downloading model image: {e}")
        return False

def create_video_nfo_with_tags(video_path, tags_list):
    """Create NFO file for video with extracted tags"""
    try:
        if not tags_list:
            return False
            
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        nfo_path = os.path.join(video_dir, f"{video_name}.nfo")
        
        # Create basic NFO content with tags
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>{video_name}</title>
    <plot>Video with tags: {', '.join(tags_list)}</plot>
"""
        
        # Add each tag
        for tag in tags_list:
            nfo_content += f"    <tag>{tag}</tag>\n"
            nfo_content += f"    <genre>{tag}</genre>\n"
        
        nfo_content += "</movie>"
        
        # Write NFO file
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
            
        log_with_timestamp(f"   📝 Created NFO with {len(tags_list)} tags: {os.path.basename(nfo_path)}")
        return True
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error creating NFO file: {e}")
        return False

def create_video_nfo_files_with_tags(video_files, tags_folder):
    """Create NFO files for videos based on which tag folders they appear in"""
    try:
        video_tags_map = {}  # Map video real path to list of tags
        
        # Walk through all tag folders to build video->tags mapping
        for root, dirs, files in os.walk(tags_folder):
            if root == tags_folder:  # Skip root tags folder
                continue
                
            # Extract tag/model name from folder path
            folder_name = os.path.basename(root)
            
            # Skip certain folders
            if folder_name in ['No Tag', 'source']:
                continue
            
            # Clean up folder name to get tag name
            if folder_name.startswith('tag '):
                tag_name = folder_name[4:]  # Remove 'tag ' prefix
            elif folder_name.startswith('model '):
                tag_name = folder_name[6:]  # Remove 'model ' prefix
            else:
                tag_name = folder_name
            
            # Find all video files in this tag folder
            for file in files:
                if file.endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v')):
                    file_path = os.path.join(root, file)
                    
                    # Get the real path (target of symlink)
                    try:
                        real_path = os.path.realpath(file_path)
                        
                        if real_path not in video_tags_map:
                            video_tags_map[real_path] = []
                        
                        if tag_name not in video_tags_map[real_path]:
                            video_tags_map[real_path].append(tag_name)
                            
                    except Exception as e:
                        continue
        
        # Create NFO files for videos that have tags
        nfo_count = 0
        for real_path, tags_list in video_tags_map.items():
            if len(tags_list) > 0:
                if create_video_nfo_with_tags(real_path, tags_list):
                    nfo_count += 1
        
        log_with_timestamp(f"   ✅ Created {nfo_count} NFO files with tag metadata")
        return nfo_count
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error creating video NFO files: {e}")
        return 0

def create_source_aware_symlink(target_path, tag_folder, video_files_dict):
    """Create symlink with source folder awareness to handle conflicts"""
    
    # Get the source folder name from the target path
    source_folder = os.path.basename(os.path.dirname(target_path))
    original_filename = os.path.basename(target_path)
    filename_without_ext = os.path.splitext(original_filename)[0]
    file_extension = os.path.splitext(original_filename)[1]
    
    # First, try the original filename
    link_path = os.path.join(tag_folder, original_filename)
    
    # Check if a link with this name already exists and points to a different file
    if os.path.exists(link_path) or os.path.islink(link_path):
        try:
            existing_target = os.path.realpath(link_path)
            current_target = os.path.realpath(target_path)
            
            # If it's the same file, no need to create another link
            if existing_target == current_target:
                return True, "already_exists"
            
            # Different file with same name - add source folder to filename
            source_aware_filename = f"{filename_without_ext} ({source_folder}){file_extension}"
            link_path = os.path.join(tag_folder, source_aware_filename)
            
            # If the source-aware filename also exists, check if it's the same file
            if os.path.exists(link_path) or os.path.islink(link_path):
                existing_source_target = os.path.realpath(link_path)
                if existing_source_target == current_target:
                    return True, "already_exists"
                    
                # Still a conflict - add a counter
                counter = 2
                while True:
                    counter_filename = f"{filename_without_ext} ({source_folder})_{counter}{file_extension}"
                    counter_link_path = os.path.join(tag_folder, counter_filename)
                    
                    if not (os.path.exists(counter_link_path) or os.path.islink(counter_link_path)):
                        link_path = counter_link_path
                        break
                    
                    counter_target = os.path.realpath(counter_link_path)
                    if counter_target == current_target:
                        return True, "already_exists"
                    
                    counter += 1
                    if counter > 10:  # Safety limit
                        break
            
        except (OSError, IOError):
            # If we can't read the existing link, create source-aware name anyway
            source_aware_filename = f"{filename_without_ext} ({source_folder}){file_extension}"
            link_path = os.path.join(tag_folder, source_aware_filename)
    
    # Create the symlink
    return create_symlink_safe(target_path, link_path)

def create_symlink_safe(target_path, link_path):
    """Create symlink with error handling and fallback to hard link"""
    try:
        # Remove existing link if it exists
        if os.path.exists(link_path) or os.path.islink(link_path):
            os.remove(link_path)
        
        # Calculate relative path from link to target for portability
        relative_target = os.path.relpath(target_path, os.path.dirname(link_path))
        
        # Try creating symlink first
        try:
            os.symlink(relative_target, link_path)
            return True, "symlink"
        except OSError:
            # Fallback to hard link for NTFS/Windows compatibility
            log_with_timestamp("❌ Symlink creation failed")
                
    except Exception as e:
        log_with_timestamp(f"   ❌ Error creating link: {e}")
        return False, "error"

def main():
    """Main function to organize videos by tags/models"""
    log_with_timestamp("🏷️ Starting Tag and Model Organizer")
    
    # Check if list_tag.txt exists
    if not os.path.exists('list_tag.txt'):
        log_with_timestamp("❌ list_tag.txt not found!")
        log_with_timestamp("Please run sitemap_tag_parser.py first to generate the tag/model URLs.")
        return False
    
    # Select video folder
    video_folder = select_video_folder()
    
    # Get all video files from the selected folder
    video_files = get_video_files(video_folder)
    
    if not video_files:
        log_with_timestamp("❌ No video files found in the selected folder!")
        return False
    
    # Setup web driver
    driver = setup_driver()
    if not driver:
        log_with_timestamp("❌ Failed to setup web driver!")
        return False
    
    try:
        # Read tag/model URLs from list_tag.txt
        log_with_timestamp("📖 Reading tag/model URLs from list_tag.txt...")
        
        with open('list_tag.txt', 'r', encoding='utf-8') as f:
            tag_model_urls = [line.strip() for line in f if line.strip()]
        
        log_with_timestamp(f"Found {len(tag_model_urls)} tag/model URLs to process")
        
        # Create tags folder
        tags_folder = "./tags"
        os.makedirs(tags_folder, exist_ok=True)
        
        # Statistics
        total_processed = 0
        total_videos_found = 0
        total_links_created = 0
        unmatched_videos = []
        
        # Process each tag/model URL
        for i, url in enumerate(tag_model_urls, 1):
            log_with_timestamp(f"🔄 Processing {i}/{len(tag_model_urls)}: {url}")
            
            # Extract tag/model name from URL
            tag_name = extract_tag_name_from_url(url)
            
            # Crawl the page to find videos
            video_titles = crawl_tag_model_page(driver, url)
            
            if not video_titles:
                log_with_timestamp(f"   ⚠️ No videos found for {tag_name}")
                total_processed += 1
                continue
            
            total_videos_found += len(video_titles)
            
            # Create tag folder
            tag_folder = os.path.join(tags_folder, tag_name)
            os.makedirs(tag_folder, exist_ok=True)
            
            # Download model image (only for model folders, not tag folders)
            if '/models/' in url:
                download_model_image(url, tag_folder)
            
            # Match videos to files and create links
            matched_count = 0
            for video_title in video_titles:
                matching_file = find_matching_video(video_title, video_files)
                
                if matching_file:
                    # Create source-aware symlink/hardlink to handle conflicts
                    success, link_type = create_source_aware_symlink(matching_file, tag_folder, video_files)
                    if success:
                        matched_count += 1
                        total_links_created += 1
                        if link_type not in ["already_exists"]:
                            source_folder = os.path.basename(os.path.dirname(matching_file))
                            log_with_timestamp(f"     📁 Linked: {os.path.basename(matching_file)} from {source_folder}")
                else:
                    unmatched_videos.append((tag_name, video_title))
            
            log_with_timestamp(f"   ✅ {tag_name}: {matched_count}/{len(video_titles)} videos linked")
            total_processed += 1
        
        # Create "No Tag" folder for unlinked videos
        log_with_timestamp("🔍 Creating 'No Tag' folder for unlinked videos...")
        no_tag_folder = os.path.join(tags_folder, "No Tag")
        os.makedirs(no_tag_folder, exist_ok=True)
        
        # Find videos that weren't linked to any tag
        linked_files = set()
        for root, dirs, files in os.walk(tags_folder):
            if root != no_tag_folder:  # Skip the "No Tag" folder itself
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.islink(file_path) or os.path.isfile(file_path):
                        try:
                            real_path = os.path.realpath(file_path)
                            linked_files.add(real_path)
                        except:
                            pass
        
        no_tag_count = 0
        for video_path in video_files.values():
            real_video_path = os.path.realpath(video_path)
            if real_video_path not in linked_files:
                # Use source-aware linking for "No Tag" folder too
                success, link_type = create_source_aware_symlink(video_path, no_tag_folder, video_files)
                if success and link_type not in ["already_exists"]:
                    no_tag_count += 1
        
        log_with_timestamp(f"   ✅ Added {no_tag_count} untagged videos to 'No Tag' folder")
        
        # Optional: Create NFO files with tags for videos (for Jellyfin filtering)
        log_with_timestamp("🏷️ Creating NFO files with tags for Jellyfin filtering...")
        create_video_nfo_files_with_tags(video_files, tags_folder)
        
        # Summary
        log_with_timestamp("📊 Summary:")
        log_with_timestamp(f"   • Processed {total_processed} tags/models")
        log_with_timestamp(f"   • Found {total_videos_found} videos on tag/model pages")
        log_with_timestamp(f"   • Created {total_links_created} video links")
        log_with_timestamp(f"   • Added {no_tag_count} videos to 'No Tag' folder")
        log_with_timestamp(f"   • {len(unmatched_videos)} videos couldn't be matched to files")
        
        if unmatched_videos:
            log_with_timestamp("⚠️ Unmatched videos (first 10):")
            for tag, title in unmatched_videos[:10]:
                log_with_timestamp(f"   • {tag}: {title}")
        
        log_with_timestamp("✅ Tag organization completed successfully!")
        return True
        
    except Exception as e:
        log_with_timestamp(f"❌ Error during tag organization: {e}")
        return False
        
    finally:
        driver.quit()
        log_with_timestamp("🔚 Chrome driver closed")

if __name__ == "__main__":
    main()
