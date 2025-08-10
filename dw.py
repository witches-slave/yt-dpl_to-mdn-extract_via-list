import subprocess
import sys
import os
import time
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def log_with_timestamp(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_login_credentials():
    """Get hardcoded login credentials"""
    email = ""
    password = ""
    log_with_timestamp(f"Using hardcoded credentials for: {email}")
    return email, password

def automated_login(driver, email, password):
    """Perform automated login and return success status"""
    try:
        log_with_timestamp("Starting automated login process...")
        
        # Go to login page
        driver.get("https://shinybound.com/login")
        time.sleep(5)  # Increased wait time
        
        # First, handle the age verification popup if it appears
        log_with_timestamp("Checking for age verification popup...")
        try:
            # Wait for the popup to appear and look for the "I agree" button
            wait = WebDriverWait(driver, 10)
            agree_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".agree, a.agree")))
            log_with_timestamp("Found age verification popup - clicking 'I agree'")
            agree_button.click()
            time.sleep(3)  # Wait for popup to close
        except:
            log_with_timestamp("No age verification popup found, proceeding...")
        
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
                # Try hidden input
                csrf_token_element = driver.find_element(By.CSS_SELECTOR, "input[type='hidden'][name='_token']")
                csrf_token = csrf_token_element.get_attribute("value")
        
        if csrf_token:
            print(f"Found CSRF token: {csrf_token[:20]}...")
        else:
            print("Could not find CSRF token")
            return False
        
        # Wait for form elements to be clickable
        print("Waiting for form elements to be interactable...")
        
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
                print(f"Found email field with selector: {selector}")
                break
            except:
                continue
        
        if not email_field:
            print("Could not find email field")
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
                print(f"Found password field with selector: {selector}")
                break
            except:
                continue
        
        if not password_field:
            print("Could not find password field")
            return False
        
        # Clear and fill fields using JavaScript if normal method fails
        print("Filling in credentials...")
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
                print(f"Found submit button with selector: {selector}")
                break
            except:
                continue
        
        if not submit_button:
            # Try submitting form directly
            try:
                form = driver.find_element(By.CSS_SELECTOR, "form.login_form, .accLoginDetails form")
                form.submit()
                print("Submitted form directly")
            except:
                print("Could not find submit button or form")
                return False
        else:
            # Click submit button using JavaScript to avoid interactability issues
            driver.execute_script("arguments[0].click();", submit_button)
            print("Clicked submit button")
        
        # Wait for redirect/response
        time.sleep(8)  # Increased wait time
        
        # Check if login was successful by looking for certain indicators
        current_url = driver.current_url
        print(f"After login redirect: {current_url}")
        
        # Get cookies after login
        cookies = driver.get_cookies()
        print(f"Got {len(cookies)} cookies after login")
        
        # Check for expected authentication cookies
        auth_cookies = {}
        for cookie in cookies:
            if cookie['name'] in ['XSRF-TOKEN', 'shiny_bound_session', 'forever_cookie']:
                auth_cookies[cookie['name']] = cookie['value']
                print(f"  ✓ {cookie['name']}: {cookie['value'][:20]}...")
        
        # Also check if we're redirected away from login page
        login_success = False
        if current_url != "https://shinybound.com/login" and len(auth_cookies) >= 1:
            login_success = True
        elif len(auth_cookies) >= 2:  # At least 2 of the 3 expected cookies
            login_success = True
        
        if login_success:
            log_with_timestamp("✓ Login appears successful")
            return True
        else:
            log_with_timestamp("✗ Login may have failed - checking page content...")
            # Check for error messages
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error, .invalid-feedback")
                if error_elements:
                    for error in error_elements:
                        if error.text:
                            log_with_timestamp(f"Error message found: {error.text}")
            except:
                pass
            return False
            
    except Exception as e:
        log_with_timestamp(f"Error during automated login: {e}")
        return False

def build_cookie_from_driver(driver):
    """Extract cookies from driver and build cookie string"""
    cookies = driver.get_cookies()
    cookie_parts = []
    
    for cookie in cookies:
        if cookie['name'] in ['XSRF-TOKEN', 'shiny_bound_session', 'forever_cookie']:
            cookie_parts.append(f"{cookie['name']}={cookie['value']}")
    
    return '; '.join(cookie_parts)

def setup_browser_with_login(email, password):
    """Setup browser and perform automated login"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Re-enable headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
    
    # Use webdriver-manager to automatically handle ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Perform automated login
    login_success = automated_login(driver, email, password)
    
    if not login_success:
        print("Login failed. Please check your credentials.")
        driver.quit()
        return None, None
    
    # Build cookie string from logged-in session
    cookie = build_cookie_from_driver(driver)
    print(f"Built cookie string with {len(cookie.split(';'))} components")
    
    return driver, cookie

def setup_browser(cookie):
    """Setup headless Chrome browser with cookies (fallback method)"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
    
    # Use webdriver-manager to automatically handle ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # First visit the domain to set cookies properly
    print("Setting up authentication cookies...")
    driver.get("https://shinybound.com")
    time.sleep(2)
    
    # Clear any existing cookies first
    driver.delete_all_cookies()
    
    # Parse and add cookies with proper domains and paths
    cookies = cookie.split('; ')
    for cookie_item in cookies:
        if '=' in cookie_item:
            name, value = cookie_item.split('=', 1)
            name = name.strip()
            value = value.strip()
            
            # Add cookie with multiple domain variations to ensure it works
            for domain in ['shinybound.com', '.shinybound.com']:
                try:
                    driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': domain,
                        'path': '/',
                        'secure': True,
                        'httpOnly': False
                    })
                except:
                    pass  # Some domains might not work, that's okay
    
    # Refresh the page to ensure cookies are applied
    print("Refreshing page with authentication cookies...")
    driver.refresh()
    time.sleep(3)
    
    # Verify cookies were set
    current_cookies = driver.get_cookies()
    print(f"Set {len(current_cookies)} cookies in browser")
    for c in current_cookies:
        print(f"  - {c['name']}: {c['value'][:20]}...")
    
    return driver

def extract_mpd_url(driver, page_url):
    """Visit page and extract authenticated manifest .mpd URL from network requests"""
    try:
        # Clear previous requests
        del driver.requests
        
        # Visit the page
        log_with_timestamp(f"Loading page: {page_url}")
        driver.get(page_url)
        
        # Extract video title from h1 tag
        video_title = None
        try:
            time.sleep(2)  # Wait for page to load
            h1_element = driver.find_element(By.TAG_NAME, "h1")
            video_title = h1_element.text.strip()
            if video_title:
                # Clean the title for use as filename (remove invalid characters)
                import re
                video_title = re.sub(r'[<>:"/\\|?*]', '', video_title)
                video_title = video_title.replace('\n', ' ').replace('\r', ' ')
                video_title = ' '.join(video_title.split())  # Remove extra whitespace
                log_with_timestamp(f"Found video title: {video_title}")
            else:
                video_title = None
        except Exception as e:
            log_with_timestamp(f"Could not extract video title: {e}")
            video_title = None
        
        # Try to trigger video player by looking for and clicking play button
        try:
            time.sleep(3)
            play_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe")
            if play_buttons:
                print(f"Found {len(play_buttons)} potential play elements, trying to interact...")
                for button in play_buttons[:3]:  # Try first 3 elements
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                    except:
                        pass
        except Exception as e:
            print(f"Could not interact with play button: {e}")
        
        # Wait and monitor for authenticated URLs
        log_with_timestamp("Waiting for video player to load and authenticate...")
        
        authenticated_url = None
        basic_url = None
        
        # Monitor requests for up to 30 seconds
        for i in range(6):  # 6 iterations of 5 seconds each = 30 seconds total
            time.sleep(5)
            log_with_timestamp(f"Checking requests... ({(i+1)*5}/30 seconds)")
            
            # Debug: Show all requests to cloudflare
            print("DEBUG: All cloudflare requests found so far:")
            cloudflare_requests = []
            for request in driver.requests:
                if request.url and 'customer-trb89iur2mnpci10.cloudflarestream.com' in request.url:
                    cloudflare_requests.append(request.url)
                    print(f"  - {request.url}")
            
            if not cloudflare_requests:
                print("  No cloudflare requests found yet")
            
            # Check all requests so far
            for request in driver.requests:
                if request.url and '/manifest/video.mpd' in request.url:
                    # Look for JWT token pattern (JWT tokens contain dots and are base64-like)
                    if '.eyJ' in request.url:  # JWT tokens have this pattern
                        authenticated_url = request.url
                        log_with_timestamp(f"✓ Found AUTHENTICATED manifest URL with JWT token!")
                        print(f"URL: {request.url}")
                        return authenticated_url, video_title
                    elif 'customer-trb89iur2mnpci10.cloudflarestream.com/' in request.url and len(request.url) > 200:
                        # Long cloudflare URLs are likely authenticated
                        authenticated_url = request.url
                        log_with_timestamp(f"✓ Found LONG cloudflare manifest URL (likely authenticated)!")
                        print(f"URL: {request.url}")
                        return authenticated_url, video_title
                    else:
                        basic_url = request.url
                        log_with_timestamp(f"⚠ Found basic manifest URL: {request.url}")
            
            # If we found an authenticated URL, break early
            if authenticated_url:
                break
        
        # Additional wait and check for any cloudflare stream URLs
        log_with_timestamp("Final check for any cloudflare stream URLs...")
        time.sleep(5)
        
        for request in driver.requests:
            print(f"DEBUG: Checking URL: {request.url[:100] if request.url else 'None'}...")
            if request.url and 'customer-trb89iur2mnpci10.cloudflarestream.com/' in request.url:
                if '/manifest/video.mpd' in request.url:
                    print(f"✓ Found cloudflare manifest URL: {request.url}")
                    return request.url, video_title
                elif request.url.count('.') >= 2 and len(request.url) > 150:
                    # This might be an authenticated URL without explicit /manifest/video.mpd
                    potential_manifest = request.url
                    if not potential_manifest.endswith('/manifest/video.mpd'):
                        potential_manifest += '/manifest/video.mpd'
                    print(f"✓ Found potential authenticated URL, trying with manifest path")
                    return potential_manifest, video_title
        
        # Fall back to basic URL if we have one
        if basic_url:
            print("Warning: Only found basic manifest URL, this may only download a preview")
            return basic_url, video_title
        else:
            print(f"No manifest URL found for {page_url}")
            return None, video_title
        
    except Exception as e:
        print(f"Error extracting manifest URL: {e}")
        return None, None

def check_file_exists(video_title):
    """Check if a file with the given title already exists in current directory or ./videos/"""
    if not video_title:
        return False
    
    # Common video file extensions
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Check in current directory
    for ext in video_extensions:
        filename = f"{video_title}{ext}"
        if os.path.exists(filename):
            log_with_timestamp(f"File already exists in current directory: {filename}")
            return True
    
    # Check in ./videos/ directory
    videos_dir = "./videos"
    if os.path.exists(videos_dir):
        for ext in video_extensions:
            filename = f"{video_title}{ext}"
            filepath = os.path.join(videos_dir, filename)
            if os.path.exists(filepath):
                log_with_timestamp(f"File already exists in videos directory: {filepath}")
                return True
    
    return False

def run_yt_dlp(manifest_url, cookie, video_title=None):
    """Download video using yt-dlp with the manifest URL and custom filename"""
    if not manifest_url:
        log_with_timestamp("No manifest URL provided")
        return False
        
    log_with_timestamp(f"Starting download of: {manifest_url}")
    
    cmd = [
        "yt-dlp",
        "--referer", "https://shinybound.com",
        "--concurrent-fragments", "12",
        "--fragment-retries", "1",
        "--abort-on-error"
    ]
    
    # Add custom filename if video title is available
    if video_title:
        # Use the video title as the output filename
        output_template = f"{video_title}.%(ext)s"
        cmd.extend(["-o", output_template])
        log_with_timestamp(f"Using custom filename: {video_title}")
    
    cmd.append(manifest_url)
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Run without capturing output so we can see real-time progress
        result = subprocess.run(cmd)
        
        print("=" * 60)
        log_with_timestamp(f"Download completed with return code: {result.returncode}")
        
        # Check if download was successful
        if result.returncode == 0:
            log_with_timestamp("✓ Download successful!")
            return True
        else:
            log_with_timestamp("✗ Download failed!")
            return False
            
    except Exception as e:
        log_with_timestamp(f"Error running yt-dlp: {e}")
        return False

def is_manifest_url(url):
    """Check if URL is already a manifest URL"""
    return url and ('/manifest/video.mpd' in url or url.endswith('.mpd'))

def main():
    if not os.path.exists("list.txt"):
        print("list.txt not found in the current directory.")
        sys.exit(1)

    with open("list.txt", "r") as txtfile:
        links = [line.strip() for line in txtfile if line.strip()]

    # Check if we have any page URLs that require authentication
    page_urls = [link for link in links if not is_manifest_url(link)]
    manifest_urls = [link for link in links if is_manifest_url(link)]
    
    log_with_timestamp(f"Found {len(page_urls)} page URLs and {len(manifest_urls)} direct manifest URLs")
    
    # Only perform login if we have page URLs
    if page_urls:
        log_with_timestamp("Page URLs detected - automated login required for browser extraction")
        email, password = get_login_credentials()
        driver, cookie = setup_browser_with_login(email, password)
        
        if not driver:
            log_with_timestamp("Login failed, exiting...")
            sys.exit(1)
    else:
        log_with_timestamp("Only direct manifest URLs detected - no authentication needed")
        driver = None
        cookie = None

    i = 0
    try:
        while i < len(links):
            url = links[i]
            log_with_timestamp(f"Processing link {i+1}/{len(links)}: {url}")
            
            if is_manifest_url(url):
                # Direct manifest URL - use it directly
                log_with_timestamp("✓ Direct manifest URL detected, using directly")
                manifest_url = url
                video_title = None  # No title extraction for direct manifest URLs
            else:
                # Page URL - extract manifest URL from the page
                log_with_timestamp("⚠ Page URL detected, extracting manifest URL...")
                if not driver:
                    # This shouldn't happen as we check for page URLs above
                    log_with_timestamp("Error: Need authentication but no driver available")
                    i += 1
                    continue
                manifest_url, video_title = extract_mpd_url(driver, url)
            
            if manifest_url:
                # Check if file already exists before downloading
                if video_title and check_file_exists(video_title):
                    log_with_timestamp(f"Skipping download - file already exists: {video_title}")
                    i += 1
                    continue
                
                # Use yt-dlp to download the video
                success = run_yt_dlp(manifest_url, cookie, video_title)
                if not success:
                    log_with_timestamp(f"Failed at link {i+1}: {url}")
                    if page_urls:  # Only prompt for new credentials if we're using page URLs
                        log_with_timestamp("Download failed. Trying to re-authenticate...")
                        if driver:
                            driver.quit()
                        
                        # Re-authenticate
                        email, password = get_login_credentials()
                        driver, cookie = setup_browser_with_login(email, password)
                        
                        if not driver:
                            log_with_timestamp("Re-authentication failed, skipping remaining page URLs...")
                            i += 1
                        # Don't increment i, retry the same URL with new authentication
                    else:
                        log_with_timestamp("Direct manifest URL failed - this might be due to expired authentication in the URL")
                        i += 1  # Skip to next URL
                else:
                    log_with_timestamp(f"Successfully downloaded video {i+1}")
                    i += 1
            else:
                log_with_timestamp(f"Could not get manifest URL from {url}, skipping...")
                i += 1
                
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
