#!/usr/bin/env python3
"""
Video Sitemap Parser Script
Parses a sitemap XML file and extracts all URLs containing '/updates/' 
to create a list_video.txt file for the video downloader script.
If no sitemap is found, falls back to manual crawling of /updates/ pages.
"""

import xml.etree.ElementTree as ET
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

def get_domain_input():
    """Get domain from user input"""
    print("=" * 60)
    print("SITEMAP VIDEO PARSER")
    print("=" * 60)
    print()
    
    # Get domain
    domain = input("Enter the domain (e.g., shinybound.com or https://shinybound.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        sys.exit(1)
    
    # Add https:// if not present
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    
    # Remove trailing slash if present
    domain = domain.rstrip('/')
    
    print(f"\nUsing domain: {domain}")
    print("="*60 + "\n")
    
    return domain

def get_user_inputs():
    """Get domain input from user"""
    print("=" * 60)
    print("SITEMAP VIDEO PARSER - DOMAIN CONFIGURATION")
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

def crawl_updates_pages_manually(domain):
    """Manually crawl /updates/ pages to find video URLs"""
    log_with_timestamp("🕷️  No sitemap found - starting manual crawling of /updates/ pages")
    
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

def manual_crawl_fallback(domain):
    """Fallback to manual crawling when sitemap is not available"""
    log_with_timestamp("📍 Sitemap method failed, switching to manual crawling mode")
    log_with_timestamp("This will take longer but should find all videos on the site")
    
    # Ask user for confirmation
    print("\nManual crawling will:")
    print("• Visit the /updates/ page(s)")
    print("• Extract all video links from pagination")
    print("• May take several minutes depending on site size")
    print()
    
    confirm = input("Proceed with manual crawling? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        log_with_timestamp("Manual crawling cancelled by user")
        return []
    
    log_separator()
    return crawl_updates_pages_manually(domain)

def download_sitemap(sitemap_url):
    """Download sitemap from URL"""
    try:
        log_with_timestamp(f"Downloading sitemap from: {sitemap_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(sitemap_url, headers=headers, timeout=30)
        response.raise_for_status()
        log_with_timestamp(f"Sitemap downloaded successfully ({len(response.content)} bytes)")
        return response.text
    except requests.RequestException as e:
        log_with_timestamp(f"Error downloading sitemap: {e}")
        return None

def parse_sitemap_file(file_path):
    """Parse sitemap from local file"""
    try:
        log_with_timestamp(f"Reading sitemap from file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        log_with_timestamp("Sitemap file read successfully")
        return content
    except FileNotFoundError:
        log_with_timestamp(f"Error: Sitemap file not found: {file_path}")
        return None
    except Exception as e:
        log_with_timestamp(f"Error reading sitemap file: {e}")
        return None

def extract_update_urls(xml_content, domain):
    """Extract all URLs containing '/updates/' from sitemap XML"""
    try:
        log_with_timestamp("Parsing XML content...")
        
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Define namespace
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Find all URL elements
        urls = []
        url_elements = root.findall('.//ns:url', namespace)
        
        log_with_timestamp(f"Found {len(url_elements)} total URLs in sitemap")
        
        # Extract URLs containing '/updates/'
        update_urls = []
        main_updates_url = f"{domain}/updates"
        
        for url_elem in url_elements:
            loc_elem = url_elem.find('ns:loc', namespace)
            if loc_elem is not None:
                url = loc_elem.text.strip()
                if '/updates/' in url and url != main_updates_url:
                    # Skip the main updates page, only include specific update pages
                    update_urls.append(url)
        
        log_with_timestamp(f"Found {len(update_urls)} URLs containing '/updates/'")
        
        # Sort URLs for consistent output
        update_urls.sort()
        
        return update_urls
        
    except ET.ParseError as e:
        log_with_timestamp(f"Error parsing XML: {e}")
        return []
    except Exception as e:
        log_with_timestamp(f"Error extracting URLs: {e}")
        return []

def write_list_file(urls, output_file='list_video.txt'):
    """Write URLs to list_video.txt file"""
    try:
        log_with_timestamp(f"Writing {len(urls)} URLs to {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')
        
        log_with_timestamp(f"Successfully wrote URLs to {output_file}")
        return True
        
    except Exception as e:
        log_with_timestamp(f"Error writing to file: {e}")
        return False

def main():
    """Main function"""
    log_with_timestamp("Starting sitemap parser...")
    
    # Get user input for domain
    domain = get_domain_input()
    
    # Check if user provided a command line argument for custom sitemap location
    if len(sys.argv) >= 2:
        input_source = sys.argv[1]
        log_with_timestamp(f"Using provided sitemap source: {input_source}")
        force_sitemap = True
    else:
        # Construct sitemap URL from domain
        input_source = f"{domain}/sitemap.xml"
        log_with_timestamp(f"Trying default sitemap URL: {input_source}")
        force_sitemap = False
        print("Note: You can also provide a custom sitemap URL or file as a command line argument")
        print(f"Usage: python {sys.argv[0]} <sitemap_url_or_file>")
        print()
    
    update_urls = []
    
    # Try sitemap method first
    if input_source.startswith('http://') or input_source.startswith('https://'):
        # Download from URL
        xml_content = download_sitemap(input_source)
        if xml_content:
            update_urls = extract_update_urls(xml_content, domain)
    else:
        # Read from local file
        xml_content = parse_sitemap_file(input_source)
        if xml_content:
            update_urls = extract_update_urls(xml_content, domain)
    
    # If sitemap method failed and user didn't force a specific sitemap, try manual crawling
    if not update_urls and not force_sitemap:
        log_with_timestamp("⚠️  Sitemap method unsuccessful")
        update_urls = manual_crawl_fallback(domain)
    elif not update_urls and force_sitemap:
        log_with_timestamp("❌ Failed to extract URLs from specified sitemap")
        sys.exit(1)
    
    if not update_urls:
        log_with_timestamp("❌ No video URLs found through any method")
        log_with_timestamp("💡 Possible solutions:")
        log_with_timestamp("   • Check if the domain is correct")
        log_with_timestamp("   • Try a different sitemap URL")
        log_with_timestamp("   • Check if the site has /updates/ pages")
        sys.exit(1)
    
    # Write to list_video.txt
    if write_list_file(update_urls):
        log_with_timestamp("✅ Video URL extraction completed successfully!")
        log_with_timestamp(f"Found and saved {len(update_urls)} video URLs")
        log_with_timestamp(f"Next step: Run 'python3 download.py' to download the videos")
    else:
        log_with_timestamp("❌ Failed to write video list file")
        sys.exit(1)

if __name__ == "__main__":
    main()
