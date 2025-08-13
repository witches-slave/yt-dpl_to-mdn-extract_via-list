# Raspberry Pi 5 + Ubuntu Server 24 + Jellyfin Media Server Setup Guide

This comprehensive guide will help you set up a Raspberry Pi 5 with Ubuntu Server 24.04 LTS as a dedicated Jellyfin media server for your downloaded video collection.

## Table of Contents
1. [Hardware Requirements](#hardware-requirements)
2. [Ubuntu Server 24.04 Installation](#ubuntu-server-2404-installation)
3. [Initial System Configuration](#initial-system-configuration)
4. [Network Configuration](#network-configuration)
5. [Storage Configuration](#storage-configuration)
6. [Jellyfin Installation](#jellyfin-installation)
7. [Integration with Tag Organization System](#integration-with-tag-organization-system)
8. [Performance Optimization](#performance-optimization)
9. [Security Hardening](#security-hardening)
10. [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

### Essential Components
- **Raspberry Pi 5** (8GB RAM recommended for 4K content)
- **High-quality microSD card** (64GB minimum, Class 10/UHS-I, recommend SanDisk Extreme Pro)
- **USB-C Power Supply** (Official Raspberry Pi 27W USB-C Power Supply recommended)
- **Active cooling solution** (Official Active Cooler or equivalent)
- **Ethernet cable** (for stable network connection)

### Optional but Recommended
- **External storage** (USB 3.0 SSD/HDD for media storage)
- **Case with ventilation** (for thermal management)
- **HDMI cable** (for initial setup if needed)
- **USB keyboard** (for initial configuration)

### Storage Recommendations
- **OS Storage**: 64GB+ microSD card (for OS only)
- **Media Storage**: External USB 3.0 SSD/HDD (500GB+ depending on your collection)
- **Backup Storage**: Additional external drive for backups

---

## Ubuntu Server 24.04 Installation

### Step 1: Download Ubuntu Server Image

1. Visit the official Ubuntu website:
   ```
   https://ubuntu.com/download/raspberry-pi
   ```

2. Download **Ubuntu Server 24.04 LTS** for Raspberry Pi (ARM64 version)
   ```bash
   # Direct download link (as of 2024):
   wget https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04-preinstalled-server-arm64+raspi.img.xz
   ```

### Step 2: Flash the Image to SD Card

**Using Raspberry Pi Imager (Recommended):**
1. Download and install Raspberry Pi Imager from: https://www.raspberrypi.org/software/
2. Select "Use custom image" and choose the downloaded Ubuntu Server image
3. Select your SD card
4. Click the gear icon for advanced options:
   - Enable SSH
   - Set username and password
   - Configure WiFi (optional, Ethernet recommended)
5. Write the image to the SD card

**Using dd command (Linux/macOS):**
```bash
# Identify your SD card device
lsblk

# Unmount the SD card if mounted
sudo umount /dev/sdX*

# Write the image (replace /dev/sdX with your SD card device)
sudo dd if=ubuntu-24.04-preinstalled-server-arm64+raspi.img of=/dev/sdX bs=4M status=progress

# Sync to ensure all data is written
sudo sync
```

### Step 3: Initial Boot Setup

1. Insert the SD card into your Pi 5
2. Connect Ethernet cable
3. Power on the Pi
4. Find the Pi's IP address on your network:
   ```bash
   # From your router's admin panel, or use nmap:
   nmap -sn 192.168.1.0/24 | grep -A2 "Raspberry\|B8:27:EB\|DC:A6:32\|E4:5F:01"
   ```

---

## Initial System Configuration

### Step 1: SSH Connection and First Boot

1. SSH into your Pi (replace with actual IP):
   ```bash
   ssh ubuntu@192.168.1.XXX
   ```

2. First boot will require password change (default: ubuntu/ubuntu)

3. Update system packages:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. Install essential packages:
   ```bash
   sudo apt install -y curl wget git htop tree unzip software-properties-common apt-transport-https
   ```

### Step 2: System Optimization for Media Server

1. **Increase GPU memory split** (for hardware acceleration):
   ```bash
   sudo nano /boot/firmware/config.txt
   ```
   Add these lines at the end:
   ```
   # GPU memory for hardware acceleration
   gpu_mem=128
   
   # Enable hardware acceleration
   dtoverlay=vc4-kms-v3d
   
   # Optimize for sustained performance
   arm_freq=2400
   over_voltage=6
   
   # Enable all USB ports at full speed
   dwc_otg.fiq_enable=1
   dwc_otg.fiq_fsm_enable=1
   dwc_otg.fiq_fsm_mask=0x3
   ```

2. **Configure system limits**:
   ```bash
   sudo nano /etc/security/limits.conf
   ```
   Add:
   ```
   * soft nofile 65536
   * hard nofile 65536
   jellyfin soft nofile 65536
   jellyfin hard nofile 65536
   ```

3. **Optimize memory settings**:
   ```bash
   sudo nano /etc/sysctl.conf
   ```
   Add:
   ```
   # Memory optimization for media server
   vm.swappiness=10
   vm.dirty_ratio=15
   vm.dirty_background_ratio=5
   net.core.rmem_max=16777216
   net.core.wmem_max=16777216
   ```

4. **Reboot to apply changes**:
   ```bash
   sudo reboot
   ```

---

## Network Configuration

### Step 1: Set Static IP Address

1. **Find your current network configuration**:
   ```bash
   ip route show default
   ip addr show
   ```

2. **Edit netplan configuration**:
   ```bash
   sudo nano /etc/netplan/50-cloud-init.yaml
   ```

3. **Configure static IP** (adjust values for your network):
   ```yaml
   network:
     version: 2
     ethernets:
       eth0:
         dhcp4: false
         addresses:
           - 192.168.1.100/24  # Choose available IP in your range
         nameservers:
           addresses:
             - 8.8.8.8
             - 8.8.4.4
             - 1.1.1.1
         routes:
           - to: default
             via: 192.168.1.1   # Your router's IP
   ```

4. **Apply the configuration**:
   ```bash
   sudo netplan apply
   ```

5. **Verify the connection**:
   ```bash
   ping -c 4 8.8.8.8
   ip addr show eth0
   ```

### Step 2: Configure Hostname

1. **Set hostname**:
   ```bash
   sudo hostnamectl set-hostname jellyfin-pi
   ```

2. **Update hosts file**:
   ```bash
   sudo nano /etc/hosts
   ```
   Add:
   ```
   192.168.1.100   jellyfin-pi
   ```

---

## Storage Configuration

### Step 1: External Storage Setup

1. **Connect your external drive** via USB 3.0

2. **Identify the drive**:
   ```bash
   lsblk
   sudo fdisk -l
   ```

3. **Check existing filesystem** (for drives with existing data):
   ```bash
   # Check what filesystem is already on the drive
   sudo file -s /dev/sda1
   
   # If it shows data or a filesystem type, the drive has existing data
   # Example outputs:
   # - ext4 filesystem: "/dev/sda1: Linux rev 1.0 ext4 filesystem data"
   # - NTFS filesystem: "/dev/sda1: DOS/MBR boot sector, code offset 0x52+2"
   # - No filesystem: "/dev/sda1: data" (this means it needs formatting)
   ```

   **⚠️ IMPORTANT: Only format if the drive is completely new and shows no filesystem!**
   
   **For NEW drives only** (will erase all data - skip if you have existing media):
   ```bash
   # ONLY run this on a completely new/empty drive!
   # Replace /dev/sda with your actual drive
   sudo fdisk /dev/sda
   
   # Create new partition table:
   # Press 'g' for GPT
   # Press 'n' for new partition
   # Press Enter for defaults
   # Press 'w' to write changes
   
   # Format as ext4 (ONLY for new drives)
   sudo mkfs.ext4 /dev/sda1
   ```

   **For drives with existing data** (most common case):
   ```bash
   # Check the filesystem type and mount directly
   # The drive should already be partitioned and formatted
   # Just proceed to mounting step below
   ```

4. **Create mount points**:
   ```bash
   sudo mkdir -p /media/jellyfin
   ```

5. **Get UUID of the drive**:
   ```bash
   sudo blkid /dev/sda1
   ```

6. **Configure automatic mounting**:
   ```bash
   sudo nano /etc/fstab
   ```
   
   **For ext4 filesystems** (Linux native):
   ```
   UUID=your-uuid-here /media/jellyfin ext4 defaults,noatime,nofail 0 2
   ```
   
   **For NTFS filesystems** (Windows drives - most common):
   ```bash
   # First install NTFS support
   sudo apt install ntfs-3g -y
   ```
   Then add to `/etc/fstab`:
   ```
   UUID=your-uuid-here /media/jellyfin ntfs-3g defaults,noatime,nofail,uid=1000,gid=1000,umask=022 0 0
   ```
   
   **For exFAT filesystems** (cross-platform drives):
   ```bash
   # First install exFAT support
   sudo apt install exfat-fuse exfatprogs -y
   ```
   Then add to `/etc/fstab`:
   ```
   UUID=your-uuid-here /media/jellyfin exfat defaults,noatime,nofail,uid=1000,gid=1000,umask=022 0 0
   ```

7. **Mount the drive**:
   ```bash
   sudo mount -a
   sudo systemctl daemon-reload
   ```

8. **Set proper permissions**:
   ```bash
   sudo chown -R $USER:$USER /media/jellyfin
   sudo chmod -R 755 /media/jellyfin
   ```

### Step 2: Directory Structure

Create organized directory structure for your media (adapt to your existing structure):

**If you have existing media on the drive:**
```bash
# Navigate to your mounted drive
cd /media/jellyfin

# Check what's already there
ls -la
```


**Example final structure with existing media:**
```
SD Card (fast):
├── /var/lib/jellyfin/          # Jellyfin config & database
├── /var/cache/jellyfin/        # Jellyfin cache
├── /var/log/jellyfin/          # Jellyfin logs
└── /tmp/jellyfin/              # Jellyfin transcoding (default location)

External NTFS Drive (large storage):
/media/jellyfin/
├── sourcefolder/               # Your existing media folders
├── sourcefolder2/              # More existing media folders
├── sourcefolder3/              # More existing media folders
├── movies/                     # Your existing movies (if any)
└── tags/                       # Created by tag_organizer.py with symlinks
    ├── tag [TagName]/          # Symlinks to videos with this tag
    ├── model [ModelName]/      # Symlinks to videos with this model
    ├── tag no tag/             # Videos without tags
    └── source [foldername]/    # All videos from each source folder
```

---

## Jellyfin Installation

### Step 1: Install Jellyfin (Official Method)

**Jellyfin provides an automated installation script for Ubuntu/Debian systems:**

1. **Install Jellyfin using the official script** (recommended):
   ```bash
   # Download and run the official Jellyfin installation script
   curl https://repo.jellyfin.org/install-debuntu.sh | sudo bash
   ```

   **Optional: Verify script integrity** (recommended for security):
   ```bash
   # Download script and verify checksum
   curl -s https://repo.jellyfin.org/install-debuntu.sh -o install-debuntu.sh
   diff <( sha256sum install-debuntu.sh ) <( curl -s https://repo.jellyfin.org/install-debuntu.sh.sha256sum )
   
   # If output is empty, integrity is verified. Inspect script (optional):
   less install-debuntu.sh
   
   # Run the verified script:
   sudo bash install-debuntu.sh
   ```

2. **Alternative: Manual repository setup** (if you prefer manual control):
   ```bash
   # Add Jellyfin repository manually
   curl -fsSL https://repo.jellyfin.org/jellyfin_team.gpg.key | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/jellyfin.gpg
   echo "deb [arch=$( dpkg --print-architecture )] https://repo.jellyfin.org/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/jellyfin.list
   
   # Update package list and install
   sudo apt update
   sudo apt install -y jellyfin
   ```

### Step 2: Install Additional Dependencies

**Note**: If you used the official Jellyfin script above, Jellyfin is already installed. This step adds multimedia and hardware acceleration support.

1. **Install multimedia and hardware acceleration packages**:
   ```bash
   # Hardware acceleration and codec support for Raspberry Pi 5
   sudo apt install -y \
     vainfo \
     mesa-va-drivers \
     ffmpeg \
     libavcodec-extra
   ```

2. **Add jellyfin user to video groups** (for hardware acceleration):
   ```bash
   sudo usermod -aG video jellyfin
   sudo usermod -aG render jellyfin
   ```

### Step 3: Configure Jellyfin Directories

**Important**: Keep Jellyfin's system files on the fast SD card, only media goes on external drive.

1. **Stop Jellyfin service**:
   ```bash
   sudo systemctl stop jellyfin
   ```

2. **Configure directories for optimal performance**:
   ```bash
   # Keep Jellyfin config/database/cache/transcodes on fast SD card (default locations)
   # External drive is only for media files
   ```

   **Performance Note**: 
   - **Keep on SD card**: Configuration, database, cache, and transcoding (for fastest access)
   - **External drive**: Media files only

3. **Create optimal Jellyfin service configuration**:
   ```bash
   sudo mkdir -p /etc/systemd/system/jellyfin.service.d
   sudo nano /etc/systemd/system/jellyfin.service.d/override.conf
   ```
   Add:
   ```ini
   [Service]
   # Increase file limits
   LimitNOFILE=65536
   # Performance optimizations
   Environment="JELLYFIN_FFMPEG_ARGS=-threads 4 -thread_queue_size 512"
   ```

4. **Start and enable Jellyfin**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start jellyfin
   sudo systemctl enable jellyfin
   ```

### Step 4: Initial Jellyfin Configuration

1. **Access Jellyfin web interface**:
   Open your browser and go to: `http://192.168.1.100:8096`
   (Replace with your Pi's IP address)

2. **Complete initial setup**:
   - Create admin account
   - Add media libraries pointing to `/media/jellyfin/sourcefolder`, `/media/jellyfin/sourcefolder2`, etc.
   - Configure hardware acceleration (Settings → Playback → Hardware acceleration: Video Acceleration API (VAAPI))
   - Transcoding will use default SD card location (optimal for 128GB SD card)

---

## Integration with Tag Organization System

**Important Note**: All script-related setup (Python environment, dependencies, downloading, and tag organization) should be done on your **development machine**. The Pi serves only as a media server. Refer to the main `README.md` for complete setup instructions for the download and organization scripts.

### Step 1: Development Machine Setup (Primary Workflow)

**On your development machine** (Windows/Linux/macOS), follow the setup instructions in the main `README.md` file to:

1. ✅ **Install Python environment and dependencies** (Chrome, Selenium, etc.)
2. ✅ **Setup the download scripts** (`download.py`, parsers, etc.)
3. ✅ **Configure tag organization** (`tag_organizer.py`, `list_tag.txt`)
4. ✅ **Download and organize videos** directly to your NTFS media drive

### Step 2: Media Organization Workflow

**Recommended Workflow** (all done on development machine):

1. **Connect NTFS drive** to your development machine (USB, external dock, etc.)

2. **Download videos** using your existing scripts:
   ```bash
   # On your development machine (follow README.md setup)
   cd /path/to/your/scripts
   source venv/bin/activate
   python3 download.py
   ```

3. **Organize with symlinks** using the updated tag_organizer.py:
   ```bash
   # tag_organizer.py now creates relative symlinks for portability
   python3 tag_organizer.py
   # When prompted, select your NTFS drive's media folder
   # Script creates: tags/, model/, source/ folders with relative symlinks
   ```

4. **Transfer to Pi**: Simply connect the organized NTFS drive to your Pi
   - All symlinks work immediately (they're relative paths within the drive)
   - No re-processing needed on the Pi

### Step 3: Pi Configuration for Media Access

**On the Pi** (minimal setup - no scripts needed):

1. **No script dependencies required** - the Pi only serves pre-organized media

2. **Setup automatic library refresh** (optional):
   ```bash
   # Create simple refresh script (optional)
   nano /home/ubuntu/refresh_jellyfin.sh
   ```
   Add:
   ```bash
   #!/bin/bash
   echo "Refreshing Jellyfin library..."
   curl -X POST "http://localhost:8096/Library/Refresh" \
        -H "X-Emby-Authorization: MediaBrowser Token=YOUR_API_TOKEN"
   echo "Library refresh triggered"
   ```

   ```bash
   chmod +x /home/ubuntu/refresh_jellyfin.sh
   ```

3. **Create Jellyfin API token** (if using refresh script):
   - Go to Jellyfin Dashboard → API Keys
   - Create new API key for library refresh
   - Update the refresh script with your token

### Step 4: Jellyfin Library Configuration

**Understanding the Tag Organization System:**

The `tag_organizer.py` script creates a sophisticated folder structure using symlinks to organize your videos without duplicating files. Here's how it works:

1. **Source videos** remain in their original download folders (e.g., `sourcefolder/`, `sourcefolder2/`)
2. **Symlinks** are created in the `tags/` folder pointing to the original files
3. **Organization structure** created by tag_organizer.py:

```
/media/jellyfin/
├── sourcefolder/               # Original downloaded videos
├── sourcefolder2/              # More original videos
├── movies/                     # Movies (if any)
└── tags/                       # Organized symlinks (created by tag_organizer.py)
    ├── tag [TagName]/          # Videos with specific tags (e.g., "tag BDSM")
    ├── model [ModelName]/      # Videos featuring specific models (e.g., "model Jane Doe")
    ├── tag no tag/             # Videos without any tags
    └── source [foldername]/    # All videos from each source folder
```

**Setting up Jellyfin Libraries:**

1. **Add media libraries in Jellyfin** based on how you want to browse:

   **Option A: Browse by Source + Organized Tags (Recommended)**
   ```
   Library Name: "Source Videos"
   Content Type: Movies or Shows
   Folder: /media/jellyfin/sourcefolder
            /media/jellyfin/sourcefolder2
            (add all your source folders)
   
   Library Name: "By Tags"  
   Content Type: Movies or Shows
   Folder: /media/jellyfin/tags/tag*/
   
   Library Name: "By Models"
   Content Type: Movies or Shows  
   Folder: /media/jellyfin/tags/model*/
   
   Library Name: "Untagged Videos"
   Content Type: Movies or Shows
   Folder: /media/jellyfin/tags/tag no tag/
   ```

2. **Library settings**:
   - Enable "Real-time monitoring" for automatic updates
   - Set content type appropriately for each library
   - Configure metadata providers as needed

**How the Tag Organization Works:**

1. **Download Phase** (done on development machine):
   - Videos are downloaded to source folders like `sourcefolder/`, `sourcefolder2/`
   - Each video keeps its original filename and location

2. **Organization Phase** (done on development machine):
   - `tag_organizer.py` reads `list_tag.txt` (created by `sitemap_tag_parser.py`)
   - Script crawls each tag/model page to find which videos belong to each tag
   - Creates **relative symlinks** in `tags/` folder pointing to original videos
   - No videos are moved or duplicated - only symlinks are created

3. **Jellyfin Benefits**:
   - **Browse by tag**: "BDSM", "Bondage", "Latex" etc. folders
   - **Browse by model**: Individual model folders with their videos
   - **Browse by source**: All videos from each download source
   - **Find untagged**: Videos that don't have tags assigned
   - **No duplicates**: Same video appears in multiple categories without using extra space

**Example of what you'll see in Jellyfin:**
```
"By Tags" Library:
├── tag BDSM/                   # 15 videos
├── tag Bondage/                # 23 videos  
├── tag Latex/                  # 8 videos
└── tag no tag/                 # 5 videos

"By Models" Library:
├── model Jane Doe/             # 12 videos
├── model Sarah Smith/          # 7 videos
└── model Alex Johnson/         # 9 videos

"Source Videos" Library:
├── sourcefolder/               # 50 videos (originals)
├── sourcefolder2/              # 30 videos (originals)
└── movies/                     # 10 videos (originals)
```

All folders show the same videos, but organized differently for easy browsing!

### Workflow Summary

**Your streamlined development workflow:**

**All script work done on development machine** (following README.md setup):

1. **Setup environment** on development machine (see README.md):
   - Install Python, Chrome, Selenium dependencies
   - Clone repository and setup virtual environment
   - Configure download scripts and tag lists

2. **Download and organize workflow**:
   ```bash
   # On development machine with NTFS drive connected
   cd /path/to/yt-dpl_to-mdn-extract_via-list
   source venv/bin/activate
   
   # Download videos to NTFS drive
   python3 download.py
   
   # Organize with relative symlinks (portable across machines)
   python3 tag_organizer.py
   # When prompted, select your NTFS drive's media folder
   ```

3. **Deploy to Pi**:
   - Connect organized NTFS drive to Pi
   - Symlinks work immediately (relative paths within drive)
   - Jellyfin serves pre-organized content

**Pi's role** (minimal setup - no scripts):
- ✅ **Media server only** - serves content via Jellyfin
- ✅ **No Python dependencies** - no Chrome, Selenium, or scripts needed
- ✅ **No download/organization** - content arrives pre-organized
- ✅ **Fast SD card storage** - for Jellyfin config and database only
- ✅ **Large NTFS storage** - for media files and symlink organization

**Benefits of this approach:**
- ✅ **Clean separation** - development machine does the work, Pi serves content
- ✅ **Relative symlinks** - portable between machines and mount points
- ✅ **No duplicate setup** - scripts run where you already have them configured
- ✅ **Pi stays lightweight** - no heavy dependencies or processing
- ✅ **Flexible workflow** - organize content anywhere, serve from Pi
- ✅ **Development environment** - use your familiar setup for downloads/organization

---

## Performance Optimization

### Step 1: Hardware Acceleration Setup

1. **Check hardware acceleration support**:
   ```bash
   vainfo
   ```

2. **Configure Jellyfin hardware acceleration**:
   - Go to Dashboard → Playback
   - Hardware acceleration: `Video Acceleration API (VAAPI)`
   - VA-API Device: `/dev/dri/renderD128`
   - Enable hardware decoding for: H264, HEVC, VP8, VP9
   - Enable hardware encoding for: H264, HEVC

### Step 2: Transcoding Optimization

1. **Transcoding uses SD card by default** (fastest option with 128GB storage):
   ```bash
   # Jellyfin uses /tmp/jellyfin/ by default for transcoding
   # This is already on your fast SD card - no changes needed
   # 128GB SD card provides plenty of space for temporary transcoding files
   ```

### Step 3: Network Optimization

1. **Optimize network buffer sizes**:
   ```bash
   sudo nano /etc/sysctl.conf
   ```
   Add:
   ```
   # Network optimization for streaming
   net.core.rmem_default=262144
   net.core.rmem_max=16777216
   net.core.wmem_default=262144
   net.core.wmem_max=16777216
   net.ipv4.tcp_rmem=4096 262144 16777216
   net.ipv4.tcp_wmem=4096 262144 16777216
   ```

2. **Apply settings**:
   ```bash
   sudo sysctl -p
   ```

---

## Security Hardening

### Step 1: Firewall Configuration

1. **Install and configure UFW**:
   ```bash
   sudo apt install ufw
   
   # Default policies
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   
   # Allow SSH
   sudo ufw allow ssh
   
   # Allow Jellyfin
   sudo ufw allow 8096/tcp
   
   # Allow local network access
   sudo ufw allow from 192.168.1.0/24
   
   # Enable firewall
   sudo ufw enable
   ```

### Step 2: SSH Security

1. **Configure SSH**:
   ```bash
   sudo nano /etc/ssh/sshd_config
   ```
   Modify:
   ```
   PermitRootLogin no
   PasswordAuthentication yes  # Change to 'no' after setting up keys
   PubkeyAuthentication yes
   Port 22  # Consider changing to non-standard port
   ```

2. **Setup SSH keys** (from your client machine):
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ssh-copy-id ubuntu@192.168.1.100
   ```

3. **Restart SSH**:
   ```bash
   sudo systemctl restart ssh
   ```

### Step 3: Automatic Updates

1. **Configure automatic security updates**:
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

2. **Configure update settings**:
   ```bash
   sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
   ```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. High CPU Temperature
```bash
# Check temperature
vcgencmd measure_temp

# If >80°C:
# - Ensure active cooling is working
# - Check case ventilation
# - Reduce overclock settings in /boot/firmware/config.txt
```

#### 2. Jellyfin Won't Start
```bash
# Check service status
sudo systemctl status jellyfin

# Check logs
sudo journalctl -u jellyfin -f

# Common fixes:
sudo chown -R jellyfin:jellyfin /media/jellyfin/config/jellyfin
sudo systemctl restart jellyfin
```

#### 3. Hardware Acceleration Not Working
```bash
# Check VA-API devices
ls -l /dev/dri/

# Check permissions
sudo usermod -aG video jellyfin
sudo usermod -aG render jellyfin
sudo systemctl restart jellyfin
```

#### 4. Storage Mount Issues
```bash
# Check mounts
mount | grep jellyfin

# Remount if needed
sudo umount /media/jellyfin
sudo mount -a

# Check filesystem
sudo fsck /dev/sda1
```

#### 5. Network Streaming Issues
```bash
# Check network performance
iperf3 -s  # On Pi
iperf3 -c 192.168.1.100  # From client

# Check Jellyfin network settings
# - Ensure external access is properly configured
# - Check port forwarding if accessing from outside
```

### Performance Troubleshooting

1. **Check system resources**:
   ```bash
   htop
   iotop
   nethogs
   ```

2. **Monitor Jellyfin performance**:
   ```bash
   # Watch Jellyfin logs
   sudo journalctl -u jellyfin -f
   
   # Check transcoding status
   curl http://localhost:8096/Sessions
   ```

3. **Storage performance**:
   ```bash
   # Test disk speed
   sudo hdparm -Tt /dev/sda1
   
   # Test with dd
   dd if=/dev/zero of=/media/jellyfin/test bs=1M count=1000 conv=fdatasync
   rm /media/jellyfin/test
   ```

### Quick Start Commands Reference

```bash
# Check system status
sudo systemctl status jellyfin
htop

# Monitor temperature
vcgencmd measure_temp

# Restart Jellyfin
sudo systemctl restart jellyfin

# Check logs
sudo journalctl -u jellyfin -f

# Update system
sudo apt update && sudo apt upgrade -y

# Run tag organization
cd /media/jellyfin/scripts
./organize_tags.sh
```

---

### Streamlined Workflow:

**Development Machine** (where all the work happens):
1. ✅ **Setup scripts** following the main `README.md` instructions
2. ✅ **Download videos** using your configured download scripts  
3. ✅ **Organize with relative symlinks** using updated `tag_organizer.py`
4. ✅ **Content ready** - NTFS drive contains organized media with portable symlinks

**Raspberry Pi** (clean media server):
1. ✅ **Connect NTFS drive** → Content immediately available
2. ✅ **No script dependencies** → Clean, lightweight server
3. ✅ **Relative symlinks work** → No path adjustments needed
4. ✅ **Ready to serve** → Browse organized content in Jellyfin

**Key Advantages:**
- 🚀 **Separation of concerns** - Development machine handles processing, Pi handles serving
- 🔄 **Portable symlinks** - Content works on any machine, any mount point  
- ⚡ **Optimal performance** - Pi focuses only on media streaming
- 🛠️ **Familiar environment** - Use your existing development setup
- 📦 **Pre-organized content** - Pi receives ready-to-serve media

Your server is ready to serve your media collection with zero script setup on the Pi - all the heavy lifting is done on your development machine with the familiar environment described in `README.md`!
