#!/usr/bin/env python3
"""
Video URL Parser Script
Crawls /updates/ pages and extracts all video URLs to create a list_video.txt file 
for the video downloader script. This ensures we get only live, current video links
and avoids dead links that might be in sitemaps.
"""

import requests
import sys
import re
import time
from urllib.parse import urlparse, urljoin
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def log_with_timestamp(message):
    """Log message with timestamp"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def log_separator():
    """Print a clean separator line without timestamp"""
    print()

def get_user_inputs():
    """Get domain input from user"""
    print("=" * 60)
    print("VIDEO URL PARSER - CRAWLING /UPDATES/ PAGES")
    print("=" * 60)
    
    # Get domain
    domain = input("Enter the domain (e.g., shinybound.com or https://shinybound.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        sys.exit(1)
    
    # Normalize domain format
    if not domain.startswith('http://') and not domain.startswith('https://'):
        domain = 'https://' + domain
    
    # Remove trailing slash if present
    domain = domain.rstrip('/')
    
    print(f"\nUsing domain: {domain}")
    print("="*60 + "\n")
    
    return domain

def setup_headless_browser():
    """Setup headless Chrome browser for manual crawling"""
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

def crawl_updates_pages(domain):
    """Crawl /updates/ pages to find all current video URLs and extract titles"""
    log_with_timestamp("🕷️  Starting crawling of /updates/ pages with title extraction")
    
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("Failed to setup browser for crawling")
        return []
    
    all_video_data = []  # Changed to store both URL and title
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
                
                # Extract video URLs and titles from this page
                video_data = extract_video_data_from_page(driver, domain)
                all_video_data.extend(video_data)
                
                log_with_timestamp(f"  Found {len(video_data)} videos on this page")
                
            except Exception as e:
                log_with_timestamp(f"  Error crawling page: {e}")
                continue
        
        # Remove duplicate URLs while preserving order
        unique_data = []
        seen_urls = set()
        for data in all_video_data:
            if data['url'] not in seen_urls:
                unique_data.append(data)
                seen_urls.add(data['url'])
        
        log_with_timestamp(f"🎯 Crawling complete: found {len(unique_data)} unique video URLs")
        return unique_data
        
    finally:
        driver.quit()

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
                log_with_timestamp(f"📋 Pattern: {page_url_pattern}")
                
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

def extract_video_data_from_page(driver, domain):
    """Extract individual video page URLs and titles from an updates listing page"""
    video_data = []
    seen_urls = set()  # Track URLs to avoid duplicates within the same page
    
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
                                
                                # Try to extract title from the element
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
                                        title = title.strip()
                                        # Remove newlines and extra spaces
                                        title = re.sub(r'\s+', ' ', title)
                                        # Remove invalid filename characters
                                        title = re.sub(r'[<>:"/\\|?*]', '', title)
                                        
                                except Exception:
                                    title = None
                                
                                video_data.append({
                                    'url': href,
                                    'title': title,
                                    'url_title': None  # Will be filled if needed for duplicates
                                })
                    except Exception as e:
                        continue
                
                log_with_timestamp(f"    → Processed {elements_processed} unique videos from this selector")
                break  # Use first working selector
        except Exception as e:
            continue
    
    log_with_timestamp(f"  Total unique videos extracted from page: {len(video_data)}")
    return video_data

def create_url_title(url):
    """Create a title from URL when duplicates are detected"""
    try:
        # Extract the part after /updates/
        if "/updates/" in url:
            url_part = url.split("/updates/")[1]
            # Remove any trailing slashes and parameters
            url_part = url_part.split('?')[0].rstrip('/')
            # Convert hyphens to spaces and make uppercase
            url_title = url_part.replace('-', ' ').upper()
            return url_title
    except Exception:
        pass
    return None

def detect_and_handle_duplicates(video_data):
    """Detect duplicate titles and assign URL-based titles where needed"""
    log_with_timestamp("🔍 Checking for duplicate titles...")
    
    # Count titles
    title_counts = {}
    for data in video_data:
        title = data['title']
        if title:  # Only count non-empty titles
            title_lower = title.lower()
            if title_lower not in title_counts:
                title_counts[title_lower] = []
            title_counts[title_lower].append(data)
    
    # Find duplicates
    duplicates_found = 0
    for title_lower, entries in title_counts.items():
        if len(entries) > 1:
            duplicates_found += len(entries)
            log_with_timestamp(f"  🔄 Duplicate title found: '{entries[0]['title']}' ({len(entries)} videos)")
            
            # Assign URL-based titles to all duplicates
            for entry in entries:
                url_title = create_url_title(entry['url'])
                if url_title:
                    entry['url_title'] = url_title
                    log_with_timestamp(f"    • {entry['url']} -> '{url_title}'")
                else:
                    log_with_timestamp(f"    • {entry['url']} -> Could not create URL title")
    
    if duplicates_found > 0:
        log_with_timestamp(f"✅ Processed {duplicates_found} duplicate titles")
    else:
        log_with_timestamp("✅ No duplicate titles found")
    
    return video_data

def write_list_file(video_data, output_file='list_video.txt'):
    """Write video data to list_video.txt file with format: URL|TITLE"""
    try:
        log_with_timestamp(f"Writing {len(video_data)} video entries to {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for data in video_data:
                url = data['url']
                # Use URL title if available (for duplicates), otherwise use normal title
                title = data.get('url_title') or data.get('title') or ''
                f.write(f"{url}|{title}\n")
        
        log_with_timestamp(f"Successfully wrote video data to {output_file}")
        return True
        
    except Exception as e:
        log_with_timestamp(f"Error writing to file: {e}")
        return False

def main():
    """Main function"""
    log_with_timestamp("Starting video URL parser with title extraction...")
    
    # Get user input for domain
    domain = get_user_inputs()
    
    # Crawl /updates/ pages to find all video URLs and titles
    video_data = crawl_updates_pages(domain)
    
    if not video_data:
        log_with_timestamp("❌ No video URLs found")
        log_with_timestamp("💡 Possible solutions:")
        log_with_timestamp("   • Check if the domain is correct")
        log_with_timestamp("   • Check if the site has /updates/ pages")
        log_with_timestamp("   • Check if there are any videos on the site")
        sys.exit(1)
    
    # Detect and handle duplicate titles
    video_data = detect_and_handle_duplicates(video_data)
    
    # Write to list_video.txt
    if write_list_file(video_data):
        log_with_timestamp("✅ Video URL and title extraction completed successfully!")
        log_with_timestamp(f"Found and saved {len(video_data)} video entries")
        log_with_timestamp(f"Next step: Run 'python3 download.py' to download the videos")
    else:
        log_with_timestamp("❌ Failed to write video list file")
        sys.exit(1)

if __name__ == "__main__":
    main()
