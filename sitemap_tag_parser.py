#!/usr/bin/env python3
"""
Tags & Models Sitemap Parser Script
Parses a sitemap XML file and extracts all URLs containing '/tags/' and '/models/' 
to create a list_tag.txt file.
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
        urls = []
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
    else:
        # Construct sitemap URL from domain
        input_source = f"{domain}/sitemap.xml"
        log_with_timestamp(f"Using default sitemap URL: {input_source}")
        print("Note: You can also provide a custom sitemap URL or file as a command line argument")
        print(f"Usage: python {sys.argv[0]} <sitemap_url_or_file>")
        print()
    
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
    
    # Extract tag and model URLs
    tag_model_urls = extract_tag_model_urls(xml_content, domain)
    
    if not tag_model_urls:
        log_with_timestamp("No tag or model URLs found")
        sys.exit(1)
    
    # Write to list_tag.txt
    if write_list_file(tag_model_urls):
        log_with_timestamp("Tags & models sitemap parsing completed successfully!")
        log_with_timestamp(f"Found and saved {len(tag_model_urls)} tag and model URLs")
    else:
        log_with_timestamp("Failed to write tag list file")
        sys.exit(1)

if __name__ == "__main__":
    main()
