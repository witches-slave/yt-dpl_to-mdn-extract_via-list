#!/usr/bin/env python3
"""
Tags & Models Sitemap Parser Script
Parses a sitemap XML file and extracts all URLs containing '/tags/' and '/models/' 
to create a list_tag.txt file.
If no sitemap is found, falls back to manual crawling of /tags/ and /models/ pages.
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

def crawl_tags_and_models_manually(domain):
    """Manually crawl /tags/ and /models/ pages to find tag/model URLs"""
    log_with_timestamp("🕷️  No sitemap found - starting manual crawling of /tags/ and /models/ pages")
    
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("Failed to setup browser for manual crawling")
        return []
    
    all_tag_model_urls = []
    
    try:
        # Crawl tags pages
        tags_urls = crawl_category_pages(driver, domain, "tags")
        all_tag_model_urls.extend(tags_urls)
        
        # Crawl models pages  
        models_urls = crawl_category_pages(driver, domain, "models")
        all_tag_model_urls.extend(models_urls)
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in all_tag_model_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        log_with_timestamp(f"🎯 Manual crawling complete: found {len(unique_urls)} unique tag/model URLs")
        return unique_urls
        
    finally:
        driver.quit()

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

def get_tag_model_video_pagination(driver, base_url):
    """Get pagination URLs for videos within a specific tag or model page"""
    pagination_urls = [base_url]  # Always include the current page
    
    try:
        # Find pagination for videos within this tag/model
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
                                        if "page=" in href:
                                            page_url_pattern = href.replace(f"page={text_page_num}", "page={}")
                                        elif "/page/" in href:
                                            page_url_pattern = href.replace(f"/page/{text_page_num}", "/page/{}")
                            except:
                                pass
                        
                        if page_num and page_num > max_page:
                            max_page = page_num
                            
                except Exception as e:
                    continue
            
            # Generate all page URLs if we found a pattern
            if page_url_pattern and max_page > 1:
                for page_num in range(2, max_page + 1):  # Start from 2 since we already have page 1
                    page_url = page_url_pattern.format(page_num)
                    pagination_urls.append(page_url)
        
        return pagination_urls
        
    except Exception as e:
        return pagination_urls

def extract_video_urls_from_tag_model_page(driver, domain):
    """Extract video URLs from a tag or model page using videoBlock structure"""
    video_urls = []
    
    # Look for videoBlock divs which contain the videos
    selectors_to_try = [
        "div.videoBlock h3 a[href*='/updates/']",
        ".videoBlock a[href*='/updates/']",
        "div.videoBlock .videoPic a",
        "a[href*='/updates/']:not([href$='/updates']):not([href$='/updates/'])"
    ]
    
    for selector in selectors_to_try:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                log_with_timestamp(f"    Found {len(elements)} videos using selector: {selector}")
                
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

def get_pagination_urls(driver, base_url, category):
    """Get all pagination URLs for tags or models pages - generates ALL pages from 1 to last"""
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
                    
                    if href and href != "#" and f"/{category}" in href:
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
                log_with_timestamp(f"🔢 Found {category} pagination: pages 1 to {max_page}")
                log_with_timestamp(f"📋 Pattern: {page_url_pattern}")
                
                # Generate URLs for all pages from 1 to max_page
                for page_num in range(1, max_page + 1):
                    if page_num == 1:
                        # Page 1 is usually the base URL
                        continue  # Already added above
                    else:
                        page_url = page_url_pattern.format(page_num)
                        pagination_urls.append(page_url)
                
                log_with_timestamp(f"✅ Generated {len(pagination_urls)} {category} URLs (pages 1-{max_page})")
            
            # Fallback: if we couldn't determine pattern, use visible links only
            elif len(pagination_links) > 0:
                log_with_timestamp(f"⚠️  Could not determine {category} pagination pattern, using visible links only")
                for link in pagination_links:
                    try:
                        href = link.get_attribute("href")
                        if href and href != "#" and href not in pagination_urls:
                            if (f"/{category}" in href and 
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
                log_with_timestamp(f"📄 Using {len(pagination_urls)} visible {category} links")
        
        else:
            log_with_timestamp(f"ℹ️  No {category} pagination found, using single page")
        
        return pagination_urls
        
    except Exception as e:
        log_with_timestamp(f"⚠️  Error finding {category} pagination: {e}")
        return pagination_urls



def extract_tag_model_urls_from_page(driver, domain, category):
    """Extract individual tag/model page URLs from a listing page based on HTML structure"""
    urls = []
    
    if category == "tags":
        # For tags pages, look for tagsContainer divs
        selectors_to_try = [
            "div.tagsContainer .tagName a",
            ".tagsContainer a",
            "div.tagName a",
            ".tag-link",
            f"a[href*='/{category}/']:not([href$='/{category}']):not([href$='/{category}/'])"
        ]
    elif category == "models":
        # For models pages, look for modelBlock divs
        selectors_to_try = [
            "div.modelBlock h3 a",
            ".modelBlock a",
            "div.modelName a", 
            ".model-link",
            f"a[href*='/{category}/']:not([href$='/{category}']):not([href$='/{category}/'])"
        ]
    else:
        # Generic fallback
        selectors_to_try = [
            f"a[href*='/{category}/']:not([href$='/{category}']):not([href$='/{category}/'])",
            f".{category}-link",
            f".{category[:-1]}-link",  # singular form (tag-link, model-link)
        ]
    
    for selector in selectors_to_try:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                log_with_timestamp(f"  Using selector: {selector} (found {len(elements)} elements)")
                
                for element in elements:
                    try:
                        href = element.get_attribute("href")
                        if href and f"/{category}/" in href:
                            # Make sure it's a full URL
                            if href.startswith("/"):
                                href = domain + href
                            elif not href.startswith("http"):
                                href = urljoin(domain, href)
                            
                            # Avoid duplicate main category page
                            if not href.endswith((f"/{category}", f"/{category}/")):
                                urls.append(href)
                    except Exception as e:
                        continue
                break  # Use first working selector
        except Exception as e:
            continue
    
    # Remove duplicates
    unique_urls = list(set(urls))
    return unique_urls

def manual_crawl_fallback(domain):
    """Fallback to manual crawling when sitemap is not available"""
    log_with_timestamp("📍 Sitemap method failed, switching to manual crawling mode")
    log_with_timestamp("This will crawl both /tags/ and /models/ pages")
    
    # Ask user for confirmation
    print("\nManual crawling will:")
    print("• Visit the /tags/ and /models/ pages")
    print("• Extract all tag and model links from pagination")
    print("• May take several minutes depending on site size")
    print()
    
    confirm = input("Proceed with manual crawling? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        log_with_timestamp("Manual crawling cancelled by user")
        return []
    
    log_separator()
    return crawl_tags_and_models_manually(domain)

def get_domain_input():
    """Get domain from user input"""
    print("=" * 60)
    print("SITEMAP TAG/MODEL PARSER")
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

def extract_tag_model_urls(xml_content, domain):
    """Extract all URLs containing '/tags/' and '/models/' from sitemap XML"""
    try:
        log_with_timestamp("Parsing XML content...")
        
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Define namespace
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Find all URL elements
        url_elements = root.findall('.//ns:url', namespace)
        
        log_with_timestamp(f"Found {len(url_elements)} total URLs in sitemap")
        
        # Extract URLs containing '/tags/' or '/models/'
        tag_model_urls = []
        tags_count = 0
        models_count = 0
        
        # Create dynamic main page URLs based on domain
        main_tags_url = f"{domain}/tags"
        main_models_url = f"{domain}/models"
        
        for url_elem in url_elements:
            loc_elem = url_elem.find('ns:loc', namespace)
            if loc_elem is not None:
                url = loc_elem.text.strip()
                
                # Check for tags URLs (but skip main tags page)
                if '/tags/' in url and url != main_tags_url:
                    tag_model_urls.append(url)
                    tags_count += 1
                
                # Check for models URLs (but skip main models page)
                elif '/models/' in url and url != main_models_url:
                    tag_model_urls.append(url)
                    models_count += 1
        
        log_with_timestamp(f"Found {tags_count} tag URLs and {models_count} model URLs")
        log_with_timestamp(f"Total: {len(tag_model_urls)} URLs containing '/tags/' or '/models/'")
        
        # Sort URLs for consistent output
        tag_model_urls.sort()
        
        return tag_model_urls
        
    except ET.ParseError as e:
        log_with_timestamp(f"Error parsing XML: {e}")
        return []
    except Exception as e:
        log_with_timestamp(f"Error extracting URLs: {e}")
        return []

def crawl_sitemap_tag_model_pages_for_videos(tag_model_urls, domain):
    """Crawl tag/model pages from sitemap to extract their associated videos"""
    log_with_timestamp(f"Setting up browser to crawl {len(tag_model_urls)} tag/model pages...")
    
    driver = setup_headless_browser()
    if not driver:
        log_with_timestamp("Failed to setup browser for sitemap tag/model crawling")
        return tag_model_urls  # Return original URLs if browser fails
    
    all_urls = []
    
    try:
        for i, tag_model_url in enumerate(tag_model_urls, 1):
            log_with_timestamp(f"Crawling tag/model {i}/{len(tag_model_urls)}: {tag_model_url}")
            
            # Add the tag/model URL itself
            all_urls.append(tag_model_url)
            
            try:
                driver.get(tag_model_url)
                time.sleep(2)
                
                # Get pagination for this specific tag/model
                tag_model_pagination = get_tag_model_video_pagination(driver, tag_model_url)
                
                # Extract videos from all pages of this tag/model
                video_urls = []
                for page_url in tag_model_pagination:
                    if page_url != tag_model_url:  # Don't reload the same page
                        driver.get(page_url)
                        time.sleep(2)
                    
                    videos = extract_video_urls_from_tag_model_page(driver, domain)
                    video_urls.extend(videos)
                
                # Add all video URLs for this tag/model
                all_urls.extend(video_urls)
                
                log_with_timestamp(f"  Found {len(video_urls)} videos for this tag/model")
                
            except Exception as e:
                log_with_timestamp(f"  Error crawling tag/model page: {e}")
                continue
        
        log_with_timestamp(f"✅ Sitemap tag/model crawling complete: enhanced with video mappings")
        return all_urls
        
    finally:
        driver.quit()

def write_list_file(urls, output_file='list_tag.txt'):
    """Write URLs to list_tag.txt file"""
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
    log_with_timestamp("Starting tags & models sitemap parser...")
    
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
    
    tag_model_urls = []
    
    # Try sitemap method first
    if input_source.startswith('http://') or input_source.startswith('https://'):
        # Download from URL
        xml_content = download_sitemap(input_source)
        if xml_content:
            tag_model_urls = extract_tag_model_urls(xml_content, domain)
    else:
        # Read from local file
        xml_content = parse_sitemap_file(input_source)
        if xml_content:
            tag_model_urls = extract_tag_model_urls(xml_content, domain)
    
    # If sitemap method failed and user didn't force a specific sitemap, try manual crawling
    if not tag_model_urls and not force_sitemap:
        log_with_timestamp("⚠️  Sitemap method unsuccessful")
        tag_model_urls = manual_crawl_fallback(domain)
    elif not tag_model_urls and force_sitemap:
        log_with_timestamp("❌ Failed to extract URLs from specified sitemap")
        sys.exit(1)
    
    if not tag_model_urls:
        log_with_timestamp("❌ No tag or model URLs found through any method")
        log_with_timestamp("💡 Possible solutions:")
        log_with_timestamp("   • Check if the domain is correct")
        log_with_timestamp("   • Try a different sitemap URL")
        log_with_timestamp("   • Check if the site has /tags/ and /models/ pages")
        sys.exit(1)
    
    # Write to list_tag.txt
    if write_list_file(tag_model_urls):
        log_with_timestamp("✅ Tags & models extraction completed successfully!")
        log_with_timestamp(f"Found and saved {len(tag_model_urls)} tag and model URLs")
        log_with_timestamp(f"Next step: Run 'python3 tag_organizer.py' to organize videos by tags")
    else:
        log_with_timestamp("❌ Failed to write tag list file")
        sys.exit(1)

if __name__ == "__main__":
    main()
