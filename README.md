# Installation Guide for WSL Ubuntu 24.04

This comprehensive guide will help you set up the automated video download and organization system on a fresh WSL Ubuntu 24.04 installation.

## Overview

This system consists of 4 main scripts that work together:
1. **sitemap_video_parser.py** - Extracts video URLs from sitemap OR manual crawling → generates `list_video.txt`
2. **download.py** - Downloads videos from the list → saves to specified folder
3. **sitemap_tag_parser.py** - Extracts tag/model URLs from sitemap OR manual crawling → generates `list_tag.txt` (tag/model URLs only)
4. **tag_organizer.py** - Crawls tag/model pages, matches videos to local files, creates organized folder structure with symlinks

### Key Features:
- **✨ Enhanced Sitemap Support**: Both parsers now work with OR without sitemaps
- **🕷️ Automatic Manual Crawling**: If no sitemap found, automatically offers to crawl pages manually  
- **� Smart Video Matching**: Tag organizer crawls tag/model pages and matches videos to your local files
- **📋 Complete Coverage**: Enhanced pagination logic ensures ALL pages are crawled (not just visible ones)
- **🔧 Runtime Configuration**: All scripts now accept domain/credentials at runtime (no hardcoding needed)
- **📁 User-Selected Video Folder**: Tag organizer lets you choose which video folder to organize

## Prerequisites

- Windows 10/11 with WSL2 enabled
- Fresh Ubuntu 24.04 WSL installation
- Internet connection
- Administrator privileges (for symlink creation on Windows)

## Step 1: Update System Packages

First, update your Ubuntu system to ensure all packages are current:

```bash
sudo apt update && sudo apt upgrade -y
```

## Step 2: Install Python 3.12 and pip

Ubuntu 24.04 comes with Python 3.12, but we need to ensure pip is installed:

```bash
# Install Python pip and development tools
sudo apt install python3-pip python3-dev python3-venv -y

# Verify Python version
python3 --version
# Should show: Python 3.12.x
```

## Step 3: Install System Dependencies

Install required system packages for the video download scripts:

```bash
# Install essential build tools and libraries
sudo apt install build-essential curl wget git -y

# Install media processing tools
sudo apt install ffmpeg -y

# Install Chrome browser dependencies (for Selenium)
sudo apt install -y \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1
```

## Step 4: Install Google Chrome

The scripts use Chrome with Selenium, so we need to install Chrome browser:

```bash
# Download and install Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# Verify Chrome installation
google-chrome --version
```

## Step 5: Create Project Directory and Virtual Environment

Set up a dedicated directory and Python virtual environment:

```bash
# Create project directory
mkdir -p ~/shiny-downloads
cd ~/shiny-downloads

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip in virtual environment
pip install --upgrade pip
```

## Step 6: Install Python Dependencies

Install the required Python packages with compatible versions:

```bash
# Install main dependencies for the download script
# Note: selenium-wire has compatibility issues with newer blinker versions
pip install "blinker<1.8" && pip install selenium-wire && pip install webdriver-manager && pip install yt-dlp && pip install requests

# Note: selenium is included with selenium-wire
# Note: xml.etree.ElementTree is part of Python standard library
# Note: urllib.parse is part of Python standard library

# Verify installations
pip list | grep -E "(selenium|webdriver|yt-dlp|requests|blinker)"
```

### Alternative: If you still encounter issues

If the above doesn't work, try installing specific compatible versions:

```bash
# Uninstall conflicting packages first
pip uninstall selenium-wire blinker -y

# Install compatible versions
pip install "blinker==1.7.0" && pip install selenium-wire==5.1.0 && pip install webdriver-manager && pip install yt-dlp && pip install requests && pip install setuptools
```

## Step 7: Download the Scripts

Copy all required scripts to your project directory:

```bash
# If you have the files on Windows, copy them to WSL
# From WSL, you can access Windows files at /mnt/c/
# Example: cp /mnt/c/path/to/your/files/* .

# Required script files:
# - sitemap_video_parser.py (extracts video URLs from sitemap)
# - download.py (main download script with authentication)
# - sitemap_tag_parser.py (extracts tag/model URLs from sitemap)
# - tag_organizer.py (organizes videos by tags/models)

# Generated files (created by scripts):
# - list_video.txt (video URL list - generated by sitemap_video_parser.py)
# - list_tag.txt (tags & models URL list - generated by sitemap_tag_parser.py)
# - videos/ folder (downloaded videos - created by download.py)
# - tags/ folder (organized symlinks - created by tag_organizer.py)
```

## Step 8: Test the Installation

Test that everything is working correctly:

```bash
# Test Chrome installation
google-chrome --headless --version

# Test Python imports
python3 -c "
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
print('All Python packages imported successfully!')
"

# Test yt-dlp
yt-dlp --version

# Test ffmpeg
ffmpeg -version | head -1
```

## Step 9: Set Up the Scripts

1. **Create or copy your scripts:**
   ```bash
   # Make sure you have these files in ~/shiny-downloads/
   ls -la
   # Should show: sitemap_video_parser.py, download.py, sitemap_tag_parser.py, tag_organizer.py
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x *.py
   ```

3. **Test the scripts installation:**
   ```bash
   # Activate virtual environment if not already active
   source venv/bin/activate
   
   # Test script imports (should not show any errors)
   python3 -c "
   import sys
   sys.path.append('.')
   
   # Test video parser imports
   from sitemap_video_parser import get_domain_input, download_sitemap
   print('✓ sitemap_video_parser.py imports OK')
   
   # Test download script imports  
   from download import get_user_inputs, get_output_folder
   print('✓ download.py imports OK')
   
   # Test tag parser imports
   from sitemap_tag_parser import download_sitemap, extract_tag_model_urls
   print('✓ sitemap_tag_parser.py imports OK')
   
   # Test tag organizer imports
   from tag_organizer import parse_enhanced_tag_list, get_video_files
   print('✓ tag_organizer.py imports OK')
   
   print('All scripts import successfully!')
   "
   ```

## Step 10: Complete Workflow Usage

### **IMPORTANT**: Always run the scripts in this exact order:

#### **Phase 1: Extract Video URLs**
```bash
cd ~/shiny-downloads
source venv/bin/activate

# Step 1: Parse sitemap OR manually crawl for video URLs
python3 sitemap_video_parser.py
# This will:
# - Ask for domain (e.g., shinybound.com)
# - Try to find and parse sitemap.xml first
# - If no sitemap found, offer to manually crawl /updates/ pages
# - Generate list_video.txt with all video URLs
```

#### **Phase 2: Download Videos**
```bash
# Step 2: Download videos using the generated list
python3 download.py
# This will:
# - Ask for domain, email, and password
# - Ask for output folder name (where to save videos)
# - Read list_video.txt and download all videos
# - Save videos to the specified folder
```

#### **Phase 3: Extract Tag/Model URLs and Associated Videos**
```bash
# Step 3: Parse sitemap OR manually crawl for tag/model URLs AND their videos
python3 sitemap_tag_parser.py
# This will:
# - Ask for domain input
# - Try to find and parse sitemap.xml first
# - If no sitemap found, offer to manually crawl /tags/ and /models/ pages
# - Extract individual tag/model URLs from listing pages
# - Generate list_tag.txt with tag/model URLs only
```

#### **Phase 4: Organize by Tags**
```bash
# Step 4: Organize videos by tags and models
python3 tag_organizer.py
# This will:
# - Read list_tag.txt, crawl each tag/model page, match videos to local files, create symlinks
# - Let you select which video folder to organize
# - Create tags/ folder with organized symlinks  
# - Create "No Tag" folder for untagged videos
# - Use fuzzy matching to connect online video titles to your local files
```

### **For Sites WITHOUT Sitemaps:**

Both parsers now automatically detect when sitemaps are unavailable and offer manual crawling:

```bash
# Video parser will crawl:
# • /updates/ page and all pagination pages
# • Extract individual video URLs from each page

# Tag parser will crawl:  
# • /tags/ page and all its pagination
# • /models/ page and all its pagination  
# • Extract individual tag/model URLs from each page
# • Generate list_tag.txt with ONLY tag/model URLs
# • Create complete video-to-tag/model mappings for faster organization
```

### **Enhanced Features:**
- **🎯 Complete pagination coverage**: Generates ALL page URLs from 1 to last (not just visible ones)
- **⚡ Performance optimizations**: Reduced wait times, smarter request handling
- **🔧 User-friendly prompts**: Video folder selection and workflow validation
- **📂 Flexible input**: Runtime domain/email/password/folder input (no hardcoding)

### **Alternative: One-liner for experienced users**
```bash
# Complete workflow (domain will be requested at runtime)
source venv/bin/activate && \
python3 sitemap_video_parser.py && \
python3 download.py && \
python3 sitemap_tag_parser.py && \
python3 tag_organizer.py
```

## Troubleshooting

### Common Issues and Solutions:

1. **"list_video.txt not found" error:**
   ```bash
   # Run the video parser first:
   python3 sitemap_video_parser.py
   ```

2. **"list_tag.txt not found" error:**
   ```bash
   # Run the tag parser first:
   python3 sitemap_tag_parser.py
   # It will ask for domain and handle sitemap/manual crawling automatically
   ```

3. **Video folder not found in tag_organizer.py:**
   ```bash
   # The tag organizer prompts you to select a video folder
   # If you're unsure which folder to choose, check where download.py saved videos:
   cat .download_config.txt  # Shows last used folder from download.py
   ```

4. **Chrome not found error:**
   ```bash
   # Reinstall Chrome
   sudo apt remove google-chrome-stable
   wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
   sudo apt update
   sudo apt install google-chrome-stable -y
   ```

5. **Permission denied errors:**
   ```bash
   # Fix file permissions
   chmod +x *.py
   chmod 644 *.txt
   ```

6. **Python module not found or blinker._saferef error:**
   ```bash
   # Make sure virtual environment is activated
   source venv/bin/activate
   
   # Fix blinker compatibility issue
   pip uninstall selenium-wire blinker -y
   pip install "blinker==1.7.0"
   pip install selenium-wire==5.1.0
   
   # Reinstall other packages if needed
   pip install webdriver-manager yt-dlp requests
   ```

7. **ffmpeg not found:**
   ```bash
   # Reinstall ffmpeg
   sudo apt update
   sudo apt install ffmpeg -y
   ```

8. **Manual crawling taking too long?**
   ```bash
   # The scripts now have optimized wait times and pagination detection
   # You can cancel manual crawling and try to find a sitemap URL manually:
   python3 find_sitemap.py  # Helper script to discover sitemaps
   ```

8. **Chrome crashes in headless mode:**
   ```bash
   # Add to your script or run with these Chrome options
   # The scripts should handle this automatically, but if issues persist:
   export DISPLAY=:0
   ```

9. **Authentication failures:**
   ```bash
   # Ensure you're using the correct domain format:
   # ✓ Correct: https://shinybound.com or shinybound.com
   # ✗ Wrong: shinybound.com/updates or www.shinybound.com
   
   # Double-check email and password
   # Try manual login on the website first
   ```

10. **sitemap_tag_parser.py domain mismatch:**
    ```bash
    # All scripts now ask for domain at runtime
    # Make sure to enter the domain in the correct format (e.g., https://example.com)
    ```

## File Structure

Your final directory structure should look like this:

```
~/shiny-downloads/
├── venv/                          # Python virtual environment
├── sitemap_video_parser.py        # Video URL extractor
├── download.py                    # Main download script with authentication
├── sitemap_tag_parser.py          # Tag/model URL extractor  
├── tag_organizer.py               # Video organization script
├── list_video.txt                 # Video URL list (generated by sitemap_video_parser.py)
├── list_tag.txt                   # Tag/model URL list (generated by sitemap_tag_parser.py)
├── [your_folder_name]/            # Downloaded videos (created by download.py)
└── tags/                          # Organized video symlinks (created by tag_organizer.py)
    ├── tag [Tag Name]/            # Tag-based folders
    ├── model [Model Name]/        # Model-based folders
    ├── tag no tag/                # Videos without tags
    └── source [folder_name]/      # All videos (symlinks)
```

## Workflow Dependencies

**Critical**: Scripts must be run in this order:

1. `sitemap_video_parser.py` → creates `list_video.txt`
2. `download.py` → reads `list_video.txt`, downloads to specified folder
3. `sitemap_tag_parser.py` → creates `list_tag.txt`
4. `tag_organizer.py` → reads `list_tag.txt`, organizes videos from download folder

## Known Issues and Improvements

### **Current Issues:**

1. **sitemap_tag_parser.py inconsistency**: 
   - All scripts now ask for domain at runtime (no hardcoding)
   - Should be fully flexible and user-friendly

2. **Workflow validation missing**:
   - Scripts don't check if prerequisite files exist
   - No validation that download folder matches tag organizer expectations

3. **Error recovery**:
   - Limited resume capability in downloads
   - No rollback mechanism if organization fails

### **Recommended Improvements:**

1. **Standardize sitemap_tag_parser.py**:
   ```bash
   # Current (problematic):
   python3 sitemap_tag_parser.py https://domain.com/sitemap.xml
   
   # Should be (like video parser):
   python3 sitemap_tag_parser.py  # asks for domain interactively
   ```

2. **Add workflow validation**:
   - Check if list_video.txt exists before running download.py
   - Check if list_tag.txt exists before running tag_organizer.py
   - Verify download folder contains videos before organizing

3. **Add dry-run modes**:
   - `--dry-run` flag to preview actions without executing
   - Better error messages with suggested fixes

4. **Improve folder handling**:
   - tag_organizer.py now prompts user to select video folder
   - Better handling of custom folder names

## Security Notes

- Scripts prompt for credentials at runtime (secure)
- Only run scripts from trusted sources
- Be aware of the website's terms of service
- Monitor your disk space usage
- Credentials are not stored permanently

## Performance Tips

- Run downloads during off-peak hours
- Monitor your internet bandwidth usage
- Keep at least 20GB free disk space for optimal performance
- Consider running in `screen` or `tmux` for long download sessions:

```bash
# Install screen for background sessions
sudo apt install screen -y

# Start a screen session
screen -S downloads

# Run your download script
cd ~/shiny-downloads
source venv/bin/activate
python3 dw.py

# Detach with Ctrl+A, D
# Reattach later with: screen -r downloads
```

## Updates and Maintenance

To keep your installation up to date:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
cd ~/shiny-downloads
source venv/bin/activate
pip install --upgrade selenium-wire webdriver-manager yt-dlp requests

# Update yt-dlp specifically (recommended weekly)
pip install --upgrade yt-dlp
```

---

**Installation complete!** You should now be able to run the video download scripts on your WSL Ubuntu 24.04 system.

## Windows Symlink Support for Video Organization

### Overview
The tag organizer script creates symlinks to organize videos by tags and models. To ensure these symlinks work properly in both WSL and Windows (for applications like VLC, Jellyfin, etc.), additional configuration is needed.

### Option 1: Enable Developer Mode (Windows 10+)
This is the recommended approach for modern Windows systems:

1. Open Windows Settings (Windows key + I)
2. Go to **Update & Security** > **For developers** 
3. Turn on **Developer mode**
4. Restart your computer if prompted
5. Symlinks will now work without Administrator privileges

### Option 2: Run as Administrator
If you can't enable Developer Mode:

1. Run Windows Terminal as Administrator
2. Launch WSL from the admin terminal
3. Run your scripts - symlinks will work with elevated privileges

### Option 3: Use the Windows Batch Helper
A batch script is provided to help with Windows compatibility:

```batch
# Run from Windows Command Prompt as Administrator
create_windows_symlinks.bat
```

This script will:
- Check if Developer Mode is enabled
- Provide guidance for enabling it if needed
- Run the Python organizer script with Windows compatibility

### NTFS Drive Configuration for Dual Access

If your videos are stored on an NTFS drive that you want to access from both Windows and WSL:

```bash
# Install NTFS support in WSL
sudo apt install ntfs-3g -y

# Create mount point
sudo mkdir -p /mnt/videos

# Mount NTFS drive with symlink support
# Replace /dev/sdX1 with your actual drive partition
sudo mount -t ntfs-3g /dev/sdX1 /mnt/videos -o uid=1000,gid=1000,dmask=022,fmask=133,windows_names

# For permanent mounting, add to /etc/fstab:
echo "/dev/sdX1 /mnt/videos ntfs-3g uid=1000,gid=1000,dmask=022,fmask=133,windows_names 0 0" | sudo tee -a /etc/fstab
```

### Symlink Compatibility Features

The updated tag organizer script (`tag_organizer.py`) includes multiple fallback methods:

1. **Windows-compatible symlinks** - Created via `mklink` command for full Windows support
2. **Unix symlinks** - Standard symlinks for WSL/Linux
3. **Relative symlinks** - Fallback for permission issues  
4. **Hard links** - Alternative for same-filesystem storage
5. **File copying** - Final fallback to ensure organization works

### Testing Symlinks

You can test symlink compatibility with the included test script:

```bash
cd ~/shiny-downloads
source venv/bin/activate
python3 test_ntfs_compat.py
```

This will test various linking methods and report which ones work on your system.

### Troubleshooting Windows Symlinks

**VLC can't open symlinked files:**
- Ensure Developer Mode is enabled OR run as Administrator
- The script now creates Windows-compatible symlinks automatically
- Try playing files directly from Windows Explorer to test

**"Operation not supported" error:**
- Enable Developer Mode in Windows Settings
- OR run WSL as Administrator
- The script will fall back to hard links or copying

**Jellyfin doesn't see symlinked videos:**
- Ensure Jellyfin service has permissions to follow symlinks
- Use absolute paths (handled automatically by the script)
- Consider using hard links instead (automatic fallback)

**Cross-platform compatibility:**
- Store videos on NTFS drive with proper mount options
- Use absolute paths for symlinks (handled automatically)
- Enable Windows symlink support as described above
