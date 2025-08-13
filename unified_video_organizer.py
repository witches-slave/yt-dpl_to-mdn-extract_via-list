#!/usr/bin/env python3
"""
Unified Video Organizer Script
Combines video list processing and organization into a single workflow:
1. Reads video URLs from list_video.txt (created by sitemap_video_parser.py)
2. Extracts comprehensive metadata from each video page (thumbnail, tags, model, description, related videos)
3. Downloads video thumbnails and model images
4. Creates relative symlinks for videos organized by tags and models
5. Generates rich NFO files for each video with all extracted metadata
6. Provides summary of missing videos (found online but not in source folder)
"""

import os
import sys
import time
import requests
from urllib.parse import urlparse, urljoin
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import re
import glob

def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def log_separator():
    """Print a clean separator line without timestamp"""
    print()

def debug_page_structure(driver, video_url):
    """Debug function to print page structure for troubleshooting"""
    try:
        log_with_timestamp(f"🔍 DEBUG: Analyzing page structure for {video_url}")
        
        # Check for common class patterns
        common_classes = ['tags', 'tag', 'model', 'modelName', 'performer', 'categories', 'genre']
        for class_name in common_classes:
            elements = driver.find_elements(By.CSS_SELECTOR, f'[class*="{class_name}"]')
            if elements:
                log_with_timestamp(f"    Found {len(elements)} elements with class containing '{class_name}'")
                for elem in elements[:2]:  # Show first 2
                    try:
                        class_attr = elem.get_attribute("class")
                        tag_name = elem.tag_name
                        text = elem.text.strip()[:100]  # First 100 chars
                        log_with_timestamp(f"      <{tag_name} class='{class_attr}'>{text}...")
                    except:
                        pass
        
        # Check for links that might be tags or models
        links = driver.find_elements(By.TAG_NAME, "a")
        tag_links = [link for link in links if "/tags/" in (link.get_attribute("href") or "")]  # Changed from /tag/ to /tags/
        model_links = [link for link in links if "/model" in (link.get_attribute("href") or "")]
        
        log_with_timestamp(f"    Found {len(tag_links)} links containing '/tags/'")  # Updated message
        log_with_timestamp(f"    Found {len(model_links)} links containing '/model'")
        
        # Show first few tag links
        for link in tag_links[:3]:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                log_with_timestamp(f"      Tag link: '{text}' -> {href}")
            except:
                pass
                
        # Show first few model links  
        for link in model_links[:3]:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                log_with_timestamp(f"      Model link: '{text}' -> {href}")
            except:
                pass
                
    except Exception as e:
        log_with_timestamp(f"    DEBUG: Error analyzing page: {e}")

def get_user_inputs():
    """Get domain and video folder from user"""
    print("=" * 60)
    print("UNIFIED VIDEO ORGANIZER")
    print("=" * 60)
    print()
    
    # Check if list_video.txt exists
    if not os.path.exists("list_video.txt"):
        print("❌ ERROR: list_video.txt not found in the current directory.")
        print("💡 SOLUTION: Run 'python3 sitemap_video_parser.py' first to generate the video list.")
        print("   This script extracts video URLs from the sitemap and creates list_video.txt")
        sys.exit(1)
    
    # Check if list_video.txt is empty
    try:
        with open("list_video.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines:
                print("❌ ERROR: list_video.txt is empty.")
                print("💡 SOLUTION: Run 'python3 sitemap_video_parser.py' to populate the video list.")
                sys.exit(1)
            print(f"✅ Found {len(lines)} video URLs in list_video.txt")
    except Exception as e:
        print(f"❌ ERROR: Could not read list_video.txt: {e}")
        sys.exit(1)
    
    # Get domain
    domain = input("Enter the domain (e.g., https://shinybound.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        sys.exit(1)
    
    # Ensure domain has proper format
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    domain = domain.rstrip('/')
    
    # Get source folder path
    video_folder = input("Enter the source folder path (where your videos are stored): ").strip()
    if not video_folder:
        print("Error: Video folder cannot be empty")
        sys.exit(1)
    
    if not os.path.exists(video_folder):
        print(f"Error: Video folder does not exist: {video_folder}")
        sys.exit(1)
    
    # Get target tags folder (where symlinks will be created)
    organization_folder = input("Enter the tags folder path (where symlinks will be created): ").strip()
    if not organization_folder:
        print("Error: Tags folder cannot be empty")
        sys.exit(1)
    
    # Create tags folder if it doesn't exist
    os.makedirs(organization_folder, exist_ok=True)
    
    # Expand paths
    video_folder = os.path.abspath(video_folder)
    organization_folder = os.path.abspath(organization_folder)
    
    def get_user_inputs():
    """Get domain and video folder from user"""
    print("=" * 60)
    print("UNIFIED VIDEO ORGANIZER")
    print("=" * 60)
    print()
    
    # Check if list_video.txt exists
    if not os.path.exists("list_video.txt"):
        print("❌ ERROR: list_video.txt not found in the current directory.")
        print("💡 SOLUTION: Run 'python3 sitemap_video_parser.py' first to generate the video list.")
        print("   This script extracts video URLs from the sitemap and creates list_video.txt")
        sys.exit(1)
    
    # Check if list_video.txt is empty and parse it
    try:
        video_entries = parse_video_list()
        if not video_entries:
            print("❌ ERROR: list_video.txt is empty or has no valid entries.")
            print("💡 SOLUTION: Run 'python3 sitemap_video_parser.py' to populate the video list.")
            sys.exit(1)
        log_with_timestamp(f"✅ Found {len(video_entries)} video entries in list_video.txt")
    except Exception as e:
        print(f"❌ ERROR: Could not read list_video.txt: {e}")
        sys.exit(1)
    
    # Get domain
    domain = input("Enter the domain (e.g., https://shinybound.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        sys.exit(1)
    
    # Ensure domain has proper format
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    domain = domain.rstrip('/')
    
    # Get source folder path
    video_folder = input("Enter the source folder path (where your videos are stored): ").strip()
    if not video_folder:
        print("Error: Video folder cannot be empty")
        sys.exit(1)
    
    if not os.path.exists(video_folder):
        print(f"Error: Video folder does not exist: {video_folder}")
        sys.exit(1)
    
    # Get target tags folder (where symlinks will be created)
    organization_folder = input("Enter the tags folder path (where symlinks will be created): ").strip()
    if not organization_folder:
        print("Error: Tags folder cannot be empty")
        sys.exit(1)
    
    # Create tags folder if it doesn't exist
    os.makedirs(organization_folder, exist_ok=True)
    
    # Expand paths
    video_folder = os.path.abspath(video_folder)
    organization_folder = os.path.abspath(organization_folder)
    
    print(f"
Domain: {domain}")
    print(f"Source folder: {video_folder}")
    print(f"Tags folder: {organization_folder}")
    print(f"Video entries: {len(video_entries)} videos from list_video.txt")
    print("="*60 + "
")
    
    return domain, video_folder, organization_folder

def parse_video_list(filename='list_video.txt'):
    """Parse list_video.txt file that contains URL|TITLE format"""
    video_entries = []
    
    try:
        with open(filename, "r", encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Check if line contains the new format (URL|TITLE)
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        url, title = parts
                        video_entries.append({
                            'url': url.strip(),
                            'title': title.strip() if title.strip() else None
                        })
                    else:
                        # Malformed line, treat as URL only
                        video_entries.append({
                            'url': line.strip(),
                            'title': None
                        })
                else:
                    # Old format (URL only)
                    video_entries.append({
                        'url': line.strip(),
                        'title': None
                    })
    
    except Exception as e:
        raise Exception(f"Error reading {filename}: {e}")
    
    return video_entries
    print(f"Source folder: {video_folder}")
    print(f"Tags folder: {organization_folder}")
    print(f"Video URLs: {len(lines)} videos from list_video.txt")
    print("="*60 + "\n")
    
    return domain, video_folder, organization_folder

def setup_headless_browser():
    """Setup headless Chrome browser"""
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

# ===== VIDEO URL EXTRACTION =====

def get_pagination_urls(driver, base_url):
    """Get all pagination URLs for updates pages - generates ALL pages from 1 to last"""
    pagination_urls = [base_url]  # Always include the first page
    
    try:
        # Find pagination div/section
        pagination_selectors = [
            "div.pagination",
            ".pagination", 
            "nav.pagination",
            ".page-numbers",
            ".pager",
            ".paginate"
        ]
        
        pagination_div = None
        for selector in pagination_selectors:
            try:
                pagination_div = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue
        
        if pagination_div:
            # Find all pagination links to determine the maximum page number
            pagination_links = pagination_div.find_elements(By.TAG_NAME, "a")
            
            max_page = 1
            page_url_pattern = None
            
            for link in pagination_links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    if href and href != "#":
                        # Try to extract page number from URL
                        page_num = None
                        if "page=" in href:
                            try:
                                page_num = int(href.split("page=")[1].split("&")[0])
                                page_url_pattern = href.replace(f"page={page_num}", "page={}")
                            except:
                                pass
                        elif "/page/" in href:
                            try:
                                page_num = int(href.split("/page/")[1].split("/")[0])
                                page_url_pattern = href.replace(f"/page/{page_num}", "/page/{}")
                            except:
                                pass
                        
                        # Also try to extract page number from link text
                        if text.isdigit():
                            try:
                                text_page_num = int(text)
                                if text_page_num > max_page:
                                    max_page = text_page_num
                                    if not page_url_pattern and href:
                                        # Try to infer pattern from this link
                                        if "page=" in href:
                                            page_url_pattern = href.replace(f"page={text_page_num}", "page={}")
                                        elif "/page/" in href:
                                            page_url_pattern = href.replace(f"/page/{text_page_num}", "/page/{}")
                            except:
                                pass
                        
                        # Update max_page if we found a higher number in URL
                        if page_num and page_num > max_page:
                            max_page = page_num
                            
                except Exception as e:
                    continue
            
            # If we found a pattern and max page, generate all URLs
            if page_url_pattern and max_page > 1:
                log_with_timestamp(f"🔢 Found pagination: pages 1 to {max_page}")
                
                # Generate URLs for all pages from 1 to max_page
                for page_num in range(1, max_page + 1):
                    if page_num == 1:
                        # Page 1 is usually the base URL
                        continue  # Already added above
                    else:
                        page_url = page_url_pattern.format(page_num)
                        pagination_urls.append(page_url)
                
                log_with_timestamp(f"✅ Generated {len(pagination_urls)} pagination URLs (pages 1-{max_page})")
            
            # Fallback: if we couldn't determine pattern, use visible links only
            elif len(pagination_links) > 0:
                log_with_timestamp("⚠️  Could not determine pagination pattern, using visible links only")
                for link in pagination_links:
                    try:
                        href = link.get_attribute("href")
                        if href and href != "#" and href not in pagination_urls:
                            if ("/updates" in href and 
                                ("page=" in href or "/page/" in href)):
                                pagination_urls.append(href)
                    except Exception as e:
                        continue
                
                # Sort fallback URLs by page number
                def get_page_number(url):
                    try:
                        if "page=" in url:
                            return int(url.split("page=")[1].split("&")[0])
                        elif "/page/" in url:
                            return int(url.split("/page/")[1].split("/")[0])
                        return 1
                    except:
                        return 1
                
                pagination_urls.sort(key=get_page_number)
                log_with_timestamp(f"📄 Using {len(pagination_urls)} visible pagination links")
        
        else:
            log_with_timestamp("ℹ️  No pagination found, using single page")
        
        return pagination_urls
        
    except Exception as e:
        log_with_timestamp(f"⚠️  Error finding pagination: {e}")
        return pagination_urls

def extract_video_urls_from_page(driver, domain):
    """Extract individual video page URLs from an updates listing page"""
    video_urls = []
    
    # Try multiple selectors to find video links
    selectors_to_try = [
        "div.videoBlock a[href*='/updates/']",
        ".videoBlock a[href*='/updates/']",
        "a[href*='/updates/']:not([href$='/updates']):not([href$='/updates/'])",
        ".video-link",
        ".update-link",
        "div.update a",
        ".thumbnail a"
    ]
    
    for selector in selectors_to_try:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                log_with_timestamp(f"  Using selector: {selector} (found {len(elements)} elements)")
                
                for element in elements:
                    try:
                        href = element.get_attribute("href")
                        if href and "/updates/" in href:
                            # Make sure it's a full URL
                            if href.startswith("/"):
                                href = domain + href
                            elif not href.startswith("http"):
                                href = urljoin(domain, href)
                            
                            # Avoid duplicate main updates page
                            if not href.endswith(("/updates", "/updates/")):
                                video_urls.append(href)
                    except Exception as e:
                        continue
                break  # Use first working selector
        except Exception as e:
            continue
    
    # Remove duplicates
    unique_urls = list(set(video_urls))
    return unique_urls

def process_videos_from_list(domain, video_folder, organization_folder):
    """Process videos from list_video.txt file"""
    log_with_timestamp("🕷️  Starting video processing from list_video.txt")
    
    # Read video entries from list_video.txt
    try:
        video_entries = parse_video_list()
    except Exception as e:
        log_with_timestamp(f"Error reading list_video.txt: {e}")
        return [], []
    
    if not video_entries:
        log_with_timestamp("No video entries found in list_video.txt")
        return [], []
    
    log_with_timestamp(f"Found {len(video_entries)} video entries to process")
    
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("Failed to setup browser for video processing")
        return [], []
    
    processed_videos = []
    missing_videos = []
    processed_models = {}  # Cache for model images to avoid re-downloading
    
    try:
        # Process each video entry
        for i, entry in enumerate(video_entries, 1):
            video_url = entry['url']
            pre_extracted_title = entry['title']  # Title from sitemap parser (may be URL-based)
            
            log_with_timestamp(f"\n🎬 Processing video {i}/{len(video_entries)}")
            log_with_timestamp(f"     URL: {video_url}")
            if pre_extracted_title:
                log_with_timestamp(f"     Pre-extracted title: {pre_extracted_title}")
            
            # Extract metadata from the video page
            metadata = extract_video_metadata(driver, video_url)
            if not metadata:
                log_with_timestamp(f"     ❌ Failed to extract metadata from {video_url}")
                continue
            
            # Determine which title to use for file matching
            # Priority: pre-extracted title (from sitemap parser) > extracted title
            final_title = pre_extracted_title or metadata.get('title', '')
            
            if final_title:
                # Update metadata with the final title
                metadata['title'] = final_title
                log_with_timestamp(f"     ✅ Using title: {final_title}")
                log_with_timestamp(f"        Model: {metadata.get('model', 'Unknown')}")
                log_with_timestamp(f"        Tags: {len(metadata.get('tags', []))} tags")
                
                # Try to find the video file using the final title
                video_file = find_video_file(video_folder, final_title)
                
                if video_file:
                    log_with_timestamp(f"        ✅ Found local file: {os.path.basename(video_file)}")
                    processed_videos.append(metadata)
                    # Organize this video with model cache
                    organize_single_video(video_file, metadata, domain, driver, processed_models, organization_folder)
                else:
                    log_with_timestamp(f"        ❌ Local file not found")
                    missing_videos.append({
                        'title': final_title,
                        'url': video_url,
                        'model': metadata.get('model', ''),
                        'tags': metadata.get('tags', [])
                    })
            else:
                log_with_timestamp(f"     ❌ No title available for video: {video_url}")
                missing_videos.append({
                    'title': 'Unknown Title',
                    'url': video_url,
                    'model': '',
                    'tags': []
                })
            
            # Small delay between videos
            time.sleep(1)
        
        log_with_timestamp(f"\n🎯 Video processing complete!")
        log_with_timestamp(f"   Processed: {len(processed_videos)} videos")
        log_with_timestamp(f"   Missing: {len(missing_videos)} videos")
        log_with_timestamp(f"   Models processed: {len(processed_models)} unique models")
        
        return processed_videos, missing_videos
        
    finally:
        driver.quit()

def organize_single_video(video_file, metadata, domain, driver=None, processed_models=None, organization_folder=None):
    """Organize a single video with its metadata"""
    try:
        video_title = metadata.get('title', '')
        log_with_timestamp(f"  �️  Organizing: {video_title}")
        
        # Handle model processing
        model = metadata.get('model', '').strip()
        model_image_url = None
        
        # Use the provided organization folder instead of dynamically determining it
        if not organization_folder:
            # Fallback to old logic if no organization folder provided
            video_folder_parent = os.path.dirname(video_file)
            organization_folder = video_folder_parent
        
        if model:
            clean_model = re.sub(r'[^\w\s-]', '', model).strip()
            model_dir = os.path.join(organization_folder, f"model {clean_model}")
            
            # Use model cache to avoid re-downloading
            if processed_models is None:
                processed_models = {}
                
            if model in processed_models:
                model_image_url = processed_models[model]
                log_with_timestamp(f"    ✅ Using cached model image")
            elif driver:
                model_image_url = extract_model_image_url(driver, model, domain)
                processed_models[model] = model_image_url
                
                # Download model image as folder.jpg
                if model_image_url:
                    folder_jpg_path = os.path.join(model_dir, 'folder.jpg')
                    if not os.path.exists(folder_jpg_path):
                        if download_image(model_image_url, folder_jpg_path):
                            log_with_timestamp(f"    ✅ Downloaded model image")
                        else:
                            log_with_timestamp(f"    ⚠️  Failed to download model image")
                
                # Create actress NFO file
                if not create_actress_nfo(model_dir, model, model_image_url):
                    log_with_timestamp(f"    ⚠️  Failed to create actress NFO")
                
                # Small delay to be respectful
                time.sleep(1)
            
            # Create model symlink
            model_link = os.path.join(model_dir, os.path.basename(video_file))
            if create_relative_symlink(video_file, model_link):
                log_with_timestamp(f"    → Model symlink: model {clean_model}")
        
        # Create NFO file with model image URL
        create_nfo_file(video_file, metadata, model_image_url)
        
        # Download video thumbnail if available
        if metadata.get('thumbnail'):
            thumbnail_path = os.path.splitext(video_file)[0] + '_thumb.jpg'
            if download_image(metadata['thumbnail'], thumbnail_path):
                log_with_timestamp(f"    ✅ Downloaded thumbnail")
        
        # Create symlinks for tags
        for tag in metadata.get('tags', []):
            clean_tag = re.sub(r'[^\w\s-]', '', tag).strip()
            if clean_tag:
                tag_dir = os.path.join(organization_folder, f"tag {clean_tag}")
                tag_link = os.path.join(tag_dir, os.path.basename(video_file))
                
                if create_relative_symlink(video_file, tag_link):
                    log_with_timestamp(f"    → Tag symlink: tag {clean_tag}")
        
        # Create source folder with all videos (using your original structure)
        source_folder_name = f"source {os.path.basename(os.path.dirname(video_file))}"
        source_dir = os.path.join(organization_folder, source_folder_name)
        source_link = os.path.join(source_dir, os.path.basename(video_file))
        
        if create_relative_symlink(video_file, source_link):
            log_with_timestamp(f"    → Source symlink: {source_folder_name}")
        
        # Create untagged folder if no tags
        if not metadata.get('tags'):
            no_tag_dir = os.path.join(organization_folder, "tag no tag")
            no_tag_link = os.path.join(no_tag_dir, os.path.basename(video_file))
            
            if create_relative_symlink(video_file, no_tag_link):
                log_with_timestamp(f"    → No tag symlink created")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"    ❌ Error organizing video: {e}")
        return False

# ===== VIDEO METADATA EXTRACTION =====

def extract_video_metadata(driver, video_url):
    """Extract comprehensive metadata from a video page"""
    try:
        log_with_timestamp(f"  Loading video page: {video_url}")
        driver.get(video_url)
        
        # Wait for page to fully load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass  # Continue even if timeout
        
        # Additional wait for content to render
        time.sleep(3)
        
        # Wait specifically for tags and models sections to load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, '.tags, .models')
            )
        except:
            log_with_timestamp(f"    ⚠️  Timeout waiting for tags/models sections to load")
        
        metadata = {
            'url': video_url,
            'title': '',
            'description': '',
            'thumbnail': '',
            'model': '',
            'tags': [],
            'duration': '',
            'photos': '',
            'date': '',
            'related_videos': []
        }
        
        # Extract title with WebDriverWait
        try:
            h1_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            metadata['title'] = h1_element.text.strip().upper()
            log_with_timestamp(f"    ✅ Title: {metadata['title']}")
        except Exception as e:
            log_with_timestamp(f"    ⚠️  Could not extract title: {e}")
        
        # Extract thumbnail from meta tag
        try:
            # Wait for meta tags to be present
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:image"]'))
            )
            thumbnail_elem = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]')
            metadata['thumbnail'] = thumbnail_elem.get_attribute("content")
            log_with_timestamp(f"    ✅ Thumbnail found")
        except:
            # Fallback: try to find thumbnail in video preview section
            try:
                thumbnail_elem = driver.find_element(By.CSS_SELECTOR, 'iframe[src*="cloudflarestream.com"]')
                poster = thumbnail_elem.get_attribute("poster")
                if poster:
                    metadata['thumbnail'] = poster
                    log_with_timestamp(f"    ✅ Thumbnail found (fallback)")
            except:
                log_with_timestamp(f"    ⚠️  No thumbnail found")
        
        # Extract description
        try:
            desc_elem = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:description"]')
            metadata['description'] = desc_elem.get_attribute("content")
            log_with_timestamp(f"    ✅ Description extracted ({len(metadata['description'])} chars)")
        except:
            # Fallback: look for description in content
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, '.videoDescription p')
                metadata['description'] = desc_elem.text.strip()
                log_with_timestamp(f"    ✅ Description extracted (fallback)")
            except:
                log_with_timestamp(f"    ⚠️  No description found")
        
        # Extract model with enhanced debugging
        try:
            # Multiple selectors to try for model based on actual HTML structure
            model_selectors = [
                '.models ul li a',  # The actual structure: div.models > ul > li > a
                '.models a', 
                'div.models ul li a',
                '.modelName a',
                '.model-name a',
                '.performer a',
                'a[href*="/models/"]'
            ]
            
            model_found = False
            log_with_timestamp(f"    🔍 Searching for model...")
            
            for selector in model_selectors:
                try:
                    model_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    if model_links:
                        # Extract text, removing any icon text - try multiple methods
                        model_text = model_links[0].text.strip()
                        
                        # If text is empty, try getting textContent via JavaScript
                        if not model_text:
                            try:
                                model_text = driver.execute_script(
                                    "return arguments[0].textContent || arguments[0].innerText;", 
                                    model_links[0]
                                ).strip()
                            except:
                                pass
                        
                        # If still empty, try getting text from children excluding icons
                        if not model_text:
                            try:
                                # Get all text nodes, excluding icon elements
                                model_text = driver.execute_script("""
                                    var elem = arguments[0];
                                    var text = '';
                                    for (var i = 0; i < elem.childNodes.length; i++) {
                                        var node = elem.childNodes[i];
                                        if (node.nodeType === 3) { // Text node
                                            text += node.textContent;
                                        } else if (node.nodeType === 1 && !node.classList.contains('fa-solid')) { // Element node, not icon
                                            text += node.textContent;
                                        }
                                    }
                                    return text.trim();
                                """, model_links[0])
                            except:
                                pass
                        
                        if model_text:
                            metadata['model'] = model_text
                            log_with_timestamp(f"    ✅ Model found with selector '{selector}': {metadata['model']}")
                            model_found = True
                            break
                        else:
                            log_with_timestamp(f"    🔍 Selector '{selector}' found element but no text")
                except Exception as e:
                    log_with_timestamp(f"    🔍 Selector '{selector}' failed: {e}")
                    continue
            
            if not model_found:
                # Debug: Print page structure around models with more detail
                try:
                    possible_model_divs = driver.find_elements(By.CSS_SELECTOR, 'div[class*="model"], div[class*="performer"]')
                    if possible_model_divs:
                        log_with_timestamp(f"    🔍 Found {len(possible_model_divs)} potential model containers")
                        for div in possible_model_divs[:3]:  # Check first 3
                            class_name = div.get_attribute("class")
                            text_content = div.text.strip()
                            inner_html = div.get_attribute("innerHTML")[:200]  # First 200 chars of HTML
                            log_with_timestamp(f"         Class: '{class_name}', Text: '{text_content}'")
                            log_with_timestamp(f"         HTML: {inner_html}...")
                            
                            # Try to find links within this div
                            links_in_div = div.find_elements(By.TAG_NAME, "a")
                            log_with_timestamp(f"         Links in div: {len(links_in_div)}")
                            for link in links_in_div:
                                link_text = link.text.strip()
                                link_href = link.get_attribute("href")
                                log_with_timestamp(f"           Link: '{link_text}' -> {link_href}")
                    else:
                        log_with_timestamp(f"    ⚠️  No model containers found in page")
                except Exception as e:
                    log_with_timestamp(f"    ❌ Error in model debug: {e}")
                log_with_timestamp(f"    ⚠️  No model found with any selector")
                
        except Exception as e:
            log_with_timestamp(f"    ❌ Error extracting model: {e}")
        
        # Extract tags with enhanced debugging
        try:
            # Multiple selectors to try for tags based on actual HTML structure
            tag_selectors = [
                '.tags ul li a',  # The actual structure: div.tags > ul > li > a
                '.tags li a',
                '.tags a',
                'div.tags ul li a',
                '.tag-list a',
                'a[href*="/tags/"]'  # Changed from /tag/ to /tags/
            ]
            
            tags_found = False
            log_with_timestamp(f"    🔍 Searching for tags...")
            
            for selector in tag_selectors:
                try:
                    tag_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    if tag_links:
                        for tag_link in tag_links:
                            # Extract text, removing any icon text - try multiple methods
                            tag_text = tag_link.text.strip()
                            
                            # If text is empty, try getting textContent via JavaScript
                            if not tag_text:
                                try:
                                    tag_text = driver.execute_script(
                                        "return arguments[0].textContent || arguments[0].innerText;", 
                                        tag_link
                                    ).strip()
                                except:
                                    pass
                            
                            # If still empty, try getting text from children excluding icons
                            if not tag_text:
                                try:
                                    # Get all text nodes, excluding icon elements
                                    tag_text = driver.execute_script("""
                                        var elem = arguments[0];
                                        var text = '';
                                        for (var i = 0; i < elem.childNodes.length; i++) {
                                            var node = elem.childNodes[i];
                                            if (node.nodeType === 3) { // Text node
                                                text += node.textContent;
                                            } else if (node.nodeType === 1 && !node.classList.contains('fa-solid')) { // Element node, not icon
                                                text += node.textContent;
                                            }
                                        }
                                        return text.trim();
                                    """, tag_link)
                                except:
                                    pass
                            
                            if tag_text:
                                metadata['tags'].append(tag_text)
                        
                        if metadata['tags']:
                            log_with_timestamp(f"    ✅ Tags found with selector '{selector}': {len(metadata['tags'])} tags")
                            log_with_timestamp(f"         Tags: {', '.join(metadata['tags'][:3])}{'...' if len(metadata['tags']) > 3 else ''}")
                            tags_found = True
                            break
                        else:
                            log_with_timestamp(f"    🔍 Selector '{selector}' found elements but no text")
                except Exception as e:
                    log_with_timestamp(f"    🔍 Selector '{selector}' failed: {e}")
                    continue
            
            if not tags_found:
                # Debug: Print page structure around tags
                try:
                    possible_tag_divs = driver.find_elements(By.CSS_SELECTOR, 'div[class*="tag"], div[class*="category"]')
                    if possible_tag_divs:
                        log_with_timestamp(f"    🔍 Found {len(possible_tag_divs)} potential tag containers")
                        for div in possible_tag_divs[:3]:  # Check first 3
                            class_name = div.get_attribute("class")
                            text_content = div.text.strip()[:50]  # First 50 chars
                            log_with_timestamp(f"         Class: '{class_name}', Text: '{text_content}'")
                    else:
                        log_with_timestamp(f"    ⚠️  No tag containers found in page")
                except:
                    pass
                log_with_timestamp(f"    ⚠️  No tags found with any selector")
                
        except Exception as e:
            log_with_timestamp(f"    ❌ Error extracting tags: {e}")
        
        # Extract video info (duration, photos, date)
        try:
            # Wait for content info to be present
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.contentInfo'))
            )
            info_items = driver.find_elements(By.CSS_SELECTOR, '.contentInfo li')
            for item in info_items:
                text = item.text.strip()
                if ':' in text and len(text.split(':')) >= 2:
                    # Duration format like "14:22"
                    metadata['duration'] = text
                elif 'photos' in text.lower():
                    metadata['photos'] = text
                elif any(month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                    metadata['date'] = text
            log_with_timestamp(f"    ✅ Video info extracted")
        except:
            log_with_timestamp(f"    ⚠️  No video info found")
        
        # Extract related videos
        try:
            # Multiple selectors to try for related videos based on actual HTML structure
            related_selectors = [
                '.relatedVideos .videoBlock',  # The actual structure
                '.related-videos .videoBlock',
                '.videoBlock',
                '.related .video-item'
            ]
            
            related_found = False
            log_with_timestamp(f"    🔍 Searching for related videos...")
            
            for selector in related_selectors:
                try:
                    related_blocks = driver.find_elements(By.CSS_SELECTOR, selector)
                    if related_blocks:
                        log_with_timestamp(f"    ✅ Found {len(related_blocks)} related videos with selector '{selector}'")
                        
                        for block in related_blocks[:5]:  # Limit to first 5 related videos
                            try:
                                # Try multiple selectors for title within each block
                                title_selectors = ['h3 a', 'h2 a', '.title a', 'a[href*="/updates/"]']
                                for title_sel in title_selectors:
                                    try:
                                        title_elem = block.find_element(By.CSS_SELECTOR, title_sel)
                                        related_title = title_elem.text.strip()
                                        
                                        # If text is empty, try getting textContent via JavaScript
                                        if not related_title:
                                            try:
                                                related_title = driver.execute_script(
                                                    "return arguments[0].textContent || arguments[0].innerText;", 
                                                    title_elem
                                                ).strip()
                                            except:
                                                pass
                                        
                                        related_url = title_elem.get_attribute("href")
                                        if related_title and related_url and "/updates/" in related_url:
                                            metadata['related_videos'].append({
                                                'title': related_title.upper(),  # Convert to uppercase for consistency
                                                'url': related_url
                                            })
                                            break
                                    except:
                                        continue
                            except:
                                continue
                        
                        if metadata['related_videos']:
                            log_with_timestamp(f"    ✅ Related videos: {len(metadata['related_videos'])} found")
                            related_found = True
                            break
                        
                except Exception as e:
                    log_with_timestamp(f"    🔍 Selector '{selector}' failed: {e}")
                    continue
                    
            if not related_found:
                log_with_timestamp(f"    ⚠️  No related videos found")
                
        except Exception as e:
            log_with_timestamp(f"    ❌ Error extracting related videos: {e}")
        
        return metadata
        
    except Exception as e:
        log_with_timestamp(f"    ❌ Error extracting metadata from {video_url}: {e}")
        return None

# ===== FILE UTILITIES =====

def download_image(url, save_path):
    """Download image from URL to save_path"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        log_with_timestamp(f"Error downloading image {url}: {e}")
        return False

def find_video_file(video_folder, video_title):
    """Find a video file matching the title (case-insensitive exact match)"""
    if not video_title:
        return None
        
    # Clean title for filename matching (remove special characters, normalize spaces)
    clean_title = re.sub(r'[^\w\s-]', '', video_title).strip()
    clean_title = re.sub(r'\s+', ' ', clean_title)
    
    # Common video extensions
    video_extensions = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm']
    
    for ext in video_extensions:
        pattern = os.path.join(video_folder, f"**/{ext}")
        for video_file in glob.glob(pattern, recursive=True):
            video_filename = os.path.basename(video_file)
            video_name = os.path.splitext(video_filename)[0]
            
            # Clean filename the same way as title
            clean_filename = re.sub(r'[^\w\s-]', '', video_name).strip()
            clean_filename = re.sub(r'\s+', ' ', clean_filename)
            
            # Case-insensitive exact match
            if clean_title.lower() == clean_filename.lower():
                return video_file
    
    # If no exact match found and title looks like a URL-based title (all caps with spaces)
    # Try to match against normal titles by converting back to typical title case
    if video_title.isupper() and ' ' in video_title:
        # Try converting URL-based title back to normal case for matching
        normal_title = video_title.title()  # Convert to Title Case
        
        for ext in video_extensions:
            pattern = os.path.join(video_folder, f"**/{ext}")
            for video_file in glob.glob(pattern, recursive=True):
                video_filename = os.path.basename(video_file)
                video_name = os.path.splitext(video_filename)[0]
                
                # Clean filename
                clean_filename = re.sub(r'[^\w\s-]', '', video_name).strip()
                clean_filename = re.sub(r'\s+', ' ', clean_filename)
                
                # Try matching with converted title
                clean_normal_title = re.sub(r'[^\w\s-]', '', normal_title).strip()
                clean_normal_title = re.sub(r'\s+', ' ', clean_normal_title)
                
                if clean_normal_title.lower() == clean_filename.lower():
                    return video_file
    
    return None

def create_relative_symlink(target_path, link_path):
    """Create a relative symlink from link_path to target_path"""
    try:
        # Calculate relative path from link to target
        link_dir = os.path.dirname(link_path)
        rel_path = os.path.relpath(target_path, link_dir)
        
        # Create directory if it doesn't exist
        os.makedirs(link_dir, exist_ok=True)
        
        # Remove existing symlink if it exists
        if os.path.islink(link_path):
            os.unlink(link_path)
        
        # Create symlink
        os.symlink(rel_path, link_path)
        return True
    except Exception as e:
        log_with_timestamp(f"Error creating symlink {link_path} -> {target_path}: {e}")
        return False

def extract_model_image_url(driver, model_name, domain):
    """Extract model image URL from model page"""
    try:
        # Clean model name for URL
        clean_model = re.sub(r'[^\w\s-]', '', model_name).strip()
        clean_model = re.sub(r'\s+', '-', clean_model).lower()
        
        model_url = f"{domain}/models/{clean_model}"
        log_with_timestamp(f"  Fetching model image from: {model_url}")
        
        driver.get(model_url)
        
        # Wait for page to fully load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass  # Continue even if timeout
        
        # Additional wait for content to render
        time.sleep(3)
        
        # Try to find model image with wait
        image_selectors = [
            'img.model-image',
            '.model-photo img',
            '.modelImage img',
            '.profile-image img',
            '.model-avatar img',
            'img[alt*="' + model_name + '"]'
        ]
        
        for selector in image_selectors:
            try:
                # Wait for image element to be present
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                img_elem = driver.find_element(By.CSS_SELECTOR, selector)
                img_url = img_elem.get_attribute("src")
                if img_url and "http" in img_url:
                    log_with_timestamp(f"  ✅ Found model image: {img_url}")
                    return img_url
            except:
                continue
        
        # Fallback: look for any large image that might be the model
        try:
            # Wait for any images to load
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
            images = driver.find_elements(By.TAG_NAME, "img")
            for img in images:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt") or ""
                if (src and "http" in src and 
                    (model_name.lower() in alt.lower() or 
                     "model" in src.lower() or 
                     "profile" in src.lower())):
                    log_with_timestamp(f"  ✅ Found model image (fallback): {src}")
                    return src
        except:
            pass
        
        log_with_timestamp(f"  ⚠️  No model image found for {model_name}")
        return None
        
    except Exception as e:
        log_with_timestamp(f"  ❌ Error extracting model image: {e}")
        return None

def create_actress_nfo(model_dir, model_name, model_image_url):
    """Create actress NFO file for model directory"""
    try:
        actress_nfo_path = os.path.join(model_dir, "actress.nfo")
        
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<person>
    <name>{model_name}</name>
    <type>Actor</type>
    <thumb>{model_image_url or ''}</thumb>
</person>"""
        
        with open(actress_nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        log_with_timestamp(f"  ✅ Created actress.nfo for {model_name}")
        return True
        
    except Exception as e:
        log_with_timestamp(f"  ❌ Error creating actress NFO: {e}")
        return False

def create_nfo_file(video_path, metadata, model_image_url=None):
    """Create NFO file for video with extracted metadata"""
    try:
        nfo_path = os.path.splitext(video_path)[0] + '.nfo'
        
        # Build NFO content
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>{metadata.get('title', '')}</title>
    <plot>{metadata.get('description', '')}</plot>
    <studio>{urlparse(metadata.get('url', '')).netloc}</studio>
    <premiered>{metadata.get('date', '')}</premiered>
    <runtime>{metadata.get('duration', '')}</runtime>
    <thumb>{metadata.get('thumbnail', '')}</thumb>
"""
        
        # Add model as actor with image
        if metadata.get('model'):
            if model_image_url:
                nfo_content += f"""    <actor>
        <name>{metadata['model']}</name>
        <thumb>{model_image_url}</thumb>
    </actor>
"""
            else:
                nfo_content += f"    <actor>\n        <name>{metadata['model']}</name>\n    </actor>\n"
        
        # Add tags as genres
        for tag in metadata.get('tags', []):
            nfo_content += f"    <genre>{tag}</genre>\n"
        
        # Add related videos as similar movies
        for related in metadata.get('related_videos', []):
            nfo_content += f"    <similar>{related['title']}</similar>\n"
        
        nfo_content += "</movie>"
        
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        return True
    except Exception as e:
        log_with_timestamp(f"Error creating NFO file for {video_path}: {e}")
        return False

# ===== MAIN LOGIC =====

def main():
    """Main function"""
    try:
        # Get user inputs
        domain, video_folder, organization_folder = get_user_inputs()
        
        # Process videos from list
        log_with_timestamp("🚀 Starting video processing from list_video.txt...")
        processed_videos, missing_videos = process_videos_from_list(domain, video_folder, organization_folder)
        
        # Print final summary
        log_separator()
        log_with_timestamp("📊 FINAL PROCESSING SUMMARY")
        log_with_timestamp("=" * 40)
        log_with_timestamp(f"✅ Videos processed: {len(processed_videos)}")
        log_with_timestamp(f"❌ Missing videos: {len(missing_videos)}")
        
        if missing_videos:
            log_with_timestamp("\n📋 Missing Videos (found online but not in folder):")
            for missing in missing_videos:
                log_with_timestamp(f"  • {missing['title']}")
                log_with_timestamp(f"    Model: {missing['model']}")
                log_with_timestamp(f"    Tags: {', '.join(missing['tags'])}")
                log_with_timestamp(f"    URL: {missing['url']}")
                log_with_timestamp("")
        
        log_with_timestamp("🎉 Page-by-page video processing completed successfully!")
            
    except KeyboardInterrupt:
        log_with_timestamp("❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_with_timestamp(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
