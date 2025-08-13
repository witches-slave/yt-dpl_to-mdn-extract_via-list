#!/usr/bin/env python3
"""
Unified Video Organizer Script
Combines video sitemap parsing and organization into a single workflow:
1. Fetches all video URLs from sitemap or manual crawling of /updates/ pages
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

def get_user_inputs():
    """Get domain and video folder from user"""
    print("=" * 60)
    print("UNIFIED VIDEO ORGANIZER")
    print("=" * 60)
    print()
    
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
        print("Error: Source folder path cannot be empty")
        sys.exit(1)
    
    # Expand paths
    video_folder = os.path.abspath(video_folder)
    
    # Check if folder exists
    if not os.path.exists(video_folder):
        print(f"Error: Source folder does not exist: {video_folder}")
        sys.exit(1)
    
    print(f"\nDomain: {domain}")
    print(f"Source folder: {video_folder}")
    print("="*60 + "\n")
    
    return domain, video_folder

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

def crawl_updates_pages_manually(domain):
    """Manually crawl /updates/ pages to find video URLs"""
    log_with_timestamp("🕷️  Starting manual crawling of /updates/ pages")
    
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("Failed to setup browser for manual crawling")
        return []
    
    all_video_urls = []
    base_updates_url = f"{domain}/updates"
    
    try:
        # Start with the main updates page
        log_with_timestamp(f"Crawling: {base_updates_url}")
        driver.get(base_updates_url)
        time.sleep(3)
        
        # Get pagination info
        pagination_urls = get_pagination_urls(driver, base_updates_url)
        log_with_timestamp(f"Found {len(pagination_urls)} update pages to crawl")
        
        # Crawl each page
        for i, page_url in enumerate(pagination_urls, 1):
            log_with_timestamp(f"Crawling page {i}/{len(pagination_urls)}: {page_url}")
            
            try:
                driver.get(page_url)
                time.sleep(2)
                
                # Extract video URLs from this page
                video_urls = extract_video_urls_from_page(driver, domain)
                all_video_urls.extend(video_urls)
                
                log_with_timestamp(f"  Found {len(video_urls)} videos on this page")
                
            except Exception as e:
                log_with_timestamp(f"  Error crawling page: {e}")
                continue
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in all_video_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        log_with_timestamp(f"🎯 Manual crawling complete: found {len(unique_urls)} unique video URLs")
        return unique_urls
        
    finally:
        driver.quit()

def get_all_video_urls(domain):
    """Get all video URLs via manual crawling of /updates/ pages"""
    log_with_timestamp("🔍 Starting video URL discovery via manual crawling...")
    
    video_urls = crawl_updates_pages_manually(domain)
    
    if not video_urls:
        log_with_timestamp("❌ No video URLs found")
        return []
    
    log_with_timestamp(f"✅ Found {len(video_urls)} video URLs")
    return video_urls

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
            metadata['title'] = h1_element.text.strip()
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
        
        # Extract model with wait
        try:
            # Wait for models section to be present
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.models, .modelName'))
            )
            model_links = driver.find_elements(By.CSS_SELECTOR, '.models a, .modelName a')
            if model_links:
                metadata['model'] = model_links[0].text.strip()
                log_with_timestamp(f"    ✅ Model: {metadata['model']}")
        except:
            log_with_timestamp(f"    ⚠️  No model found")
        
        # Extract tags with wait
        try:
            # Wait for tags section to be present
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.tags'))
            )
            tag_links = driver.find_elements(By.CSS_SELECTOR, '.tags a')
            for tag_link in tag_links:
                tag_text = tag_link.text.strip()
                if tag_text:
                    metadata['tags'].append(tag_text)
            log_with_timestamp(f"    ✅ Tags: {len(metadata['tags'])} found")
        except:
            log_with_timestamp(f"    ⚠️  No tags found")
        
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
            related_blocks = driver.find_elements(By.CSS_SELECTOR, '.relatedVideos .videoBlock')
            for block in related_blocks[:5]:  # Limit to first 5 related videos
                try:
                    title_elem = block.find_element(By.CSS_SELECTOR, 'h3 a')
                    related_title = title_elem.text.strip()
                    related_url = title_elem.get_attribute("href")
                    if related_title and related_url:
                        metadata['related_videos'].append({
                            'title': related_title,
                            'url': related_url
                        })
                except:
                    continue
            log_with_timestamp(f"    ✅ Related videos: {len(metadata['related_videos'])} found")
        except:
            log_with_timestamp(f"    ⚠️  No related videos found")
        
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

# ===== MAIN ORGANIZATION LOGIC =====

def organize_videos_by_metadata(video_folder, video_metadata_list, domain):
    """Organize videos by tags and models using extracted metadata"""
    log_with_timestamp("🗂️  Starting video organization...")
    
    organized_count = 0
    missing_videos = []
    processed_models = {}  # Cache for model images to avoid re-downloading
    
    # Setup browser for model image extraction
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("⚠️  Could not setup browser for model images, continuing without them")
        driver = None
    
    try:
        for metadata in video_metadata_list:
            video_title = metadata.get('title', '')
            if not video_title:
                continue
            
            # Find the actual video file
            video_file = find_video_file(video_folder, video_title)
            
            if not video_file:
                missing_videos.append({
                    'title': video_title,
                    'url': metadata.get('url', ''),
                    'model': metadata.get('model', ''),
                    'tags': metadata.get('tags', [])
                })
                continue
            
            log_with_timestamp(f"Organizing: {video_title}")
            
            # Handle model processing
            model = metadata.get('model', '').strip()
            model_image_url = None
            
            if model:
                clean_model = re.sub(r'[^\w\s-]', '', model).strip()
                model_dir = os.path.join(video_folder, clean_model)
                
                # Get or extract model image URL
                if model in processed_models:
                    model_image_url = processed_models[model]
                elif driver:
                    model_image_url = extract_model_image_url(driver, model, domain)
                    processed_models[model] = model_image_url
                    
                    # Download model image as folder.jpg
                    if model_image_url:
                        folder_jpg_path = os.path.join(model_dir, 'folder.jpg')
                        if not os.path.exists(folder_jpg_path):
                            download_image(model_image_url, folder_jpg_path)
                    
                    # Create actress NFO file
                    create_actress_nfo(model_dir, model, model_image_url)
                    
                    # Small delay to be respectful
                    time.sleep(1)
                
                # Create model symlink
                model_link = os.path.join(model_dir, os.path.basename(video_file))
                if create_relative_symlink(video_file, model_link):
                    log_with_timestamp(f"  → Model symlink: {clean_model}")
            
            # Create NFO file with model image URL
            create_nfo_file(video_file, metadata, model_image_url)
            
            # Download video thumbnail if available
            if metadata.get('thumbnail'):
                thumbnail_path = os.path.splitext(video_file)[0] + '_thumb.jpg'
                download_image(metadata['thumbnail'], thumbnail_path)
            
            # Create symlinks for tags
            for tag in metadata.get('tags', []):
                clean_tag = re.sub(r'[^\w\s-]', '', tag).strip()
                if clean_tag:
                    tag_dir = os.path.join(video_folder, clean_tag)
                    tag_link = os.path.join(tag_dir, os.path.basename(video_file))
                    
                    if create_relative_symlink(video_file, tag_link):
                        log_with_timestamp(f"  → Tag symlink: {clean_tag}")
            
            organized_count += 1
    
    finally:
        if driver:
            driver.quit()
    
    # Print summary
    log_separator()
    log_with_timestamp("📊 ORGANIZATION SUMMARY")
    log_with_timestamp("=" * 40)
    log_with_timestamp(f"✅ Videos organized: {organized_count}")
    log_with_timestamp(f"👤 Models processed: {len(processed_models)}")
    log_with_timestamp(f"❌ Missing videos: {len(missing_videos)}")
    
    if missing_videos:
        log_with_timestamp("\n📋 Missing Videos (found online but not in folder):")
        for missing in missing_videos:
            log_with_timestamp(f"  • {missing['title']}")
            log_with_timestamp(f"    Model: {missing['model']}")
            log_with_timestamp(f"    Tags: {', '.join(missing['tags'])}")
            log_with_timestamp(f"    URL: {missing['url']}")
            log_with_timestamp("")

def main():
    """Main function"""
    try:
        # Get user inputs
        domain, video_folder = get_user_inputs()
        
        # Get all video URLs
        video_urls = get_all_video_urls(domain)
        
        if not video_urls:
            log_with_timestamp("❌ No video URLs found. Exiting.")
            sys.exit(1)
        
        log_with_timestamp(f"🎬 Found {len(video_urls)} videos to process")
        
        # Setup browser for metadata extraction
        driver = setup_headless_browser()
        if not driver:
            log_with_timestamp("❌ Failed to setup browser. Exiting.")
            sys.exit(1)
        
        try:
            # Extract metadata from all videos
            log_with_timestamp("🔍 Extracting metadata from video pages...")
            video_metadata_list = []
            
            for i, video_url in enumerate(video_urls, 1):
                log_with_timestamp(f"Processing {i}/{len(video_urls)}: {video_url}")
                
                metadata = extract_video_metadata(driver, video_url)
                if metadata:
                    video_metadata_list.append(metadata)
                    log_with_timestamp(f"  ✅ Title: {metadata.get('title', 'Unknown')}")
                    log_with_timestamp(f"     Model: {metadata.get('model', 'Unknown')}")
                    log_with_timestamp(f"     Tags: {len(metadata.get('tags', []))} tags")
                else:
                    log_with_timestamp(f"  ❌ Failed to extract metadata")
                
                # Small delay to be respectful
                time.sleep(1)
            
            log_with_timestamp(f"✅ Extracted metadata from {len(video_metadata_list)} videos")
            
            # Organize videos based on extracted metadata
            organize_videos_by_metadata(video_folder, video_metadata_list, domain)
            
            log_with_timestamp("🎉 Video organization completed successfully!")
            
        finally:
            driver.quit()
            
    except KeyboardInterrupt:
        log_with_timestamp("❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_with_timestamp(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
