import subprocess
import sys
import os
import time
import shutil
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

def log_separator():
    """Print a clean separator line without timestamp"""
    print()

def log_section_break():
    """Print a section break with equals signs"""
    print("=" * 80)

def check_storage_space(min_gb=10):
    """Check if there's enough free storage space (in GB)"""
    try:
        # Get disk usage statistics for current directory
        total, used, free = shutil.disk_usage(".")
        
        # Convert bytes to GB
        free_gb = free / (1024**3)
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        
        log_with_timestamp(f"Storage info - Total: {total_gb:.1f}GB, Used: {used_gb:.1f}GB, Free: {free_gb:.1f}GB")
        
        if free_gb < min_gb:
            log_with_timestamp(f"⚠️  Warning: Only {free_gb:.1f}GB free space remaining (minimum required: {min_gb}GB)")
            log_with_timestamp("❌ Skipping download due to insufficient storage space")
            return False
        else:
            log_with_timestamp(f"✓ Sufficient storage space available: {free_gb:.1f}GB free")
            return True
            
    except Exception as e:
        log_with_timestamp(f"Error checking storage space: {e}")
        # Continue with download if we can't check storage
        return True

def get_user_inputs():
    """Get domain, email, and password from user input"""
    print("\n" + "="*60)
    print("AUTHENTICATION SETUP")
    print("="*60)
    
    # Get domain
    domain = input("Enter the domain (e.g., https://shinybound.com): ").strip()
    if not domain:
        print("Error: Domain cannot be empty")
        sys.exit(1)
    
    # Ensure domain has proper format
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    
    # Remove trailing slash if present
    domain = domain.rstrip('/')
    
    # Get email
    email = input("Enter your email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        sys.exit(1)
    
    # Get password
    import getpass
    password = getpass.getpass("Enter your password: ").strip()
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)
    
    print(f"\nUsing domain: {domain}")
    print(f"Using email: {email}")
    print("Password: [HIDDEN]")
    print("="*60 + "\n")
    
    return domain, email, password

def get_output_folder():
    """Get output folder from user input"""
    print("=" * 60)
    print("OUTPUT FOLDER SELECTION")
    print("=" * 60)
    print()
    
    # Show current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    print()
    
    # Get folder name
    folder_name = input("Enter folder name for downloads (will be created in current directory): ").strip()
    if not folder_name:
        print("Error: Folder name cannot be empty")
        sys.exit(1)
    
    # Create the folder path
    output_folder = os.path.join(current_dir, folder_name)
    
    # Create folder if it doesn't exist
    try:
        os.makedirs(output_folder, exist_ok=True)
        print(f"\nOutput folder: {output_folder}")
        if os.path.exists(output_folder):
            print("✓ Folder ready for downloads")
        else:
            print("✓ Folder will be created")
    except Exception as e:
        print(f"Error creating folder: {e}")
        sys.exit(1)
    
    print("="*60 + "\n")
    return output_folder

def automated_login(driver, email, password, domain):
    """Perform automated login and return success status"""
    try:
        log_with_timestamp("Starting automated login process...")
        
        # Go to login page using the provided domain
        login_url = f"{domain}/login"
        driver.get(login_url)
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
            log_with_timestamp(f"Found CSRF token: {csrf_token[:20]}...")
        else:
            log_with_timestamp("Could not find CSRF token")
            return False
        
        # Wait for form elements to be clickable
        log_with_timestamp("Waiting for form elements to be interactable...")
        
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
                log_with_timestamp(f"Found email field with selector: {selector}")
                break
            except:
                continue
        
        if not email_field:
            log_with_timestamp("Could not find email field")
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
                log_with_timestamp(f"Found password field with selector: {selector}")
                break
            except:
                continue
        
        if not password_field:
            log_with_timestamp("Could not find password field")
            return False
        
        # Clear and fill fields using JavaScript if normal method fails
        log_with_timestamp("Filling in credentials...")
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
                log_with_timestamp(f"Found submit button with selector: {selector}")
                break
            except:
                continue
        
        if not submit_button:
            # Try submitting form directly
            try:
                form = driver.find_element(By.CSS_SELECTOR, "form.login_form, .accLoginDetails form")
                form.submit()
                log_with_timestamp("Submitted form directly")
            except:
                log_with_timestamp("Could not find submit button or form")
                return False
        else:
            # Click submit button using JavaScript to avoid interactability issues
            driver.execute_script("arguments[0].click();", submit_button)
            log_with_timestamp("Clicked submit button")
        
        # Wait for redirect/response
        time.sleep(8)  # Increased wait time
        
        # Check if login was successful by looking for certain indicators
        current_url = driver.current_url
        log_with_timestamp(f"After login redirect: {current_url}")
        
        # Get cookies after login
        cookies = driver.get_cookies()
        log_with_timestamp(f"Got {len(cookies)} cookies after login")
        
        # Check for expected authentication cookies (these may vary by site)
        auth_cookies = {}
        for cookie in cookies:
            # Look for common session/auth cookie patterns
            if any(keyword in cookie['name'].lower() for keyword in ['session', 'auth', 'token', 'login', 'xsrf', 'csrf']):
                auth_cookies[cookie['name']] = cookie['value']
                log_with_timestamp(f"  ✓ {cookie['name']}: {cookie['value'][:20]}...")
        
        # Also check if we're redirected away from login page
        login_success = False
        login_url = f"{domain}/login"
        if current_url != login_url and len(auth_cookies) >= 1:
            login_success = True
        elif len(auth_cookies) >= 1:  # At least 1 authentication-related cookie
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
        # Include all cookies, not just specific ones, for maximum compatibility
        cookie_parts.append(f"{cookie['name']}={cookie['value']}")
    
    return '; '.join(cookie_parts)

def setup_browser_with_login(email, password, domain):
    """Setup browser and perform automated login"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Re-enable headless mode
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
    
    # Use webdriver-manager to automatically handle ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Perform automated login
    login_success = automated_login(driver, email, password, domain)
    
    if not login_success:
        log_with_timestamp("Login failed. Please check your credentials.")
        driver.quit()
        return None, None
    
    # Build cookie string from logged-in session
    cookie = build_cookie_from_driver(driver)
    log_with_timestamp(f"Built cookie string with {len(cookie.split(';'))} components")
    
    return driver, cookie

def setup_browser(cookie, domain):
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
    log_with_timestamp("Setting up authentication cookies...")
    driver.get(domain)
    time.sleep(2)
    
    # Clear any existing cookies first
    driver.delete_all_cookies()
    
    # Parse and add cookies with proper domains and paths
    cookies = cookie.split('; ')
    # Extract domain name from full URL
    from urllib.parse import urlparse
    parsed_domain = urlparse(domain).netloc
    
    for cookie_item in cookies:
        if '=' in cookie_item:
            name, value = cookie_item.split('=', 1)
            name = name.strip()
            value = value.strip()
            
            # Add cookie with multiple domain variations to ensure it works
            for cookie_domain in [parsed_domain, f'.{parsed_domain}']:
                try:
                    driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': cookie_domain,
                        'path': '/',
                        'secure': True,
                        'httpOnly': False
                    })
                except:
                    pass  # Some domains might not work, that's okay
    
    # Refresh the page to ensure cookies are applied
    log_with_timestamp("Refreshing page with authentication cookies...")
    driver.refresh()
    time.sleep(3)
    
    # Verify cookies were set
    current_cookies = driver.get_cookies()
    log_with_timestamp(f"Set {len(current_cookies)} cookies in browser")
    for c in current_cookies:
        log_with_timestamp(f"  - {c['name']}: {c['value'][:20]}...")
    
    return driver

def extract_mpd_url(driver, page_url, domain):
    """Visit page and extract authenticated manifest .mpd URL from network requests"""
    try:
        # Clear previous requests
        del driver.requests
        
        # Visit the page
        log_with_timestamp(f"Loading page: {page_url}")
        driver.get(page_url)
        
        # Wait for page to load using WebDriverWait instead of fixed sleep
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass  # Continue even if timeout
        
        # Check if we were redirected to the main updates page (dead link)
        current_url = driver.current_url
        updates_main_page = f"{domain}/updates"
        
        if current_url == updates_main_page or current_url == f"{updates_main_page}/":
            log_with_timestamp(f"⚠ Page redirected to main updates page - this is a dead link")
            log_with_timestamp(f"Original URL: {page_url}")
            log_with_timestamp(f"Redirected to: {current_url}")
            log_with_timestamp("Skipping this video and moving to next...")
            return None, None
        
        # Extract video title from h1 tag
        video_title = None
        try:
            # Use WebDriverWait to wait for h1 element instead of fixed sleep
            h1_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
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
            # If we can't find h1 tag, it's likely a redirect or broken page
            log_with_timestamp(f"Could not extract video title (page might be redirected or broken): {e}")
            log_with_timestamp("Checking if this is a redirect to main updates page...")
            
            # Double-check for redirect
            current_url = driver.current_url
            if current_url == updates_main_page or current_url == f"{updates_main_page}/":
                log_with_timestamp(f"⚠ Confirmed: Page redirected to main updates page")
                log_with_timestamp("Skipping this video and moving to next...")
                return None, None
            
            video_title = None
        
        # Try to trigger video player by looking for and clicking play button
        try:
            # Wait for any play buttons to appear (reduced timeout)
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe"))
                )
            except:
                pass  # Continue even if no play buttons found
            
            play_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe")
            if play_buttons:
                for button in play_buttons[:2]:  # Try only first 2 elements for speed
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.3)  # Further reduced from 0.5 second
                    except:
                        pass
        except Exception as e:
            pass
        
        # Wait and monitor for authenticated URLs
        log_with_timestamp("Waiting for video player to load and authenticate...")
        
        authenticated_url = None
        basic_url = None
        
        # Monitor requests for up to 2 seconds for speed
        for i in range(1):  # 1 iteration of 2 seconds each = 2 seconds total
            time.sleep(2)  # Further reduced from 3 seconds
            log_with_timestamp(f"Checking requests... ({(i+1)*2}/2 seconds)")
            
            # Debug: Show all requests to common video CDN patterns
            cdn_requests = []
            for request in driver.requests:
                if request.url and any(pattern in request.url.lower() for pattern in ['stream', 'video', 'manifest', '.mpd']):
                    cdn_requests.append(request.url)
            
            # Check all requests so far
            for request in driver.requests:
                if request.url and '/manifest/video.mpd' in request.url:
                    # Look for JWT token pattern (JWT tokens contain dots and are base64-like)
                    if '.eyJ' in request.url:  # JWT tokens have this pattern
                        authenticated_url = request.url
                        log_with_timestamp(f"✓ Found AUTHENTICATED manifest URL with JWT token!")
                        return authenticated_url, video_title
                    elif len(request.url) > 200:
                        # Long URLs are likely authenticated
                        authenticated_url = request.url
                        log_with_timestamp(f"✓ Found LONG manifest URL (likely authenticated)!")
                        return authenticated_url, video_title
                    else:
                        basic_url = request.url
            
            # If we found an authenticated URL, break early
            if authenticated_url:
                break
        
        # Additional wait and check for any video stream URLs
        log_with_timestamp("Final check for any video stream URLs...")
        time.sleep(1)  # Further reduced from 2 seconds
        
        for request in driver.requests:
            if request.url and any(pattern in request.url.lower() for pattern in ['stream', 'cloudflare']):
                if '/manifest/video.mpd' in request.url:
                    log_with_timestamp(f"✓ Found video stream manifest URL")
                    return request.url, video_title
                elif request.url.count('.') >= 2 and len(request.url) > 150:
                    # This might be an authenticated URL without explicit /manifest/video.mpd
                    potential_manifest = request.url
                    if not potential_manifest.endswith('/manifest/video.mpd'):
                        potential_manifest += '/manifest/video.mpd'
                    log_with_timestamp(f"✓ Found potential authenticated URL, trying with manifest path")
                    return potential_manifest, video_title
        
        # Fall back to basic URL if we have one
        if basic_url:
            log_with_timestamp("Warning: Only found basic manifest URL, this may only download a preview")
            return basic_url, video_title
        else:
            log_with_timestamp(f"No manifest URL found for {page_url}")
            return None, video_title
        
    except Exception as e:
        log_with_timestamp(f"Error extracting manifest URL: {e}")
        return None, None

def extract_title_and_manifest_url(driver, page_url, domain):
    """Extract both video title and manifest URL in a single page load - OPTIMIZED VERSION"""
    try:
        # Clear previous requests for fresh monitoring
        del driver.requests
        
        # Load the page once
        log_with_timestamp(f"🔄 Loading page for title and manifest extraction: {page_url}")
        driver.get(page_url)
        
        # Wait for page to load using WebDriverWait
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass  # Continue even if timeout
        
        # Check if we were redirected to the main updates page (dead link)
        current_url = driver.current_url
        updates_main_page = f"{domain}/updates"
        
        if current_url == updates_main_page or current_url == f"{updates_main_page}/":
            log_with_timestamp(f"⚠ Page redirected to main updates page - this is a dead link")
            return None, None, True  # No manifest, no title, is redirect
        
        # Extract video title from h1 tag
        video_title = None
        try:
            h1_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            video_title = h1_element.text.strip()
            if video_title:
                # Clean the title for use as filename
                import re
                video_title = re.sub(r'[<>:"/\\|?*]', '', video_title)
                video_title = video_title.replace('\n', ' ').replace('\r', ' ')
                video_title = ' '.join(video_title.split())  # Remove extra whitespace
                log_with_timestamp(f"📝 Extracted video title: {video_title}")
            else:
                log_with_timestamp("❌ Could not extract video title - h1 element is empty")
                return None, None, False
        except Exception as e:
            log_with_timestamp(f"❌ Could not extract video title: {e}")
            return None, None, False
        
        # Now extract manifest URL from the same page load
        log_with_timestamp("🎥 Triggering video player for manifest URL...")
        
        # Try to trigger video player by looking for and clicking play button
        try:
            # Wait for any play buttons to appear (reduced timeout)
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe"))
                )
            except:
                pass  # Continue even if no play buttons found
            
            play_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe")
            if play_buttons:
                for button in play_buttons[:2]:  # Try only first 2 elements for speed
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.3)  # Brief pause
                    except:
                        pass
        except Exception as e:
            pass
        
        # Wait and monitor for authenticated URLs
        log_with_timestamp("🔍 Monitoring for authenticated manifest URL...")
        
        authenticated_url = None
        basic_url = None
        
        # Monitor requests for up to 2 seconds for speed
        start_time = time.time()
        while time.time() - start_time < 2:
            try:
                for request in driver.requests:
                    if request.response and hasattr(request, 'url'):
                        url = request.url
                        if '/manifest/video.mpd' in url:
                            if 'auth=' in url or 'token=' in url or 'key=' in url or 'signature=' in url:
                                authenticated_url = url
                                log_with_timestamp(f"🔐 Found authenticated manifest URL")
                                break
                            elif not basic_url:
                                basic_url = url
                                log_with_timestamp(f"🎬 Found basic manifest URL")
                
                if authenticated_url:
                    break
                    
                time.sleep(0.1)
            except Exception as e:
                pass
        
        # Return the best URL we found
        manifest_url = authenticated_url or basic_url
        
        if manifest_url:
            log_with_timestamp(f"✅ Single page load complete - extracted both title and manifest URL")
            return manifest_url, video_title, False
        else:
            log_with_timestamp("⚠ Could not find manifest URL in captured requests")
            return None, video_title, False
            
    except Exception as e:
        log_with_timestamp(f"❌ Error in optimized extraction: {e}")
        return None, None, False

def extract_video_title_only(driver, page_url, domain):
    """Quickly extract just the video title without triggering video player"""
    try:
        # Visit the page
        log_with_timestamp(f"Loading page to check title: {page_url}")
        driver.get(page_url)
        
        # Wait for page to load using WebDriverWait
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass  # Continue even if timeout
        
        # Check if we were redirected to the main updates page (dead link)
        current_url = driver.current_url
        updates_main_page = f"{domain}/updates"
        
        if current_url == updates_main_page or current_url == f"{updates_main_page}/":
            log_with_timestamp(f"⚠ Page redirected to main updates page - this is a dead link")
            return None, True  # None title, True for redirect
        
        # Extract video title from h1 tag
        try:
            h1_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            video_title = h1_element.text.strip()
            if video_title:
                # Clean the title for use as filename
                import re
                video_title = re.sub(r'[<>:"/\\|?*]', '', video_title)
                video_title = video_title.replace('\n', ' ').replace('\r', ' ')
                video_title = ' '.join(video_title.split())  # Remove extra whitespace
                log_with_timestamp(f"Found video title: {video_title}")
                return video_title, False  # Title found, not redirected
            else:
                return None, False
        except Exception as e:
            log_with_timestamp(f"Could not extract video title: {e}")
            return None, False
            
    except Exception as e:
        log_with_timestamp(f"Error extracting video title: {e}")
        return None, False

def extract_mpd_url_with_title(driver, page_url, domain, video_title):
    """Extract manifest URL when we already have the video title"""
    try:
        # Clear previous requests and reload the page to start fresh request monitoring
        del driver.requests
        
        # Reload the page for fresh request monitoring
        log_with_timestamp("Reloading page for manifest URL extraction...")
        driver.get(page_url)
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass  # Continue even if timeout
        
        # Try to trigger video player by looking for and clicking play button
        try:
            # Wait for any play buttons to appear (reduced timeout)
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe"))
                )
            except:
                pass  # Continue even if no play buttons found
            
            play_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[aria-label*='play'], .play-button, button.play, [class*='play'], iframe")
            if play_buttons:
                for button in play_buttons[:2]:  # Try only first 2 elements for speed
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.3)  # Further reduced from 0.5 second
                    except:
                        pass
        except Exception as e:
            pass
        
        # Wait and monitor for authenticated URLs
        log_with_timestamp("Waiting for video player to load and authenticate...")
        
        authenticated_url = None
        basic_url = None
        
        # Monitor requests for up to 2 seconds for speed
        for i in range(1):  # 1 iteration of 2 seconds each = 2 seconds total
            time.sleep(2)  # Further reduced from 3 seconds
            log_with_timestamp(f"Checking requests... ({(i+1)*2}/2 seconds)")
            
            # Debug: Log all requests to help diagnose issues
            all_requests = []
            for request in driver.requests:
                if request.url:
                    all_requests.append(request.url)
            log_with_timestamp(f"Total requests captured: {len(all_requests)}")
            
            # Check all requests so far
            for request in driver.requests:
                if request.url and '/manifest/video.mpd' in request.url:
                    # Look for JWT token pattern (JWT tokens contain dots and are base64-like)
                    if '.eyJ' in request.url:  # JWT tokens have this pattern
                        authenticated_url = request.url
                        log_with_timestamp(f"✓ Found AUTHENTICATED manifest URL with JWT token!")
                        return authenticated_url, video_title
                    elif len(request.url) > 200:
                        # Long URLs are likely authenticated
                        authenticated_url = request.url
                        log_with_timestamp(f"✓ Found LONG manifest URL (likely authenticated)!")
                        return authenticated_url, video_title
                    else:
                        basic_url = request.url
            
            # If we found an authenticated URL, break early
            if authenticated_url:
                break
        
        # Additional wait and check for any video stream URLs
        log_with_timestamp("Final check for any video stream URLs...")
        time.sleep(1)  # Further reduced from 2 seconds
        
        for request in driver.requests:
            if request.url and any(pattern in request.url.lower() for pattern in ['stream', 'cloudflare']):
                if '/manifest/video.mpd' in request.url:
                    log_with_timestamp(f"✓ Found video stream manifest URL")
                    return request.url, video_title
                elif request.url.count('.') >= 2 and len(request.url) > 150:
                    # This might be an authenticated URL without explicit /manifest/video.mpd
                    potential_manifest = request.url
                    if not potential_manifest.endswith('/manifest/video.mpd'):
                        potential_manifest += '/manifest/video.mpd'
                    log_with_timestamp(f"✓ Found potential authenticated URL, trying with manifest path")
                    return potential_manifest, video_title
        
        # Fall back to basic URL if we have one
        if basic_url:
            log_with_timestamp("Warning: Only found basic manifest URL, this may only download a preview")
            return basic_url, video_title
        else:
            log_with_timestamp(f"No manifest URL found for {page_url}")
            return None, video_title
        
    except Exception as e:
        log_with_timestamp(f"Error extracting manifest URL: {e}")
        return None, video_title

def check_file_exists(video_title, output_folder=None):
    """Check if a file with the given title already exists in output folder or current directory (case-insensitive)"""
    if not video_title:
        return False
    
    # Common video file extensions
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Normalize video title for comparison (lowercase)
    video_title_lower = video_title.lower()
    
    # Determine which directory to check
    check_dir = output_folder if output_folder else "."
    
    # Check in specified directory
    try:
        files = os.listdir(check_dir)
        for file in files:
            file_path = os.path.join(check_dir, file)
            if os.path.isfile(file_path):
                # Check if file matches any video extension
                for ext in video_extensions:
                    if file.lower().endswith(ext.lower()):
                        # Extract filename without extension and compare case-insensitively
                        file_title = os.path.splitext(file)[0].lower()
                        if file_title == video_title_lower:
                            log_with_timestamp(f"File already exists: {file_path}")
                            return True
    except OSError:
        log_with_timestamp(f"Could not list files in directory: {check_dir}")
        return False
    
    return False

def run_yt_dlp(manifest_url, cookie, video_title=None, domain=None, output_folder=None):
    """Download video using yt-dlp with the manifest URL and custom filename"""
    if not manifest_url:
        log_with_timestamp("No manifest URL provided")
        return False
    
    # Record start time
    start_time = datetime.now()
    log_with_timestamp(f"Starting download of: {manifest_url}")
    
    cmd = [
        "yt-dlp",
        "--concurrent-fragments", "8",
        "--fragment-retries", "1",
        "--abort-on-error"
    ]
    
    # Add referer if domain is provided
    if domain:
        cmd.extend(["--referer", domain])
    
    # Add custom filename and output folder if available
    if video_title and output_folder:
        # Use the video title as the output filename in the specified folder
        output_template = os.path.join(output_folder, f"{video_title}.%(ext)s")
        cmd.extend(["-o", output_template])
        log_with_timestamp(f"Using custom filename: {video_title}")
        log_with_timestamp(f"Output folder: {output_folder}")
    elif video_title:
        # Use the video title as the output filename in current directory
        output_template = f"{video_title}.%(ext)s"
        cmd.extend(["-o", output_template])
        log_with_timestamp(f"Using custom filename: {video_title}")
    elif output_folder:
        # Use default filename in specified folder
        output_template = os.path.join(output_folder, "%(title)s.%(ext)s")
        cmd.extend(["-o", output_template])
        log_with_timestamp(f"Output folder: {output_folder}")
    
    cmd.append(manifest_url)
    
    # Show concise command info instead of full command
    log_with_timestamp(f"Starting yt-dlp download...")
    if video_title:
        log_with_timestamp(f"Title: {video_title}")
    if output_folder:
        log_with_timestamp(f"Output: {output_folder}")
    log_with_timestamp("=" * 40)
    print()  # Empty line before yt-dlp output
    
    try:
        # Run without capturing output so we can see real-time progress
        result = subprocess.run(cmd)
        
        print()  # Empty line after yt-dlp output
        # Calculate duration
        end_time = datetime.now()
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Remove microseconds
        
        log_with_timestamp("=" * 40)
        log_with_timestamp(f"Completed (Return code: {result.returncode}, Duration: {duration_str})")
        
        # Check if download was successful
        if result.returncode == 0:
            log_with_timestamp("✓ Download successful!")
            return True
        else:
            log_with_timestamp("✗ Download failed!")
            return False
            
    except Exception as e:
        print()  # Empty line after yt-dlp output (in case of error)
        # Calculate duration even on error
        end_time = datetime.now()
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Remove microseconds
        
        log_with_timestamp("=" * 40)
        log_with_timestamp(f"Error: {str(e)[:100]}...")  # Truncate long error messages
        log_with_timestamp(f"Duration: {duration_str}")
        return False

def is_manifest_url(url):
    """Check if URL is already a manifest URL"""
    return url and ('/manifest/video.mpd' in url or url.endswith('.mpd'))

def validate_prerequisites():
    """Validate that required files exist before starting"""
    log_with_timestamp("Validating prerequisites...")
    
    if not os.path.exists("list_video.txt"):
        log_with_timestamp("❌ ERROR: list_video.txt not found in the current directory.")
        log_with_timestamp("💡 SOLUTION: Run 'python3 sitemap_video_parser.py' first to generate the video list.")
        log_with_timestamp("   This script extracts video URLs from the sitemap and creates list_video.txt")
        return False
    
    # Check if list_video.txt is empty
    try:
        with open("list_video.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines:
                log_with_timestamp("❌ ERROR: list_video.txt is empty.")
                log_with_timestamp("💡 SOLUTION: Run 'python3 sitemap_video_parser.py' to populate the video list.")
                return False
            log_with_timestamp(f"✅ Found {len(lines)} video URLs in list_video.txt")
    except Exception as e:
        log_with_timestamp(f"❌ ERROR: Could not read list_video.txt: {e}")
        return False
    
    log_with_timestamp("✅ Prerequisites validated successfully")
    return True

def main():
    # Check if we're in dry-run mode
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        log_with_timestamp("🔍 DRY-RUN MODE: Will preview actions without downloading")
        log_separator()
    
    # Validate prerequisites first
    if not validate_prerequisites():
        log_separator()
        log_with_timestamp("Exiting due to validation errors. Please fix the issues above and try again.")
        sys.exit(1)
    
    log_separator()
    
    # Get user inputs for domain, email, and password
    domain, email, password = get_user_inputs()
    
    # Get output folder
    output_folder = get_output_folder()
    
    # Save output folder info for other scripts to use
    try:
        with open(".download_config.txt", "w") as f:
            f.write(f"output_folder={output_folder}\n")
            f.write(f"domain={domain}\n")
        log_with_timestamp(f"📝 Saved configuration for other scripts")
    except Exception as e:
        log_with_timestamp(f"⚠️  Warning: Could not save config file: {e}")

    with open("list_video.txt", "r") as txtfile:
        links = [line.strip() for line in txtfile if line.strip()]

    if dry_run:
        log_with_timestamp(f"🔍 DRY-RUN: Would process {len(links)} video URLs")
        log_with_timestamp(f"🔍 DRY-RUN: Would save videos to folder: {output_folder}")
        log_with_timestamp(f"🔍 DRY-RUN: Would authenticate with domain: {domain}")
        log_separator()
        log_with_timestamp("DRY-RUN complete. Use without --dry-run to actually download.")
        return

    # Check if we have any page URLs that require authentication
    page_urls = [link for link in links if not is_manifest_url(link)]
    manifest_urls = [link for link in links if is_manifest_url(link)]
    
    log_with_timestamp(f"Found {len(page_urls)} page URLs and {len(manifest_urls)} direct manifest URLs")
    log_separator()
    
    # Only perform login if we have page URLs
    if page_urls:
        log_with_timestamp("Page URLs detected - automated login required for browser extraction")
        driver, cookie = setup_browser_with_login(email, password, domain)
        
        if not driver:
            log_with_timestamp("Login failed, exiting...")
            sys.exit(1)
        log_with_timestamp("✓ Authentication successful, ready to process page URLs")
    else:
        log_with_timestamp("Only direct manifest URLs detected - no authentication needed")
        driver = None
        cookie = None
    
    log_separator()
    log_with_timestamp("Starting video processing...")
    log_separator()

    i = 0
    successful_downloads = 0
    try:
        while i < len(links):
            url = links[i]
            log_separator()
            log_section_break()
            log_with_timestamp(f"Processing link {i+1}/{len(links)}: {url}")
            log_section_break()
            
            if is_manifest_url(url):
                # Direct manifest URL - use it directly
                log_with_timestamp("✓ Direct manifest URL detected, using directly")
                manifest_url = url
                video_title = None  # No title extraction for direct manifest URLs
            else:
                # Page URL - OPTIMIZATION: Extract title and manifest URL in single page load
                log_with_timestamp("Page URL detected, processing video page...")
                if not driver:
                    # This shouldn't happen as we check for page URLs above
                    log_with_timestamp("Error: Need authentication but no driver available")
                    i += 1
                    continue
                
                # Extract both title and manifest URL in a single page load (OPTIMIZED)
                manifest_url, video_title, is_redirect = extract_title_and_manifest_url(driver, url, domain)
                
                if is_redirect:
                    log_with_timestamp("Skipping redirected page...")
                    log_separator()
                    i += 1
                    continue
                
                # Check if file already exists after getting the title
                if video_title and check_file_exists(video_title, output_folder):
                    log_with_timestamp(f"✓ File already exists, skipping: {video_title}")
                    log_separator()
                    i += 1
                    continue
                
                # If we got here, file doesn't exist and we should have manifest_url
                if not manifest_url:
                    log_with_timestamp("⚠ Could not extract manifest URL, skipping video")
                    log_separator()
                    i += 1
                    continue
                
                log_with_timestamp("✓ Ready to download - both title and manifest URL extracted")
            
            if manifest_url:
                # Check if there's enough storage space before downloading
                if not check_storage_space(min_gb=10):
                    log_with_timestamp("Stopping downloads due to insufficient storage space")
                    break
                
                log_separator()
                # Use yt-dlp to download the video
                success = run_yt_dlp(manifest_url, cookie, video_title, domain, output_folder)
                
                log_separator()
                if not success:
                    log_with_timestamp(f"✗ Download failed for link {i+1}")
                    if page_urls:  # Only prompt for new credentials if we're using page URLs
                        log_with_timestamp("Download failed. Trying to re-authenticate...")
                        log_separator()
                        if driver:
                            driver.quit()
                        
                        # Re-authenticate
                        driver, cookie = setup_browser_with_login(email, password, domain)
                        
                        if not driver:
                            log_with_timestamp("Re-authentication failed, skipping remaining page URLs...")
                            log_separator()
                            i += 1
                        # Don't increment i, retry the same URL with new authentication
                    else:
                        log_with_timestamp("Direct manifest URL failed - this might be due to expired authentication in the URL")
                        log_separator()
                        i += 1  # Skip to next URL
                else:
                    successful_downloads += 1
                    log_with_timestamp(f"✓ Successfully downloaded video (#{successful_downloads})")
                    log_separator()
                    i += 1
            else:
                log_with_timestamp(f"✗ Could not get manifest URL from {url}")
                log_with_timestamp("This could be due to:")
                log_with_timestamp("  - Dead link (redirects to /updates/)")
                log_with_timestamp("  - Authentication issues")
                log_with_timestamp("  - Page structure changes")
                log_with_timestamp("Skipping to next video...")
                log_separator()
                i += 1
                
    finally:
        # Show final summary
        log_separator()
        log_section_break()
        log_with_timestamp("DOWNLOAD SUMMARY")
        log_section_break()
        log_with_timestamp(f"Total links processed: {i}")
        log_with_timestamp(f"Successful downloads: {successful_downloads}")
        log_with_timestamp(f"Failed/Skipped: {i - successful_downloads}")
        if i > 0:
            success_rate = (successful_downloads / i) * 100
            log_with_timestamp(f"Success rate: {success_rate:.1f}%")
        log_section_break()
        log_separator()
        
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()