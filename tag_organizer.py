#!/usr/bin/env python3
"""
Tag and Model Organizer Script
Reads tag/model URLs from list_tag.txt, crawls each page to find videos,
and creates organized folders with symlinks to videos in a user-selected folder.
"""

import os
import sys
import re
import glob
import time
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
    print("2. videos subfolder (./videos/)")
    print("3. Custom folder")
    
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            folder = "./"
        elif choice == "2":
            folder = "./videos/"
        elif choice == "3":
            folder = input("Enter the custom folder path: ").strip()
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
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
        time.sleep(2)
        
        video_titles = []
        
        # Try multiple selectors for video titles
        title_selectors = [
            "h3 a",
            ".video-title a",
            ".title a", 
            "a[href*='/updates/']",
            ".thumbnail a",
            ".video-item a",
            ".item-title a"
        ]
        
        for selector in title_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    title = element.get_attribute("title") or element.text.strip()
                    if title and len(title) > 3:  # Skip very short titles
                        video_titles.append(title)
                
                if video_titles:
                    break  # Found titles with this selector
            except:
                continue
        
        # Check for pagination and crawl additional pages
        try:
            # Find last page number for pagination
            pagination_selectors = [
                "div.pagination a",
                ".pagination a", 
                "nav.pagination a",
                ".page-numbers a"
            ]
            
            last_page = 1
            for selector in pagination_selectors:
                try:
                    page_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in page_links:
                        text = link.text.strip()
                        if text.isdigit():
                            last_page = max(last_page, int(text))
                    if last_page > 1:
                        break
                except:
                    continue
            
            # Crawl additional pages if pagination exists
            if last_page > 1:
                log_with_timestamp(f"   Found pagination: {last_page} pages")
                
                for page_num in range(2, last_page + 1):
                    page_url = f"{url}?page={page_num}"
                    
                    try:
                        driver.get(page_url)
                        time.sleep(1)
                        
                        for selector in title_selectors:
                            try:
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                for element in elements:
                                    title = element.get_attribute("title") or element.text.strip()
                                    if title and len(title) > 3:
                                        video_titles.append(title)
                                
                                if elements:
                                    break
                            except:
                                continue
                                
                    except Exception as e:
                        log_with_timestamp(f"   ⚠️ Error crawling page {page_num}: {e}")
        
        except Exception as e:
            log_with_timestamp(f"   ⚠️ Error checking pagination: {e}")
        
        # Remove duplicates while preserving order
        unique_titles = []
        seen = set()
        for title in video_titles:
            if title not in seen:
                unique_titles.append(title)
                seen.add(title)
        
        log_with_timestamp(f"   Found {len(unique_titles)} videos")
        return unique_titles
        
    except Exception as e:
        log_with_timestamp(f"   ❌ Error crawling {url}: {e}")
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

def create_symlink_safe(target_path, link_path):
    """Create symlink with error handling and fallback to hard link"""
    try:
        # Remove existing link if it exists
        if os.path.exists(link_path) or os.path.islink(link_path):
            os.remove(link_path)
        
        # Try creating symlink first
        try:
            os.symlink(target_path, link_path)
            return True, "symlink"
        except OSError:
            # Fallback to hard link for NTFS/Windows compatibility
            try:
                os.link(target_path, link_path)
                return True, "hardlink"
            except OSError:
                log_with_timestamp(f"   ⚠️ Failed to create link for {os.path.basename(target_path)}")
                return False, "failed"
                
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
            
            # Match videos to files and create links
            matched_count = 0
            for video_title in video_titles:
                matching_file = find_matching_video(video_title, video_files)
                
                if matching_file:
                    # Create symlink/hardlink
                    filename = os.path.basename(matching_file)
                    link_path = os.path.join(tag_folder, filename)
                    
                    success, link_type = create_symlink_safe(matching_file, link_path)
                    if success:
                        matched_count += 1
                        total_links_created += 1
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
                filename = os.path.basename(video_path)
                link_path = os.path.join(no_tag_folder, filename)
                
                success, link_type = create_symlink_safe(video_path, link_path)
                if success:
                    no_tag_count += 1
        
        log_with_timestamp(f"   ✅ Added {no_tag_count} untagged videos to 'No Tag' folder")
        
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
