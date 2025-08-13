# Video Organization and Jellyfin Setup Guide

This comprehensive guide will help you set up an automated video download and organization system optimized for Jellyfin media server.

## Overview

This system consists of 2 main scripts that work together:
1. **download.py** - Downloads videos from URL lists → saves to specified folder
2. **unified_video_organizer.py** - Unified script that crawls /updates/ pages, extracts metadata, creates organized folder structure with symlinks, downloads model images, and generates NFO files for Jellyfin

### Key Features:
- **🎯 Unified Workflow**: Single script handles page crawling, organization, metadata extraction, and NFO generation
- **📄 Automatic Pagination**: Discovers and processes all pages in /updates/ automatically
- **📊 Rich Metadata**: Extracts tags, models, related videos, and downloads model images
- **🔗 Smart Symlinks**: Creates organized folder structure with relative symlinks for cross-platform compatibility
- **📁 Jellyfin Integration**: Generates NFO files and folder.jpg images for perfect Jellyfin integration
- **⚡ Efficient Processing**: Model image caching prevents redundant downloads
- **🔍 Missing Video Detection**: Reports videos found online but missing locally
- **📋 Consistent Naming**: Normalizes all titles to uppercase for consistency

## Prerequisites

- Windows 10/11 with WSL2 enabled or Linux development machine
- Ubuntu 24.04 (WSL or native)
- Raspberry Pi 5 with Ubuntu Server 24.04 (for Jellyfin server)
- NTFS external drive for media storage
- Internet connection
- Administrator privileges (for symlink creation on Windows)

## Step 1: Development Machine Setup

### Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### Install Python 3.12 and Dependencies

```bash
# Install Python and development tools
sudo apt install python3-pip python3-dev python3-venv build-essential curl wget git -y

# Install Chrome browser dependencies (for Selenium)
sudo apt install -y \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgtk-3-0 libnspr4 libnss3 \
    libwayland-client0 libxcomposite1 libxdamage1 libxfixes3 \
    libxkbcommon0 libxrandr2 xdg-utils libu2f-udev libvulkan1

# Install Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install google-chrome-stable -y
```

### Set Up Python Environment

```bash
# Create project directory
mkdir -p ~/video-organizer
cd ~/video-organizer

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install "blinker<1.8" selenium-wire webdriver-manager requests setuptools Pillow
```

## Step 2: Raspberry Pi 5 Setup (Jellyfin Server)

### Install Ubuntu Server 24.04

1. Flash Ubuntu Server 24.04 LTS to SD card
2. Enable SSH in user-data (cloud-init)
3. Boot Pi and complete initial setup

### Basic System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install curl wget git htop -y

# Configure timezone
sudo timedatectl set-timezone Your/Timezone
```

### Install Jellyfin (Official Method)

```bash
# Install Jellyfin using official script
curl https://repo.jellyfin.org/install-debuntu.sh | sudo bash

# Enable and start Jellyfin
sudo systemctl enable jellyfin
sudo systemctl start jellyfin

# Check status
sudo systemctl status jellyfin
```

### Configure NTFS Drive Mount

```bash
# Install NTFS support
sudo apt install ntfs-3g -y

# Create mount point
sudo mkdir -p /mnt/media

# Find your drive (look for NTFS partition)
sudo fdisk -l

# Mount drive (replace sdX1 with your actual partition)
sudo mount -t ntfs-3g /dev/sdX1 /mnt/media -o uid=jellyfin,gid=jellyfin,umask=022

# Add to fstab for permanent mounting
echo "UUID=$(sudo blkid -s UUID -o value /dev/sdX1) /mnt/media ntfs-3g uid=jellyfin,gid=jellyfin,umask=022 0 0" | sudo tee -a /etc/fstab

# Verify mount
df -h /mnt/media
```

### Configure Jellyfin Data Location

```bash
# Stop Jellyfin
sudo systemctl stop jellyfin

# Create config directory on SD card
sudo mkdir -p /opt/jellyfin-config
sudo chown jellyfin:jellyfin /opt/jellyfin-config

# Create override directory
sudo mkdir -p /etc/systemd/system/jellyfin.service.d

# Create override configuration
sudo tee /etc/systemd/system/jellyfin.service.d/override.conf << EOF
[Service]
Environment="JELLYFIN_CONFIG_DIR=/opt/jellyfin-config"
Environment="JELLYFIN_DATA_DIR=/opt/jellyfin-config/data"
Environment="JELLYFIN_CACHE_DIR=/opt/jellyfin-config/cache"
EOF

# Reload systemd and start Jellyfin
sudo systemctl daemon-reload
sudo systemctl start jellyfin
sudo systemctl status jellyfin
```

## Step 3: Download and Organization Workflow

### Prepare Video Lists

Create your video URL lists manually or use existing parsers:

```bash
# Create list_video.txt with video URLs (one per line)
# Format: https://domain.com/updates/video-title/
echo "https://example.com/updates/video1/" > list_video.txt
echo "https://example.com/updates/video2/" >> list_video.txt
```

### Download Videos

```bash
cd ~/video-organizer
source venv/bin/activate

# Run download script
python3 download.py
# Will prompt for:
# - Domain
# - Email/password for authentication
# - Output folder name
```

### Organize Videos for Jellyfin

```bash
# Run unified organizer
python3 unified_video_organizer.py
# Will prompt for:
# - Domain (e.g., https://shinybound.com)
# - Source video folder (where downloaded videos are stored)
# - Tags folder (where symlinks will be created)

# The script will:
# 1. Automatically crawl all /updates/ pages 
# 2. Extract metadata from each video page
# 3. Create organized folder structure with symlinks
# 4. Download model images as folder.jpg
# 5. Generate NFO files for Jellyfin
# 6. Report any missing videos
```

### Folder Structure Created

```
/mnt/media/
├── videos/                    # Original downloads
│   ├── video1.mp4
│   └── video2.mp4
└── tags/                      # Symlink organization (tags folder)
    ├── source [videos]/       # All videos (symlinks)
    ├── tag [tagname]/         # Tag-based folders
    │   ├── folder.jpg         # Tag thumbnail (if available)
    │   ├── tvshow.nfo         # Jellyfin metadata
    │   └── video1.mp4         # Symlink to original
    ├── model [modelname]/     # Model-based folders
    │   ├── folder.jpg         # Model image
    │   ├── actress.nfo        # Jellyfin actress metadata
    │   └── video2.mp4         # Symlink to original
    └── tag no tag/           # Untagged videos
```

## Step 4: Jellyfin Library Setup

### Add Libraries in Jellyfin

1. Access Jellyfin web interface: `http://pi-ip:8096`
2. Go to Dashboard → Libraries → Add Media Library
3. Add these libraries:

**Main Video Collection:**
- Content type: Movies
- Folder: `/mnt/media/tags/source [videos]`
- Enable: Fetch metadata from the internet = No
- Enable: Save artwork into media folders = Yes

**Tags Collection:**
- Content type: TV Shows  
- Folder: `/mnt/media/tags/tag*` (add each tag folder separately)
- Enable: Fetch metadata from the internet = No
- Enable: Save artwork into media folders = Yes

**Models Collection:**
- Content type: TV Shows  
- Folder: `/mnt/media/tags/model*` (add each model folder separately)
- Enable: Fetch metadata from the internet = No
- Enable: Save artwork into media folders = Yes

### Configure Metadata Settings

1. Dashboard → Libraries → Manage Libraries
2. For each library, click the three dots → Manage
3. Metadata tab:
   - Uncheck all internet metadata providers
   - Check "NFO" provider and set it to highest priority
   - Check "Local Image Provider" and set to highest priority

## Step 5: Automation and Maintenance

### Automated Organization Script

Create a simple update script:

```bash
#!/bin/bash
# update_jellyfin.sh

cd ~/video-organizer
source venv/bin/activate

echo "Starting video organization update..."

# Run organizer (will skip existing files)
python3 unified_video_organizer.py

echo "Organization complete. Updating Jellyfin library..."

# Trigger Jellyfin library scan (optional)
# curl -X POST "http://pi-ip:8096/Library/Refresh" -H "X-Emby-Token: YOUR_API_TOKEN"

echo "Update complete!"
```

### Copy to Raspberry Pi

After organization on development machine:

```bash
# Sync organized folder to Pi (preserving symlinks)
rsync -avz --copy-links ~/video-organizer/tags/ pi@pi-ip:/mnt/media/tags/

# Or if using shared NTFS drive, just move organized content:
# mv ~/video-organizer/tags/* /path/to/ntfs/mount/tags/
```

## Troubleshooting

### Common Issues

**Symlinks don't work on Windows:**
- Enable Developer Mode in Windows Settings
- Or run WSL as Administrator

**Jellyfin doesn't show metadata:**
- Verify NFO files are created in video folders
- Check that NFO provider is enabled and prioritized
- Ensure folder.jpg images are present

**Model images not downloading:**
- Check internet connection
- Verify credentials are correct
- Check Chrome/Selenium setup

**Missing videos reported:**
- Video titles may not match exactly
- Check if videos are in subfolders
- Verify video file extensions are supported

### Performance Tips

- Use SSD for Jellyfin config/database
- Keep video files on fast external drive
- Run organization on powerful development machine
- Use relative symlinks for cross-platform compatibility

### Security Notes

- Store media on NTFS drive (read-only mount on Pi for security)
- Keep Jellyfin config on SD card (easily replaceable)
- Use strong passwords for web authentication
- Consider VPN for remote access

## Advanced Configuration

### Custom NFO Templates

Edit the NFO generation functions in `unified_video_organizer.py` to customize metadata format.

### Additional Metadata Sources

The script can be extended to extract additional metadata fields by modifying the `extract_video_metadata` function.

### Batch Processing

For large collections, consider running the organizer in batches:

```bash
# Process specific URL ranges
head -100 list_video.txt > batch1.txt
python3 unified_video_organizer.py  # Use batch1.txt as input
```

---

This setup provides a robust, automated system for organizing video content with rich metadata for Jellyfin, optimized for a Raspberry Pi 5 server with all heavy processing done on a development machine.
