#!/usr/bin/env python3
"""
All-in-One Video Download and Organization Script
Combines sitemap_video_parser.py, download.py, and unified_video_organizer.py into a single workflow:

1. Extracts video URLs from /updates/ pages
2. Downloads videos (skipping existing files)
3. Extracts metadata and creates NFO files
4. Organizes videos into tag/model folders with symlinks
5. Downloads thumbnails and model images

Features:
- Smart filename truncation to avoid long filename errors
- Duplicate title handling with URL-based naming
- Existing file detection and skip
- NFO and thumbnail creation/update for existing videos
- Complete Jellyfin integration
"""

import os
import sys
import re
import time
import glob
import shutil
import getpass
import hashlib
import requests
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urljoin

# Selenium imports
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ===== UTILITY FUNCTIONS =====

def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def log_separator():
    """Print a clean separator line without timestamp"""
    print()

def log_section(title):
    """Print a section header"""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename)
    return filename.strip()

def truncate_title_smart(title, max_length=200):
    """Smart truncation that preserves meaning while staying under filename limits"""
    if not title:
        return "UNTITLED_VIDEO"
    
    clean_title = sanitize_filename(title)
    if len(clean_title) <= max_length:
        return clean_title
    
    # Create hash for uniqueness
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()[:8]
    available_length = max_length - 11  # Reserve space for " [HASH]"
    
    if available_length < 20:
        return f"VIDEO_{title_hash.upper()}"
    
    truncated = clean_title[:available_length]
    last_space = truncated.rfind(' ')
    if last_space > available_length * 0.7:
        truncated = truncated[:last_space]
    
    return f"{truncated} [{title_hash.upper()}]"

def get_consistent_filename(title, url=None):
    """Get a consistent filename that all operations will use"""
    if not title and url:
        title = create_url_title_from_url(url)
    elif not title:
        title = "UNKNOWN_VIDEO"
    
    return truncate_title_smart(title)

def create_url_title_from_url(url):
    """Create a title from URL (consistent across all operations)"""
    try:
        if "/updates/" in url:
            url_part = url.split("/updates/")[1]
            url_part = url_part.split('?')[0].rstrip('/')
            url_title = url_part.replace('-', ' ').upper()
            return truncate_title_smart(url_title)
    except Exception:
        pass
    return "UNKNOWN_VIDEO"

def check_storage_space(min_gb=10):
    """Check if there's enough free storage space"""
    try:
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024**3)
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        
        log_with_timestamp(f"Storage - Total: {total_gb:.1f}GB, Used: {used_gb:.1f}GB, Free: {free_gb:.1f}GB")
        
        if free_gb < min_gb:
            log_with_timestamp(f"⚠️ Warning: Low disk space ({free_gb:.1f}GB free, {min_gb}GB recommended)")
            response = input("Continue anyway? (y/n): ").strip().lower()
            return response == 'y'
        else:
            log_with_timestamp(f"✅ Sufficient disk space available ({free_gb:.1f}GB free)")
            return True
    except Exception as e:
        log_with_timestamp(f"Could not check storage space: {e}")
        return True

# ===== USER INPUT FUNCTIONS =====

def get_user_inputs():
    """Get all required inputs from user"""
    log_section("SETUP - User Inputs")
    
    # Get domain
    domain = input("Enter the domain (e.g., https://shinybound.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        sys.exit(1)
    
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    domain = domain.rstrip('/')
    
    # Get credentials
    email = input("Enter your email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        sys.exit(1)
    
    password = getpass.getpass("Enter your password: ").strip()
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)
    
    # Get download folder
    current_dir = os.getcwd()
    print(f"\nCurrent directory: {current_dir}")
    download_folder = input("Enter download folder name (will be created in current directory): ").strip()
    if not download_folder:
        print("Error: Download folder cannot be empty")
        sys.exit(1)
    
    download_path = os.path.join(current_dir, download_folder)
    os.makedirs(download_path, exist_ok=True)
    
    # Create tags folder for organization
    tags_path = os.path.join(current_dir, "tags")
    os.makedirs(tags_path, exist_ok=True)
    
    print(f"\nConfiguration:")
    print(f"Domain: {domain}")
    print(f"Email: {email}")
    print(f"Password: [HIDDEN]")
    print(f"Download folder: {download_path}")
    print(f"Tags folder: {tags_path}")
    
    return domain, email, password, download_path, tags_path

# ===== BROWSER SETUP =====

def setup_headless_browser():
    """Setup headless Chrome browser with all the options from working download.py"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Don't load images for speed
    chrome_options.add_argument("--disable-web-security")  # May help with loading speed
    chrome_options.add_argument("--aggressive-cache-discard")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
    
    try:
        # Use webdriver-manager to automatically handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        log_with_timestamp(f"Error setting up browser: {e}")
        return None

def perform_login(driver, email, password, domain):
    """Perform automated login using the proven approach from download.py"""
    try:
        log_with_timestamp("🔐 Starting automated login...")
        
        login_url = f"{domain}/login"
        log_with_timestamp(f"Navigating to: {login_url}")
        driver.get(login_url)
        time.sleep(5)
        
        # Handle age verification popup with proper waiting
        try:
            log_with_timestamp("Checking for age verification popup...")
            age_verify_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ageVerifyPass"))
            )
            age_verify_button.click()
            time.sleep(3)
            log_with_timestamp("✅ Age verification popup handled")
        except:
            log_with_timestamp("ℹ️ No age verification popup found, proceeding...")
        
        # Wait for page to fully load after popup closes
        wait = WebDriverWait(driver, 10)
        
        # Find and extract CSRF token - try multiple selectors
        csrf_token = None
        try:
            csrf_token_element = wait.until(EC.presence_of_element_located((By.NAME, "_token")))
            csrf_token = csrf_token_element.get_attribute("value")
        except:
            # Try alternative selectors
            try:
                csrf_token_element = driver.find_element(By.CSS_SELECTOR, "input[name='_token']")
                csrf_token = csrf_token_element.get_attribute("value")
            except:
                try:
                    # Try hidden input
                    csrf_token_element = driver.find_element(By.CSS_SELECTOR, "input[type='hidden'][name='_token']")
                    csrf_token = csrf_token_element.get_attribute("value")
                except:
                    pass
        
        if csrf_token:
            log_with_timestamp(f"✅ Found CSRF token: {csrf_token[:20]}...")
        else:
            log_with_timestamp("⚠️ Could not find CSRF token")
        
        # Wait for form elements to be clickable
        log_with_timestamp("🔍 Waiting for form elements to be interactable...")
        
        # Try different selectors for email field - including the main form selectors
        email_field = None
        email_selectors = [
            "form.login_form input[name='email']",  # Main form
            ".accLoginDetails input[name='email']",  # Main login area
            "input[name='email']", 
            "input[type='email']", 
            "#email", 
            ".email"
        ]
        
        for selector in email_selectors:
            try:
                email_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                log_with_timestamp(f"✅ Found email field with selector: {selector}")
                break
            except:
                continue
        
        if not email_field:
            log_with_timestamp("❌ Could not find email field")
            return False
        
        # Try different selectors for password field
        password_field = None
        password_selectors = [
            "form.login_form input[name='password']",  # Main form
            ".accLoginDetails input[name='password']",  # Main login area
            "input[name='password']", 
            "input[type='password']", 
            "#password", 
            ".password"
        ]
        
        for selector in password_selectors:
            try:
                password_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                log_with_timestamp(f"✅ Found password field with selector: {selector}")
                break
            except:
                continue
        
        if not password_field:
            log_with_timestamp("❌ Could not find password field")
            return False
        
        # Clear and fill fields using JavaScript if normal method fails
        log_with_timestamp("📝 Filling in credentials...")
        try:
            email_field.clear()
            email_field.send_keys(email)
        except:
            # Use JavaScript as fallback
            driver.execute_script(f"arguments[0].value = '{email}';", email_field)
        
        try:
            password_field.clear()
            password_field.send_keys(password)
        except:
            # Use JavaScript as fallback
            driver.execute_script(f"arguments[0].value = '{password}';", password_field)
        
        time.sleep(2)
        
        # Find and click submit button - try multiple selectors including the main form
        submit_button = None
        submit_selectors = [
            "form.login_form input[type='submit']",  # Main form submit
            ".acctLogin",  # Main form submit button class
            "input.acctLogin",  # Specific submit button
            "button[type='submit']", 
            "input[type='submit']", 
            ".btn-primary", 
            ".login-btn", 
            "form button"
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                log_with_timestamp(f"✅ Found submit button with selector: {selector}")
                break
            except:
                continue
        
        if not submit_button:
            # Try submitting form directly
            try:
                form = driver.find_element(By.CSS_SELECTOR, "form.login_form, .accLoginDetails form")
                form.submit()
                log_with_timestamp("✅ Submitted form directly")
            except:
                log_with_timestamp("❌ Could not find submit button or form")
                return False
        else:
            # Click submit button using JavaScript to avoid interactability issues
            driver.execute_script("arguments[0].click();", submit_button)
            log_with_timestamp("✅ Clicked submit button")
        
        # Wait for redirect/response
        time.sleep(8)  # Increased wait time
        
        # Check if login was successful by looking for certain indicators
        current_url = driver.current_url
        log_with_timestamp(f"📍 After login redirect: {current_url}")
        
        # Get cookies after login
        cookies = driver.get_cookies()
        log_with_timestamp(f"🍪 Got {len(cookies)} cookies after login")
        
        # Check for expected authentication cookies (these may vary by site)
        auth_cookies = {}
        for cookie in cookies:
            # Look for common session/auth cookie patterns
            if any(keyword in cookie['name'].lower() for keyword in ['session', 'auth', 'token', 'login', 'xsrf', 'csrf']):
                auth_cookies[cookie['name']] = cookie['value']
                log_with_timestamp(f"  ✓ {cookie['name']}: {cookie['value'][:20]}...")
        
        # Also check if we're redirected away from login page
        login_success = False
        if current_url != login_url and len(auth_cookies) >= 1:
            login_success = True
        elif len(auth_cookies) >= 1:  # At least 1 authentication-related cookie
            login_success = True
        
        if login_success:
            log_with_timestamp("✅ Login appears successful")
            return True
        else:
            log_with_timestamp("❌ Login may have failed - checking page content...")
            # Check for error messages
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error, .invalid-feedback")
                if error_elements:
                    for error in error_elements:
                        if error.text:
                            log_with_timestamp(f"❌ Error message found: {error.text}")
            except:
                pass
            return False
            
    except Exception as e:
        log_with_timestamp(f"❌ Error during automated login: {e}")
        return False

def extract_cookies(driver):
    """Extract cookies from driver and build cookie string"""
    cookies = driver.get_cookies()
    cookie_parts = []
    
    for cookie in cookies:
        cookie_parts.append(f"{cookie['name']}={cookie['value']}")
    
    return '; '.join(cookie_parts)

# ===== URL EXTRACTION =====

def get_pagination_urls(driver, base_url):
    """Get all pagination URLs for updates pages - using the working logic from sitemap_video_parser.py"""
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
                                page_url_pattern = href.replace(f"/page/{page_num}", "/page={}")
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
                                            page_url_pattern = href.replace(f"/page/{text_page_num}", "/page={}")
                            except:
                                pass
                        
                        # Update max_page if we found a higher number in URL
                        if page_num and page_num > max_page:
                            max_page = page_num
                            
                except Exception:
                    continue
            
            # If we found a pattern and max page, generate all URLs
            if page_url_pattern and max_page > 1:
                log_with_timestamp(f"🔢 Found pagination: pages 1 to {max_page}")
                log_with_timestamp(f"📋 Pattern: {page_url_pattern}")
                
                # Generate URLs for all pages from 2 to max_page (1 is already included)
                for page_num in range(2, max_page + 1):
                    page_url = page_url_pattern.format(page_num)
                    pagination_urls.append(page_url)
                
                log_with_timestamp(f"✅ Generated {len(pagination_urls)} pagination URLs (pages 1-{max_page})")
            
            # Fallback: if we couldn't determine pattern, use visible links only
            elif len(pagination_links) > 0:
                log_with_timestamp("⚠️ Could not determine pagination pattern, using visible links only")
                for link in pagination_links:
                    try:
                        href = link.get_attribute("href")
                        if href and href != "#" and href not in pagination_urls:
                            if ("/updates" in href and 
                                ("page=" in href or "/page/" in href)):
                                pagination_urls.append(href)
                    except Exception:
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
            log_with_timestamp("ℹ️ No pagination found, using single page")
        
        return pagination_urls
        
    except Exception as e:
        log_with_timestamp(f"⚠️ Error finding pagination: {e}")
        return pagination_urls

def extract_videos_from_page(driver, domain):
    """Extract video URLs and titles from current page - using working logic from sitemap_video_parser.py"""
    video_data = []
    seen_urls = set()  # Track URLs to avoid duplicates within the same page
    
    # Try multiple selectors to find video links - same as working script
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
                
                elements_processed = 0
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
                                # Skip if we've already processed this URL on this page
                                if href in seen_urls:
                                    continue
                                
                                seen_urls.add(href)
                                elements_processed += 1
                                
                                # Try to extract title from the element - same as working script
                                title = None
                                
                                # Try various ways to get the title
                                try:
                                    # Try title attribute first
                                    title = element.get_attribute("title")
                                    if not title:
                                        # Try alt attribute of image inside
                                        img = element.find_element(By.TAG_NAME, "img")
                                        title = img.get_attribute("alt")
                                    if not title:
                                        # Try text content
                                        title = element.text.strip()
                                    if not title:
                                        # Try aria-label
                                        title = element.get_attribute("aria-label")
                                        
                                    # Clean the title if we found one
                                    if title:
                                        title = get_consistent_filename(title)
                                        
                                except Exception:
                                    title = None
                                
                                video_data.append({
                                    'url': href,
                                    'title': title,
                                    'url_title': None  # Will be filled if needed for duplicates
                                })
                    except Exception:
                        continue
                
                log_with_timestamp(f"    → Processed {elements_processed} unique videos from this selector")
                break  # Use first working selector
        except Exception:
            continue
    
    log_with_timestamp(f"  Total unique videos extracted from page: {len(video_data)}")
    return video_data

def crawl_all_videos(driver, domain):
    """Crawl all /updates/ pages to find video URLs"""
    log_section("PHASE 1 - Extracting Video URLs")
    
    all_video_data = []
    base_updates_url = f"{domain}/updates"
    
    try:
        log_with_timestamp(f"Starting crawl of: {base_updates_url}")
        driver.get(base_updates_url)
        time.sleep(3)
        
        pagination_urls = get_pagination_urls(driver, base_updates_url)
        log_with_timestamp(f"Found {len(pagination_urls)} pages to crawl")
        
        for i, page_url in enumerate(pagination_urls, 1):
            log_with_timestamp(f"Crawling page {i}/{len(pagination_urls)}: {page_url}")
            
            try:
                driver.get(page_url)
                time.sleep(2)
                
                video_data = extract_videos_from_page(driver, domain)
                all_video_data.extend(video_data)
                
                log_with_timestamp(f"  Found {len(video_data)} videos on this page")
                
            except Exception as e:
                log_with_timestamp(f"  Error crawling page: {e}")
                continue
        
        # Remove duplicates
        unique_data = []
        seen_urls = set()
        for data in all_video_data:
            if data['url'] not in seen_urls:
                unique_data.append(data)
                seen_urls.add(data['url'])
        
        log_with_timestamp(f"✅ Found {len(unique_data)} unique video URLs")
        return unique_data
        
    except Exception as e:
        log_with_timestamp(f"Error during crawling: {e}")
        return []

def detect_duplicate_titles(video_data):
    """Detect and handle duplicate titles"""
    log_with_timestamp("Checking for duplicate titles...")
    
    title_counts = {}
    for data in video_data:
        title = data['title']
        if title:
            title_lower = title.lower()
            if title_lower not in title_counts:
                title_counts[title_lower] = []
            title_counts[title_lower].append(data)
    
    duplicates_found = 0
    for title_lower, entries in title_counts.items():
        if len(entries) > 1:
            duplicates_found += len(entries)
            log_with_timestamp(f"  Duplicate title: '{entries[0]['title']}' ({len(entries)} videos)")
            
            for entry in entries:
                url_title = create_url_title_from_url(entry['url'])
                if url_title:
                    entry['url_title'] = url_title
    
    if duplicates_found > 0:
        log_with_timestamp(f"✅ Processed {duplicates_found} duplicate titles")
    else:
        log_with_timestamp("✅ No duplicate titles found")
    
    return video_data

# ===== FILE CHECKING =====

def check_existing_files(video_data, download_folder):
    """Check which videos already exist and what's missing (NFO, thumbnails)"""
    log_section("PHASE 2 - Checking Existing Files")
    
    existing_files = []
    missing_files = []
    need_metadata = []
    
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    try:
        existing_video_files = []
        for ext in video_extensions:
            pattern = os.path.join(download_folder, f"*{ext}")
            existing_video_files.extend(glob.glob(pattern))
        
        log_with_timestamp(f"Found {len(existing_video_files)} existing video files")
        
        for entry in video_data:
            title = entry.get('url_title') or entry.get('title') or "UNKNOWN_VIDEO"
            safe_title = get_consistent_filename(title)
            
            # Check if video file exists
            video_found = False
            video_path = None
            
            for video_file in existing_video_files:
                video_name = os.path.splitext(os.path.basename(video_file))[0]
                if video_name.lower() == safe_title.lower():
                    video_found = True
                    video_path = video_file
                    break
            
            if video_found:
                existing_files.append(entry)
                
                # Check if NFO and thumbnail exist
                nfo_path = os.path.splitext(video_path)[0] + '.nfo'
                jpg_path = os.path.splitext(video_path)[0] + '.jpg'
                
                needs_nfo = not os.path.exists(nfo_path)
                needs_thumb = not os.path.exists(jpg_path)
                
                if needs_nfo or needs_thumb:
                    need_metadata.append({
                        'entry': entry,
                        'video_path': video_path,
                        'needs_nfo': needs_nfo,
                        'needs_thumb': needs_thumb
                    })
            else:
                missing_files.append(entry)
        
        log_with_timestamp(f"✅ Analysis complete:")
        log_with_timestamp(f"   - Existing videos: {len(existing_files)}")
        log_with_timestamp(f"   - Missing videos: {len(missing_files)}")
        log_with_timestamp(f"   - Need metadata: {len(need_metadata)}")
        
        return existing_files, missing_files, need_metadata
        
    except Exception as e:
        log_with_timestamp(f"Error checking existing files: {e}")
        return [], video_data, []

# ===== DOWNLOAD FUNCTIONS =====

def download_video(manifest_url, cookie, video_title, domain, download_folder):
    """Download a single video using yt-dlp with the proven approach from download.py"""
    try:
        if not manifest_url:
            log_with_timestamp(f"  ❌ No manifest URL provided")
            return False
        
        safe_title = get_consistent_filename(video_title)
        
        cmd = [
            "yt-dlp",
            "--concurrent-fragments", "8",
            "--fragment-retries", "3",
            "--abort-on-error"
        ]
        
        # Add referer if domain is provided
        if domain:
            cmd.extend(["--referer", domain])
        
        # Add cookie header
        if cookie:
            cmd.extend(["--add-header", f"Cookie:{cookie}"])
        
        # Add custom filename and output folder
        if video_title and download_folder:
            output_template = os.path.join(download_folder, f"{safe_title}.%(ext)s")
            cmd.extend(["-o", output_template])
        elif video_title:
            cmd.extend(["-o", f"{safe_title}.%(ext)s"])
        elif download_folder:
            cmd.extend(["-o", os.path.join(download_folder, "%(title)s.%(ext)s")])
        
        cmd.append(manifest_url)
        
        log_with_timestamp(f"  📥 Starting download: {safe_title}")
        
        # Run yt-dlp with proper error handling
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            log_with_timestamp(f"  ✅ Download complete: {safe_title}")
            return True
        else:
            log_with_timestamp(f"  ❌ Download failed: {safe_title}")
            if result.stderr:
                log_with_timestamp(f"  Error: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        log_with_timestamp(f"  ❌ Download timeout for {video_title}")
        return False
    except Exception as e:
        log_with_timestamp(f"  ❌ Download error for {video_title}: {e}")
        return False

def extract_manifest_url(driver, page_url, domain):
    """Extract manifest URL from video page using proven approach from download.py"""
    try:
        # Clear previous requests
        del driver.requests
        
        driver.get(page_url)
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        
        # Check if we were redirected to the main updates page (dead link)
        current_url = driver.current_url
        updates_main_page = f"{domain}/updates"
        
        if current_url == updates_main_page or current_url == f"{updates_main_page}/":
            log_with_timestamp(f"⚠️ Page redirected to main updates page - dead link")
            return None
        
        # Try to trigger video player by looking for and clicking play button
        try:
            # Wait for any play buttons to appear
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe"))
                )
            except:
                pass
            
            play_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe")
            if play_buttons:
                for button in play_buttons[:2]:  # Try only first 2 elements
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.3)
                    except:
                        pass
        except Exception:
            pass
        
        # Wait and monitor for authenticated URLs
        log_with_timestamp("  🔍 Waiting for video player to load and authenticate...")
        
        authenticated_url = None
        basic_url = None
        
        # Monitor requests for up to 2 seconds
        for i in range(1):  # 1 iteration of 2 seconds
            time.sleep(2)
            
            # Check all requests so far
            for request in driver.requests:
                if request.url and '/manifest/video.mpd' in request.url:
                    # Look for JWT token pattern (JWT tokens contain dots and are base64-like)
                    if '.eyJ' in request.url:  # JWT tokens have this pattern
                        authenticated_url = request.url
                        log_with_timestamp(f"  ✅ Found AUTHENTICATED manifest URL with JWT token!")
                        return authenticated_url
                    elif len(request.url) > 200:
                        # Long URLs are likely authenticated
                        authenticated_url = request.url
                        log_with_timestamp(f"  ✅ Found LONG manifest URL (likely authenticated)!")
                        return authenticated_url
                    else:
                        basic_url = request.url
            
            # If we found an authenticated URL, break early
            if authenticated_url:
                break
        
        # Additional wait and check for any video stream URLs
        time.sleep(1)
        
        for request in driver.requests:
            if request.url and any(pattern in request.url.lower() for pattern in ['stream', 'cloudflare']):
                if '/manifest/video.mpd' in request.url:
                    log_with_timestamp(f"  ✅ Found video stream manifest URL")
                    return request.url
                elif request.url.count('.') >= 2 and len(request.url) > 150:
                    # This might be an authenticated URL without explicit /manifest/video.mpd
                    potential_manifest = request.url
                    if not potential_manifest.endswith('/manifest/video.mpd'):
                        potential_manifest += '/manifest/video.mpd'
                    log_with_timestamp(f"  ✅ Found potential authenticated URL, trying with manifest path")
                    return potential_manifest
        
        # Fall back to basic URL if we have one
        if basic_url:
            log_with_timestamp("  ⚠️ Warning: Only found basic manifest URL, this may only download a preview")
            return basic_url
        else:
            log_with_timestamp(f"  ❌ No manifest URL found")
            return None
        
    except Exception as e:
        log_with_timestamp(f"  ❌ Error extracting manifest URL: {e}")
        return None

def download_missing_videos(driver, missing_videos, cookie, domain, download_folder):
    """Download all missing videos"""
    log_section("PHASE 3 - Downloading Missing Videos")
    
    successful_downloads = []
    failed_downloads = []
    
    for i, entry in enumerate(missing_videos, 1):
        try:
            title = entry.get('url_title') or entry.get('title') or "UNKNOWN_VIDEO"
            log_with_timestamp(f"Processing {i}/{len(missing_videos)}: {title}")
            
            # Extract manifest URL
            manifest_url = extract_manifest_url(driver, entry['url'], domain)
            
            if not manifest_url:
                log_with_timestamp(f"  ❌ Could not extract manifest URL")
                failed_downloads.append(entry)
                continue
            
            # Download video
            if download_video(manifest_url, cookie, title, domain, download_folder):
                successful_downloads.append(entry)
            else:
                failed_downloads.append(entry)
            
            # Small delay between downloads
            time.sleep(2)
            
        except Exception as e:
            log_with_timestamp(f"  ❌ Error processing {title}: {e}")
            failed_downloads.append(entry)
            continue
    
    log_with_timestamp(f"✅ Download phase complete:")
    log_with_timestamp(f"   - Successful: {len(successful_downloads)}")
    log_with_timestamp(f"   - Failed: {len(failed_downloads)}")
    
    return successful_downloads, failed_downloads

# ===== METADATA EXTRACTION =====

def extract_video_metadata(driver, video_url):
    """Extract comprehensive metadata from a video page - using working logic from unified_video_organizer.py"""
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
            log_with_timestamp(f"    ⚠️ Timeout waiting for tags/models sections to load")
        
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
            log_with_timestamp(f"    ⚠️ Could not extract title: {e}")
        
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
                log_with_timestamp(f"    ⚠️ No thumbnail found")
        
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
                log_with_timestamp(f"    ⚠️ No description found")
        
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
                log_with_timestamp(f"    ⚠️ No model found with any selector")
                
        except Exception as e:
            log_with_timestamp(f"    ❌ Error extracting model: {e}")
        
        # Extract tags with enhanced debugging
        try:
            # Multiple selectors to try for tags
            tag_selectors = [
                '.tags ul li a',  # Main structure: div.tags > ul > li > a
                '.tags a',
                'div.tags ul li a',
                '.tag-links a',
                '.genre a',
                'a[href*="/tags/"]'
            ]
            
            tags_found = False
            log_with_timestamp(f"    🔍 Searching for tags...")
            
            for selector in tag_selectors:
                try:
                    tag_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    if tag_links:
                        log_with_timestamp(f"    ✅ Found {len(tag_links)} tags with selector '{selector}'")
                        
                        for tag_link in tag_links:
                            try:
                                # Get tag text, removing any icon text
                                tag_text = tag_link.text.strip()
                                
                                # If text is empty, try JavaScript approach
                                if not tag_text:
                                    try:
                                        tag_text = driver.execute_script(
                                            "return arguments[0].textContent || arguments[0].innerText;", 
                                            tag_link
                                        ).strip()
                                    except:
                                        pass
                                
                                # Clean up tag text and add if valid
                                if tag_text and len(tag_text) > 1 and tag_text not in metadata['tags']:
                                    # Remove common icon text patterns
                                    tag_text = re.sub(r'^[\s\n]+|[\s\n]+$', '', tag_text)  # Trim whitespace/newlines
                                    
                                    if tag_text and tag_text not in metadata['tags']:
                                        metadata['tags'].append(tag_text)
                            except Exception as e:
                                log_with_timestamp(f"        ⚠️ Error processing tag: {e}")
                                continue
                        
                        if metadata['tags']:
                            log_with_timestamp(f"    ✅ Tags found: {', '.join(metadata['tags'])}")
                            tags_found = True
                            break
                        else:
                            log_with_timestamp(f"    🔍 Selector '{selector}' found elements but no valid tags")
                            
                except Exception as e:
                    log_with_timestamp(f"    🔍 Selector '{selector}' failed: {e}")
                    continue
            
            if not tags_found:
                log_with_timestamp(f"    ⚠️ No tags found with any selector")
                
        except Exception as e:
            log_with_timestamp(f"    ❌ Error extracting tags: {e}")
        
        # Extract video info (duration, photos, date)
        try:
            info_selectors = [
                '.contentInfo li',
                '.video-info li',
                '.details li'
            ]
            
            for selector in info_selectors:
                try:
                    info_items = driver.find_elements(By.CSS_SELECTOR, selector)
                    if info_items:
                        log_with_timestamp(f"    ✅ Found {len(info_items)} info items")
                        for item in info_items:
                            try:
                                text = item.text.strip()
                                if text:
                                    if 'Runtime:' in text or 'Duration:' in text:
                                        metadata['duration'] = text.split(':', 1)[1].strip()
                                        log_with_timestamp(f"    ✅ Duration: {metadata['duration']}")
                                    elif 'Photos:' in text:
                                        metadata['photos'] = text.split(':', 1)[1].strip()
                                        log_with_timestamp(f"    ✅ Photos: {metadata['photos']}")
                                    elif 'Added:' in text or 'Date:' in text:
                                        metadata['date'] = text.split(':', 1)[1].strip()
                                        log_with_timestamp(f"    ✅ Date: {metadata['date']}")
                            except Exception:
                                continue
                        break
                except Exception:
                    continue
        except:
            log_with_timestamp(f"    ⚠️ No video info found")
        
        # Extract related videos
        try:
            related_selectors = [
                '.relatedVideos a',
                '.similar a',
                '.related-content a'
            ]
            
            for selector in related_selectors:
                try:
                    related_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    if related_links:
                        for link in related_links[:5]:  # Limit to 5 related videos
                            try:
                                title = link.get_attribute('title') or link.text.strip()
                                if title and len(title) > 3:
                                    metadata['related_videos'].append({'title': title})
                            except:
                                continue
                        
                        if metadata['related_videos']:
                            log_with_timestamp(f"    ✅ Found {len(metadata['related_videos'])} related videos")
                            break
                except Exception:
                    continue
        except:
            log_with_timestamp(f"    ⚠️ No related videos found")
        
        return metadata
        
    except Exception as e:
        log_with_timestamp(f"    ❌ Error extracting metadata from {video_url}: {e}")
        return None

def download_image(url, save_path):
    """Download image from URL"""
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

def extract_model_image_url(driver, model_name, domain):
    """Extract model image URL from model page - using working logic from unified_video_organizer.py"""
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
        
        log_with_timestamp(f"  ⚠️ No model image found for {model_name}")
        return None
        
    except Exception as e:
        log_with_timestamp(f"  ❌ Error extracting model image: {e}")
        return None

def create_actress_nfo(model_dir, model_name, model_image_url):
    """Create actress NFO file for model directory - using working logic from unified_video_organizer.py"""
    try:
        actress_nfo_path = os.path.join(model_dir, "actress.nfo")
        
        # Use local folder.jpg instead of remote URL for better performance
        local_image_path = "folder.jpg"
        
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<person>
    <name>{model_name}</name>
    <type>Actor</type>
    <thumb>{local_image_path}</thumb>
</person>"""
        
        with open(actress_nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        log_with_timestamp(f"  ✅ Created actress.nfo for {model_name}")
        return True
        
    except Exception as e:
        log_with_timestamp(f"  ❌ Error creating actress NFO: {e}")
        return False

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

def create_nfo_file(video_path, metadata):
    """Create NFO file for video"""
    try:
        nfo_path = os.path.splitext(video_path)[0] + '.nfo'
        
        safe_title = get_consistent_filename(metadata.get('title', ''))
        
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>{safe_title}</title>
    <plot>{metadata.get('description', '')}</plot>
    <studio>{urlparse(metadata.get('url', '')).netloc}</studio>
    <premiered>{metadata.get('date', '')}</premiered>
    <runtime>{metadata.get('duration', '')}</runtime>
    <thumb>{metadata.get('thumbnail', '')}</thumb>
    <year>{metadata.get('date', '').split(' ')[-1] if metadata.get('date') else ''}</year>
    <dateadded>{datetime.now().isoformat()}</dateadded>
"""
        
        # Add model as actor
        if metadata.get('model'):
            model_image = f"../model {metadata['model']}/folder.jpg"
            nfo_content += f"""    <actor>
        <name>{metadata['model']}</name>
        <thumb>{model_image}</thumb>
    </actor>
"""
        
        # Add tags as genres
        for tag in metadata.get('tags', []):
            nfo_content += f"    <genre>{tag}</genre>\n"
        
        # Add related videos
        for related in metadata.get('related_videos', []):
            nfo_content += f"    <similar>{related['title']}</similar>\n"
        
        # Add source URL as tag
        if metadata.get('url'):
            nfo_content += f"    <tag>Source: {metadata['url']}</tag>\n"
        
        nfo_content += "</movie>"
        
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        return True
    except Exception as e:
        log_with_timestamp(f"Error creating NFO: {e}")
        return False

def process_metadata_for_files(driver, files_needing_metadata):
    """Process metadata for existing files that need NFO/thumbnails"""
    log_section("PHASE 4 - Creating Missing Metadata")
    
    processed_count = 0
    
    for item in files_needing_metadata:
        try:
            entry = item['entry']
            video_path = item['video_path']
            needs_nfo = item['needs_nfo']
            needs_thumb = item['needs_thumb']
            
            title = entry.get('url_title') or entry.get('title') or "UNKNOWN_VIDEO"
            log_with_timestamp(f"Processing metadata for: {title}")
            
            # Extract metadata
            metadata = extract_video_metadata(driver, entry['url'])
            if not metadata:
                log_with_timestamp(f"  ❌ Could not extract metadata")
                continue
            
            # Create NFO if needed
            if needs_nfo:
                if create_nfo_file(video_path, metadata):
                    log_with_timestamp(f"  ✅ Created NFO file")
                else:
                    log_with_timestamp(f"  ❌ Failed to create NFO file")
            
            # Download thumbnail if needed
            if needs_thumb and metadata.get('thumbnail'):
                thumb_path = os.path.splitext(video_path)[0] + '.jpg'
                if download_image(metadata['thumbnail'], thumb_path):
                    log_with_timestamp(f"  ✅ Downloaded thumbnail")
                else:
                    log_with_timestamp(f"  ❌ Failed to download thumbnail")
            
            processed_count += 1
            time.sleep(1)  # Small delay
            
        except Exception as e:
            log_with_timestamp(f"  ❌ Error processing metadata: {e}")
            continue
    
    log_with_timestamp(f"✅ Metadata processing complete: {processed_count} files processed")

# ===== ORGANIZATION FUNCTIONS =====

def create_relative_symlink(target_path, link_path):
    """Create a relative symlink"""
    try:
        link_dir = os.path.dirname(link_path)
        rel_path = os.path.relpath(target_path, link_dir)
        
        os.makedirs(link_dir, exist_ok=True)
        
        if os.path.islink(link_path):
            os.unlink(link_path)
        
        os.symlink(rel_path, link_path)
        return True
    except Exception as e:
        log_with_timestamp(f"Error creating symlink: {e}")
        return False

def get_all_models_cache(driver, domain):
    """Get all models and their images"""
    models_cache = {}
    
    try:
        models_url = f"{domain}/models"
        log_with_timestamp(f"Fetching models from: {models_url}")
        
        driver.get(models_url)
        time.sleep(3)
        
        model_blocks = driver.find_elements(By.CSS_SELECTOR, '.allModels .modelBlock')
        
        for block in model_blocks:
            try:
                model_name = block.find_element(By.CSS_SELECTOR, 'a').text.strip()
                img_element = block.find_element(By.CSS_SELECTOR, 'img')
                img_url = img_element.get_attribute('src')
                
                if model_name and img_url:
                    models_cache[model_name] = img_url
                    
            except Exception:
                continue
        
        log_with_timestamp(f"Cached {len(models_cache)} models")
        return models_cache
        
    except Exception as e:
        log_with_timestamp(f"Error caching models: {e}")
        return {}

def organize_videos(driver, all_videos, download_folder, tags_folder, domain):
    """Organize all videos into tag/model folders"""
    log_section("PHASE 5 - Organizing Videos")
    
    # Get models cache
    models_cache = get_all_models_cache(driver, domain)
    
    organized_count = 0
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Get all video files in download folder
    video_files = []
    for ext in video_extensions:
        pattern = os.path.join(download_folder, f"*{ext}")
        video_files.extend(glob.glob(pattern))
    
    log_with_timestamp(f"Found {len(video_files)} video files to organize")
    
    for video_file in video_files:
        try:
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            
            # Find matching entry in video data
            matching_entry = None
            for entry in all_videos:
                title = entry.get('url_title') or entry.get('title') or "UNKNOWN_VIDEO"
                safe_title = get_consistent_filename(title)
                if safe_title.lower() == video_name.lower():
                    matching_entry = entry
                    break
            
            if not matching_entry:
                log_with_timestamp(f"  ⚠️ No metadata found for: {video_name}")
                continue
            
            log_with_timestamp(f"  Organizing: {video_name}")
            
            # Extract metadata if not already done
            metadata = extract_video_metadata(driver, matching_entry['url'])
            if not metadata:
                continue
            
            # Create NFO file if not exists
            nfo_path = os.path.splitext(video_file)[0] + '.nfo'
            if not os.path.exists(nfo_path):
                create_nfo_file(video_file, metadata)
            
            # Download thumbnail if not exists
            thumb_path = os.path.splitext(video_file)[0] + '.jpg'
            if not os.path.exists(thumb_path) and metadata.get('thumbnail'):
                download_image(metadata['thumbnail'], thumb_path)
            
            # Create source folder symlink
            source_folder = os.path.join(tags_folder, f"source {os.path.basename(download_folder)}")
            source_link = os.path.join(source_folder, os.path.basename(video_file))
            create_relative_symlink(video_file, source_link)
            
            # Create tag folder symlinks
            for tag in metadata.get('tags', []):
                tag_folder = os.path.join(tags_folder, f"tag {tag}")
                tag_link = os.path.join(tag_folder, os.path.basename(video_file))
                create_relative_symlink(video_file, tag_link)
            
            # Create model folder symlink and download model image
            model = metadata.get('model', '').strip()
            if model:
                model_folder = os.path.join(tags_folder, f"model {model}")
                model_link = os.path.join(model_folder, os.path.basename(video_file))
                create_relative_symlink(video_file, model_link)
                
                # Download model image and create actress NFO
                model_image_path = os.path.join(model_folder, "folder.jpg")
                if not os.path.exists(model_image_path) and model in models_cache:
                    download_image(models_cache[model], model_image_path)
                
                # Create actress NFO using the proper function
                actress_nfo_path = os.path.join(model_folder, "actress.nfo")
                if not os.path.exists(actress_nfo_path):
                    create_actress_nfo(model_folder, model, models_cache.get(model))
            
            # Create untagged folder if no tags
            if not metadata.get('tags'):
                untagged_folder = os.path.join(tags_folder, "tag no tag")
                untagged_link = os.path.join(untagged_folder, os.path.basename(video_file))
                create_relative_symlink(video_file, untagged_link)
            
            organized_count += 1
            
        except Exception as e:
            log_with_timestamp(f"  ❌ Error organizing {video_file}: {e}")
            continue
    
    log_with_timestamp(f"✅ Organization complete: {organized_count} videos organized")

# ===== MAIN FUNCTION =====

def main():
    """Main function that orchestrates the entire workflow"""
    print("=" * 80)
    print(" ALL-IN-ONE VIDEO DOWNLOAD AND ORGANIZATION SCRIPT")
    print("=" * 80)
    print()
    print("This script will:")
    print("1. Extract video URLs from /updates/ pages")
    print("2. Check for existing files and missing metadata") 
    print("3. Download missing videos")
    print("4. Create NFO files and download thumbnails")
    print("5. Organize videos into tag/model folders")
    print()
    
    try:
        # Get user inputs
        domain, email, password, download_folder, tags_folder = get_user_inputs()
        
        # Check storage space
        if not check_storage_space():
            print("Exiting due to insufficient storage space.")
            return
        
        # Setup browser and login
        log_section("SETUP - Browser and Authentication")
        driver = setup_headless_browser()
        if not driver:
            log_with_timestamp("❌ Failed to setup browser")
            return
        
        try:
            if not perform_login(driver, email, password, domain):
                log_with_timestamp("❌ Login failed")
                return
            
            cookie = extract_cookies(driver)
            log_with_timestamp(f"✅ Authentication complete")
            
            # Phase 1: Extract all video URLs
            all_videos = crawl_all_videos(driver, domain)
            if not all_videos:
                log_with_timestamp("❌ No videos found")
                return
            
            # Handle duplicate titles
            all_videos = detect_duplicate_titles(all_videos)
            
            # Phase 2: Check existing files
            existing_files, missing_files, need_metadata = check_existing_files(all_videos, download_folder)
            
            # Phase 3: Download missing videos
            if missing_files:
                successful_downloads, failed_downloads = download_missing_videos(
                    driver, missing_files, cookie, domain, download_folder
                )
                
                if failed_downloads:
                    log_with_timestamp(f"⚠️ {len(failed_downloads)} downloads failed")
                    for failed in failed_downloads:
                        title = failed.get('url_title') or failed.get('title') or "UNKNOWN_VIDEO"
                        log_with_timestamp(f"  - {title}")
            else:
                log_with_timestamp("✅ No videos need downloading")
            
            # Phase 4: Process metadata for existing files
            if need_metadata:
                process_metadata_for_files(driver, need_metadata)
            
            # Phase 5: Organize all videos
            organize_videos(driver, all_videos, download_folder, tags_folder, domain)
            
            # Final summary
            log_section("WORKFLOW COMPLETE")
            log_with_timestamp(f"✅ All operations completed successfully!")
            log_with_timestamp(f"   - Total videos found: {len(all_videos)}")
            log_with_timestamp(f"   - Existing files: {len(existing_files)}")
            log_with_timestamp(f"   - Downloaded: {len(missing_files) - (len(failed_downloads) if 'failed_downloads' in locals() else 0)}")
            log_with_timestamp(f"   - Download folder: {download_folder}")
            log_with_timestamp(f"   - Organization folder: {tags_folder}")
            log_with_timestamp("")
            log_with_timestamp("🎉 Ready for Jellyfin!")
            
        finally:
            driver.quit()
            
    except KeyboardInterrupt:
        log_with_timestamp("\n⏹️ Process interrupted by user")
        try:
            driver.quit()
        except:
            pass
        
    except Exception as e:
        log_with_timestamp(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
