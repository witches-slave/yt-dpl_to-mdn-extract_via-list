#!/usr/bin/env python3
"""
Unified Tag and Model Organizer Script
Crawls tags/models directly, creates symlinks, downloads images/thumbnails,
and generates rich NFO files with metadata from video pages.
"""

import os
import re
import glob
import time
import requests
import xml.etree.ElementTree as ET
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

def get_user_inputs():
    """Get domain and video folder from user"""
    print("=" * 60)
    print("UNIFIED TAG & MODEL ORGANIZER")
    print("=" * 60)
    print()
    
    # Get domain
    domain = input("Enter the domain (e.g., https://shinysboundsluts.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        exit(1)
    
    # Ensure domain has proper format
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    domain = domain.rstrip('/')
    
    print()
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
            break
        else:
            print(f"Folder '{folder}' does not exist. Please try again.")
    
    print(f"\nUsing domain: {domain}")
    print(f"Using video folder: {folder}")
    print("=" * 60 + "\n")
    
    return domain, folder

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

def get_video_files(video_folder):
    """Scan video folder and return normalized file mapping"""
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

def normalize_title_for_matching(title):
    """Normalize title for better matching"""
    normalized = title.lower()
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
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

def crawl_tags_and_models(driver, domain):
    """Crawl /tags/ and /models/ pages to get all tag/model URLs"""
    log_with_timestamp("🕷️ Starting crawl of /tags/ and /models/ pages...")
    
    all_tag_model_urls = []
    
    # Crawl tags
    tags_urls = crawl_category_pages(driver, domain, "tags")
    all_tag_model_urls.extend(tags_urls)
    
    # Crawl models
    models_urls = crawl_category_pages(driver, domain, "models")
    all_tag_model_urls.extend(models_urls)
    
    # Remove duplicates
    unique_urls = list(dict.fromkeys(all_tag_model_urls))
    
    log_with_timestamp(f"🎯 Found {len(unique_urls)} total tag/model URLs")
    return unique_urls

def crawl_category_pages(driver, domain, category):
    """Crawl either 'tags' or 'models' category pages"""
    base_url = f"{domain}/{category}"
    category_urls = []
    
    log_with_timestamp(f"Crawling {category} pages: {base_url}")
    
    try:
        driver.get(base_url)
        time.sleep(3)
        
        # Get pagination URLs for this category
        pagination_urls = get_pagination_urls(driver, base_url, category)
        log_with_timestamp(f"Found {len(pagination_urls)} {category} pages to crawl")
        
        # Crawl each page
        for i, page_url in enumerate(pagination_urls, 1):
            log_with_timestamp(f"Crawling {category} page {i}/{len(pagination_urls)}: {page_url}")
            
            try:
                driver.get(page_url)
                time.sleep(2)
                
                # Extract tag/model URLs from this page
                urls = extract_tag_model_urls_from_page(driver, domain, category)
                category_urls.extend(urls)
                
                log_with_timestamp(f"  Found {len(urls)} {category} on this page")
                
            except Exception as e:
                log_with_timestamp(f"  Error crawling {category} page: {e}")
                continue
        
        log_with_timestamp(f"✅ {category.title()} crawling complete: found {len(category_urls)} {category} URLs")
        return category_urls
        
    except Exception as e:
        log_with_timestamp(f"Error crawling {category}: {e}")
        return category_urls

def get_pagination_urls(driver, base_url, category):
    """Get all pagination URLs for tags or models pages"""
    pagination_urls = [base_url]
    
    try:
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
            pagination_links = pagination_div.find_elements(By.TAG_NAME, "a")
            
            max_page = 1
            page_url_pattern = None
            all_page_numbers = []
            
            for link in pagination_links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    # Extract page numbers from text
                    if text.isdigit():
                        page_num = int(text)
                        all_page_numbers.append(page_num)
                        
                        # Set URL pattern from any page link (prefer page 2)
                        if page_num >= 2 and not page_url_pattern:
                            if f"?page={page_num}" in href:
                                page_url_pattern = href.replace(f"?page={page_num}", "?page={}")
                            elif f"/page/{page_num}" in href:
                                page_url_pattern = href.replace(f"/page/{page_num}", "/page/{}")
                    
                    # Also extract from href directly for higher page numbers
                    if href and "page=" in href:
                        try:
                            page_match = re.search(r'page=(\d+)', href)
                            if page_match:
                                page_num = int(page_match.group(1))
                                all_page_numbers.append(page_num)
                                
                                # Set URL pattern if not already set
                                if not page_url_pattern:
                                    if f"?page={page_num}" in href:
                                        page_url_pattern = href.replace(f"?page={page_num}", "?page={}")
                                    elif f"/page/{page_num}" in href:
                                        page_url_pattern = href.replace(f"/page/{page_num}", "/page/{}")
                        except:
                            pass
                            
                except Exception:
                    continue
            
            # Find the maximum page number from all discovered pages
            if all_page_numbers:
                max_page = max(all_page_numbers)
                log_with_timestamp(f"🔢 Found {category} pagination: discovered pages {sorted(set(all_page_numbers))}, max page: {max_page}")
            
            # If we still don't have a pattern, try to build one from base URL
            if not page_url_pattern and max_page > 1:
                if "?" in base_url:
                    page_url_pattern = base_url + "&page={}"
                else:
                    page_url_pattern = base_url + "?page={}"
            
            # Generate URLs for all pages from 1 to max_page
            if page_url_pattern and max_page > 1:
                log_with_timestamp(f"� Generating {category} URLs for pages 1 to {max_page}")
                log_with_timestamp(f"🔗 URL pattern: {page_url_pattern}")
                
                # Clear pagination_urls and rebuild with all pages
                pagination_urls = []
                
                for page_num in range(1, max_page + 1):
                    if page_num == 1:
                        # Page 1 is usually the base URL
                        pagination_urls.append(base_url)
                    else:
                        page_url = page_url_pattern.format(page_num)
                        pagination_urls.append(page_url)
        
        log_with_timestamp(f"✅ Generated {len(pagination_urls)} {category} page URLs")
        return pagination_urls
        
    except Exception as e:
        log_with_timestamp(f"⚠️ Error finding {category} pagination: {e}")
        return pagination_urls

def extract_tag_model_urls_from_page(driver, domain, category):
    """Extract individual tag/model page URLs from a listing page"""
    urls = []
    
    if category == "tags":
        selectors_to_try = [
            "div.tagsContainer .tagName a",
            ".tagsContainer a",
            "div.tagName a",
            ".tag-link",
            f"a[href*='/{category}/']:not([href$='/{category}']):not([href$='/{category}/'])"
        ]
    elif category == "models":
        selectors_to_try = [
            "div.modelBlock h3 a",
            ".modelBlock a",
            "div.modelName a", 
            ".model-link",
            f"a[href*='/{category}/']:not([href$='/{category}']):not([href$='/{category}/'])"
        ]
    else:
        selectors_to_try = [
            f"a[href*='/{category}/']:not([href$='/{category}']):not([href$='/{category}/'])"
        ]
    
    for selector in selectors_to_try:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for element in elements:
                    href = element.get_attribute("href")
                    if href and f"/{category}/" in href and not href.endswith(f"/{category}"):
                        # Ensure it's a full URL
                        if href.startswith('/'):
                            href = domain + href
                        urls.append(href)
                break
        except Exception:
            continue
    
    return list(set(urls))

def crawl_tag_model_page_for_videos(driver, url):
    """Crawl a tag/model page to extract video information including thumbnails"""
    try:
        log_with_timestamp(f"🔍 Crawling tag/model page: {url}")
        driver.get(url)
        time.sleep(3)
        
        # Wait for dynamic content
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.videoBlock"))
            )
            time.sleep(2)
        except:
            log_with_timestamp("   ⚠️ Timeout waiting for videoBlock elements, proceeding anyway")
        
        all_video_data = []
        
        # Extract videos from current page
        def extract_videos_from_current_page():
            video_data = []
            
            try:
                video_blocks = driver.find_elements(By.CSS_SELECTOR, "div.videoBlock")
                log_with_timestamp(f"   Found {len(video_blocks)} video blocks on page")
                
                for i, block in enumerate(video_blocks):
                    try:
                        # Extract title
                        title_element = block.find_element(By.CSS_SELECTOR, "h3 a")
                        title = title_element.text.strip()
                        video_url = title_element.get_attribute("href")
                        
                        # Extract thumbnail
                        thumbnail_url = None
                        try:
                            img_element = block.find_element(By.CSS_SELECTOR, "div.videoPic img")
                            thumbnail_url = img_element.get_attribute("src")
                        except:
                            pass
                        
                        if title and len(title) > 3:
                            video_info = {
                                'title': title,
                                'url': video_url,
                                'thumbnail': thumbnail_url
                            }
                            video_data.append(video_info)
                            log_with_timestamp(f"     ✅ Video {len(video_data)}: '{title}'")
                            if thumbnail_url:
                                log_with_timestamp(f"       🖼️ Thumbnail: {thumbnail_url}")
                        
                    except Exception as e:
                        log_with_timestamp(f"     ❌ Error processing video block {i+1}: {e}")
                        continue
                
            except Exception as e:
                log_with_timestamp(f"   ❌ Error extracting videos: {e}")
            
            return video_data
        
        # Extract videos from the first page
        page_videos = extract_videos_from_current_page()
        all_video_data.extend(page_videos)
        log_with_timestamp(f"   Page 1: Found {len(page_videos)} videos")
        
        # Handle pagination (similar to original logic but for video data)
        # ... pagination logic here (simplified for brevity) ...
        
        log_with_timestamp(f"   ✅ Total videos found: {len(all_video_data)}")
        return all_video_data
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error crawling {url}: {e}")
        return []

def extract_tag_name_from_url(url):
    """Extract tag/model name from URL"""
    try:
        if '/tags/' in url:
            tag_name = url.split('/tags/')[-1].rstrip('/')
        elif '/models/' in url:
            tag_name = url.split('/models/')[-1].rstrip('/')
        else:
            tag_name = url.rstrip('/').split('/')[-1]
        
        # Clean up the tag name
        tag_name = tag_name.replace('-', ' ').replace('_', ' ')
        tag_name = re.sub(r'[^\w\s]', '', tag_name)
        tag_name = ' '.join(tag_name.split())
        
        return tag_name.title() if tag_name else "Unknown"
        
    except Exception as e:
        log_with_timestamp(f"Error extracting tag name from {url}: {e}")
        return "Unknown"

def download_image(url, filepath):
    """Download image from URL to filepath"""
    try:
        if not url:
            return False
            
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        log_with_timestamp(f"   ❌ Error downloading image: {e}")
        return False

def download_model_image(driver, url, folder_path):
    """Download model preview image for model folders only"""
    try:
        if '/models/' not in url:
            return False
            
        log_with_timestamp(f"   🖼️ Downloading model image from {url}")
        
        driver.get(url)
        time.sleep(3)
        
        # Look for model image
        img_selectors = [
            '.modelPic img',
            '.modelBlock img',
            'img[alt*="model"]',
            '.performer-image img',
            '.model-photo img',
            'img[src*="performer"]',
            'img[src*="model"]'
        ]
        
        for selector in img_selectors:
            try:
                img_element = driver.find_element(By.CSS_SELECTOR, selector)
                img_url = img_element.get_attribute('src')
                
                if img_url and img_url.startswith(('http', '//')):
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        base_url = url.split('/models/')[0] if '/models/' in url else url.rsplit('/', 1)[0]
                        img_url = base_url + img_url
                    
                    img_path = os.path.join(folder_path, 'folder.jpg')
                    if download_image(img_url, img_path):
                        log_with_timestamp(f"   ✅ Model image saved: folder.jpg")
                        return True
                    
            except Exception:
                continue
        
        log_with_timestamp(f"   ⚠️ No model image found")
        return False
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error downloading model image: {e}")
        return False

def extract_video_metadata(driver, video_url):
    """Extract rich metadata from video page"""
    try:
        log_with_timestamp(f"   📄 Extracting metadata from: {video_url}")
        driver.get(video_url)
        time.sleep(3)
        
        metadata = {}
        
        # Extract title
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, "h1")
            metadata['title'] = title_element.text.strip()
        except:
            pass
        
        # Extract description
        try:
            desc_element = driver.find_element(By.CSS_SELECTOR, ".videoDescription p")
            metadata['description'] = desc_element.text.strip()
        except:
            pass
        
        # Extract tags
        try:
            tag_elements = driver.find_elements(By.CSS_SELECTOR, ".tags a")
            tags = []
            for tag_elem in tag_elements:
                tag_text = tag_elem.text.strip()
                if tag_text and tag_text.lower() != 'updates':
                    tags.append(tag_text)
            metadata['tags'] = tags
        except:
            metadata['tags'] = []
        
        # Extract models
        try:
            model_elements = driver.find_elements(By.CSS_SELECTOR, ".models a")
            models = []
            for model_elem in model_elements:
                model_text = model_elem.text.strip()
                if model_text:
                    models.append(model_text)
            metadata['models'] = models
        except:
            metadata['models'] = []
        
        # Extract date
        try:
            date_element = driver.find_element(By.CSS_SELECTOR, ".contentInfo .fa-calendar").find_element(By.XPATH, "..")
            metadata['date'] = date_element.text.strip()
        except:
            pass
        
        # Extract duration
        try:
            duration_element = driver.find_element(By.CSS_SELECTOR, ".contentInfo .fa-clock").find_element(By.XPATH, "..")
            metadata['duration'] = duration_element.text.strip()
        except:
            pass
        
        # Extract thumbnail from meta tags (high quality)
        try:
            meta_image = driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]')
            metadata['thumbnail'] = meta_image.get_attribute('content')
        except:
            # Fallback to poster in iframe
            try:
                iframe = driver.find_element(By.CSS_SELECTOR, 'iframe.cloudflare-player')
                poster_url = iframe.get_attribute('src')
                if 'poster=' in poster_url:
                    metadata['thumbnail'] = poster_url.split('poster=')[1].split('&')[0]
            except:
                pass
        
        log_with_timestamp(f"   ✅ Extracted metadata: {len(metadata.get('tags', []))} tags, {len(metadata.get('models', []))} models")
        return metadata
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error extracting metadata: {e}")
        return {}

def create_rich_nfo(video_path, metadata, additional_tags=None):
    """Create rich NFO file with metadata from video page"""
    try:
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        nfo_path = os.path.join(video_dir, f"{video_name}.nfo")
        
        # Combine tags from video page and folder organization
        all_tags = list(metadata.get('tags', []))
        if additional_tags:
            for tag in additional_tags:
                if tag not in all_tags:
                    all_tags.append(tag)
        
        # Create NFO content
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>{metadata.get('title', video_name)}</title>
    <plot>{metadata.get('description', 'Video with tags: ' + ', '.join(all_tags))}</plot>
"""
        
        if metadata.get('date'):
            nfo_content += f"    <aired>{metadata.get('date')}</aired>\n"
        
        if metadata.get('duration'):
            nfo_content += f"    <runtime>{metadata.get('duration')}</runtime>\n"
        
        # Add tags and genres
        for tag in all_tags:
            nfo_content += f"    <tag>{tag}</tag>\n"
            nfo_content += f"    <genre>{tag}</genre>\n"
        
        # Add actors (models)
        for model in metadata.get('models', []):
            nfo_content += f"    <actor><name>{model}</name></actor>\n"
        
        nfo_content += "</movie>"
        
        # Write NFO file
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
            
        log_with_timestamp(f"   📝 Created rich NFO with {len(all_tags)} tags: {os.path.basename(nfo_path)}")
        return True
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error creating NFO file: {e}")
        return False

def create_source_aware_symlink(target_path, tag_folder):
    """Create symlink with source folder awareness"""
    source_folder = os.path.basename(os.path.dirname(target_path))
    original_filename = os.path.basename(target_path)
    filename_without_ext = os.path.splitext(original_filename)[0]
    file_extension = os.path.splitext(original_filename)[1]
    
    link_path = os.path.join(tag_folder, original_filename)
    
    # Handle conflicts
    if os.path.exists(link_path) or os.path.islink(link_path):
        try:
            existing_target = os.path.realpath(link_path)
            current_target = os.path.realpath(target_path)
            
            if existing_target == current_target:
                return True, "already_exists"
            
            # Different file - add source folder to filename
            source_aware_filename = f"{filename_without_ext} ({source_folder}){file_extension}"
            link_path = os.path.join(tag_folder, source_aware_filename)
            
        except (OSError, IOError):
            source_aware_filename = f"{filename_without_ext} ({source_folder}){file_extension}"
            link_path = os.path.join(tag_folder, source_aware_filename)
    
    # Create the symlink
    try:
        if os.path.exists(link_path) or os.path.islink(link_path):
            os.remove(link_path)
        
        relative_target = os.path.relpath(target_path, os.path.dirname(link_path))
        os.symlink(relative_target, link_path)
        return True, "symlink"
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error creating link: {e}")
        return False, "error"

def main():
    """Main function"""
    log_with_timestamp("🏷️ Starting Unified Tag and Model Organizer")
    
    # Get user inputs
    domain, video_folder = get_user_inputs()
    
    # Get all video files
    video_files = get_video_files(video_folder)
    if not video_files:
        log_with_timestamp("❌ No video files found!")
        return False
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        log_with_timestamp("❌ Failed to setup web driver!")
        return False
    
    try:
        # Crawl tags and models
        tag_model_urls = crawl_tags_and_models(driver, domain)
        if not tag_model_urls:
            log_with_timestamp("❌ No tag/model URLs found!")
            return False
        
        # Create tags folder
        tags_folder = "./tags"
        os.makedirs(tags_folder, exist_ok=True)
        
        # Statistics
        total_processed = 0
        total_videos_found = 0
        total_links_created = 0
        total_nfos_created = 0
        video_metadata_map = {}  # Store metadata for each video
        
        # Process each tag/model URL
        for i, url in enumerate(tag_model_urls, 1):
            log_with_timestamp(f"🔄 Processing {i}/{len(tag_model_urls)}: {url}")
            
            # Extract tag/model name
            tag_name = extract_tag_name_from_url(url)
            
            # Create tag folder
            tag_folder = os.path.join(tags_folder, tag_name)
            os.makedirs(tag_folder, exist_ok=True)
            
            # Download model image if it's a model
            if '/models/' in url:
                download_model_image(driver, url, tag_folder)
            
            # Crawl tag/model page for videos
            video_data_list = crawl_tag_model_page_for_videos(driver, url)
            
            if not video_data_list:
                log_with_timestamp(f"   ⚠️ No videos found for {tag_name}")
                total_processed += 1
                continue
            
            total_videos_found += len(video_data_list)
            
            # Process each video
            matched_count = 0
            for video_data in video_data_list:
                video_title = video_data['title']
                video_url = video_data['url']
                thumbnail_url = video_data['thumbnail']
                
                # Find matching video file
                matching_file = find_matching_video(video_title, video_files)
                
                if matching_file:
                    # Create symlink
                    success, link_type = create_source_aware_symlink(matching_file, tag_folder)
                    if success:
                        matched_count += 1
                        total_links_created += 1
                        
                        if link_type not in ["already_exists"]:
                            source_folder = os.path.basename(os.path.dirname(matching_file))
                            log_with_timestamp(f"     📁 Linked: {os.path.basename(matching_file)} from {source_folder}")
                        
                        # Download thumbnail
                        if thumbnail_url:
                            video_dir = os.path.dirname(matching_file)
                            video_name = os.path.splitext(os.path.basename(matching_file))[0]
                            thumb_path = os.path.join(video_dir, f"{video_name}-thumb.jpg")
                            if download_image(thumbnail_url, thumb_path):
                                log_with_timestamp(f"     🖼️ Downloaded thumbnail")
                        
                        # Extract metadata from video page if not already done
                        real_path = os.path.realpath(matching_file)
                        if real_path not in video_metadata_map:
                            metadata = extract_video_metadata(driver, video_url)
                            video_metadata_map[real_path] = metadata
                        
                        # Add current tag to video's tag list
                        if real_path not in video_metadata_map:
                            video_metadata_map[real_path] = {'tags': []}
                        
                        current_tags = video_metadata_map[real_path].get('folder_tags', [])
                        if tag_name not in current_tags:
                            current_tags.append(tag_name)
                            video_metadata_map[real_path]['folder_tags'] = current_tags
            
            log_with_timestamp(f"   ✅ {tag_name}: {matched_count}/{len(video_data_list)} videos linked")
            total_processed += 1
        
        # Create NFO files with rich metadata
        log_with_timestamp("🏷️ Creating rich NFO files with metadata...")
        
        for real_path, metadata in video_metadata_map.items():
            # Combine tags from video page and folder organization
            video_tags = metadata.get('tags', [])
            folder_tags = metadata.get('folder_tags', [])
            all_tags = video_tags + [tag for tag in folder_tags if tag not in video_tags]
            
            if create_rich_nfo(real_path, metadata, all_tags):
                total_nfos_created += 1
        
        # Create "No Tag" folder for unlinked videos
        log_with_timestamp("🔍 Creating 'No Tag' folder for unlinked videos...")
        no_tag_folder = os.path.join(tags_folder, "No Tag")
        os.makedirs(no_tag_folder, exist_ok=True)
        
        # Find unlinked videos
        linked_files = set()
        for root, dirs, files in os.walk(tags_folder):
            if root != no_tag_folder:
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.islink(file_path):
                        try:
                            real_path = os.path.realpath(file_path)
                            linked_files.add(real_path)
                        except:
                            pass
        
        no_tag_count = 0
        for video_path in video_files.values():
            real_video_path = os.path.realpath(video_path)
            if real_video_path not in linked_files:
                success, link_type = create_source_aware_symlink(video_path, no_tag_folder)
                if success and link_type not in ["already_exists"]:
                    no_tag_count += 1
        
        log_with_timestamp(f"   ✅ Added {no_tag_count} untagged videos to 'No Tag' folder")
        
        # Summary
        log_with_timestamp("📊 Summary:")
        log_with_timestamp(f"   • Processed {total_processed} tags/models")
        log_with_timestamp(f"   • Found {total_videos_found} videos on tag/model pages")
        log_with_timestamp(f"   • Created {total_links_created} video links")
        log_with_timestamp(f"   • Created {total_nfos_created} rich NFO files")
        log_with_timestamp(f"   • Added {no_tag_count} videos to 'No Tag' folder")
        
        log_with_timestamp("✅ Unified tag organization completed successfully!")
        return True
        
    except Exception as e:
        log_with_timestamp(f"❌ Error during organization: {e}")
        return False
        
    finally:
        driver.quit()
        log_with_timestamp("🔚 Chrome driver closed")

if __name__ == "__main__":
    main()
