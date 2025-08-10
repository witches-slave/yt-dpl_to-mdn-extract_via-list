#!/usr/bin/env python3
"""
Sitemap Parser Script
Parses a sitemap XML file and extracts all URLs containing '/updates/' 
to create a list.txt file for the video downloader script.
"""

import xml.etree.ElementTree as ET
import requests
import sys
from urllib.parse import urlparse

def log_with_timestamp(message):
    """Log message with timestamp"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

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

def extract_update_urls(xml_content):
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
        for url_elem in url_elements:
            loc_elem = url_elem.find('ns:loc', namespace)
            if loc_elem is not None:
                url = loc_elem.text.strip()
                if '/updates/' in url and url != 'https://www.shinybound.com/updates':
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

def write_list_file(urls, output_file='list.txt'):
    """Write URLs to list.txt file"""
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
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python sitemap_parser.py <sitemap_url>          # Download from URL")
        print("  python sitemap_parser.py <sitemap_file.xml>     # Parse local file")
        print()
        print("Examples:")
        print("  python sitemap_parser.py https://www.shinybound.com/sitemap.xml")
        print("  python sitemap_parser.py sitemap.xml")
        sys.exit(1)
    
    input_source = sys.argv[1]
    
    # Determine if input is URL or file
    if input_source.startswith('http://') or input_source.startswith('https://'):
        # Download from URL
        xml_content = download_sitemap(input_source)
    else:
        # Read from local file
        xml_content = parse_sitemap_file(input_source)
    
    if not xml_content:
        log_with_timestamp("Failed to get sitemap content")
        sys.exit(1)
    
    # Extract update URLs
    update_urls = extract_update_urls(xml_content)
    
    if not update_urls:
        log_with_timestamp("No update URLs found")
        sys.exit(1)
    
    # Write to list.txt
    if write_list_file(update_urls):
        log_with_timestamp("Sitemap parsing completed successfully!")
        log_with_timestamp(f"Found and saved {len(update_urls)} update URLs")
    else:
        log_with_timestamp("Failed to write list file")
        sys.exit(1)

if __name__ == "__main__":
    main()
