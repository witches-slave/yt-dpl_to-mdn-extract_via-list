# Installation Guide for WSL Ubuntu 24.04

This guide will help you set up the video download scripts on a fresh WSL Ubuntu 24.04 installation.

## Prerequisites

- Windows 10/11 with WSL2 enabled
- Fresh Ubuntu 24.04 WSL installation
- Internet connection

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

Install the required Python packages:

```bash
# Install main dependencies
pip install selenium==4.15.2
pip install selenium-wire==5.1.0
pip install webdriver-manager==4.0.1
pip install yt-dlp
pip install requests

# Verify installations
pip list
```

## Step 7: Download the Scripts

Copy the download scripts to your project directory:

```bash
# If you have the files on Windows, copy them to WSL
# From WSL, you can access Windows files at /mnt/c/
# Example: cp /mnt/c/path/to/your/files/* .

# Or create the files manually (copy the content from the existing scripts)
# You'll need these files:
# - dw.py (main download script)
# - sitemap_parser.py (sitemap parser script)
# - list.txt (URL list file)
```

## Step 8: Test the Installation

Test that everything is working correctly:

```bash
# Test Chrome installation
google-chrome --headless --version

# Test Python imports
python3 -c "
import selenium
import seleniumwire
import yt_dlp
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
   # Should show: dw.py, sitemap_parser.py, list.txt
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x dw.py sitemap_parser.py
   ```

3. **Test the sitemap parser:**
   ```bash
   # Activate virtual environment if not already active
   source venv/bin/activate
   
   # Test sitemap parser (replace with actual sitemap URL)
   python3 sitemap_parser.py https://www.shinybound.com/sitemap.xml
   ```

## Step 10: Running the Scripts

### Always activate the virtual environment first:
```bash
cd ~/shiny-downloads
source venv/bin/activate
```

### Run the sitemap parser:
```bash
# Parse sitemap and generate list.txt
python3 sitemap_parser.py https://www.shinybound.com/sitemap.xml
```

### Run the main download script:
```bash
# Start downloading videos from list.txt
python3 dw.py
```

## Troubleshooting

### Common Issues and Solutions:

1. **Chrome not found error:**
   ```bash
   # Reinstall Chrome
   sudo apt remove google-chrome-stable
   wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
   sudo apt update
   sudo apt install google-chrome-stable -y
   ```

2. **Permission denied errors:**
   ```bash
   # Fix file permissions
   chmod +x *.py
   chmod 644 *.txt
   ```

3. **Python module not found:**
   ```bash
   # Make sure virtual environment is activated
   source venv/bin/activate
   # Reinstall packages if needed
   pip install --force-reinstall selenium selenium-wire webdriver-manager yt-dlp requests
   ```

4. **ffmpeg not found:**
   ```bash
   # Reinstall ffmpeg
   sudo apt update
   sudo apt install ffmpeg -y
   ```

5. **Chrome crashes in headless mode:**
   ```bash
   # Add to your script or run with these Chrome options
   # The scripts should handle this automatically, but if issues persist:
   export DISPLAY=:0
   ```

## File Structure

Your final directory structure should look like this:

```
~/shiny-downloads/
├── venv/                 # Python virtual environment
├── dw.py                # Main download script
├── sitemap_parser.py    # Sitemap parser script
├── list.txt             # URL list (generated by sitemap parser)
└── videos/              # Downloaded videos (created automatically)
```

## Security Notes

- The scripts contain hardcoded credentials - keep them secure
- Only run scripts from trusted sources
- Be aware of the website's terms of service
- Monitor your disk space usage

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
pip install --upgrade selenium selenium-wire webdriver-manager yt-dlp requests

# Update yt-dlp specifically (recommended weekly)
pip install --upgrade yt-dlp
```

---

**Installation complete!** You should now be able to run the video download scripts on your WSL Ubuntu 24.04 system.
