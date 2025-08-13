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
   sudo mkdir -p /media/jellyfin/videos
   sudo mkdir -p /media/jellyfin/config
   sudo mkdir -p /media/jellyfin/cache
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

# Your existing source folders should already be here (sourcefolder, sourcefolder2, etc.)
# No need to create additional directories - tag_organizer.py will create the tags/ structure

# Only create transcoding directory (optional - only if SD space is limited)
mkdir -p transcodes
```

**If starting with a clean drive:**
```bash
# Create basic structure (adjust folder names to match your media collection)
mkdir -p /media/jellyfin/sourcefolder
mkdir -p /media/jellyfin/sourcefolder2
mkdir -p /media/jellyfin/movies

# Create transcoding directory (optional)
mkdir -p /media/jellyfin/transcodes

# Note: tags/ directory will be created automatically by tag_organizer.py
```

**Example final structure with existing media:**
```
SD Card (fast):
├── /var/lib/jellyfin/          # Jellyfin config & database (keep here!)
├── /var/cache/jellyfin/        # Jellyfin cache (keep here for speed)
└── /var/log/jellyfin/          # Jellyfin logs (keep here)

External NTFS Drive (large storage):
/media/jellyfin/
├── sourcefolder/               # Your existing media folders
├── sourcefolder2/              # More existing media folders
├── sourcefolder3/              # More existing media folders
├── movies/                     # Your existing movies (if any)
├── tags/                       # Created by tag_organizer.py with symlinks
│   ├── tag [TagName]/          # Symlinks to videos with this tag
│   ├── model [ModelName]/      # Symlinks to videos with this model
│   ├── tag no tag/             # Videos without tags
│   └── source [foldername]/    # All videos from each source folder
└── transcodes/                 # Temporary transcoding files (optional)
```

**🚀 Performance Rationale:**
- **SD Card (fast random access)**: Jellyfin database, config, cache for instant UI response
- **External NTFS Drive (large capacity)**: Media files only - sequential reads are fine
- **NTFS compatibility**: Works perfectly with Jellyfin, maintains Windows compatibility
- **Network streaming**: NTFS read performance is excellent for video streaming
- **Symlinks organization**: tag_organizer.py creates organized symlinks without moving files

---

## Jellyfin Installation

### Step 1: Install Jellyfin Repository

1. **Add Microsoft package repository** (required for .NET):
   ```bash
   wget https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
   sudo dpkg -i packages-microsoft-prod.deb
   sudo apt update
   ```

2. **Add Jellyfin repository**:
   ```bash
   curl -fsSL https://repo.jellyfin.org/jellyfin_team.gpg.key | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/jellyfin.gpg
   echo "deb [arch=$( dpkg --print-architecture )] https://repo.jellyfin.org/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/jellyfin.list
   ```

3. **Update package list**:
   ```bash
   sudo apt update
   ```

### Step 2: Install Jellyfin and Dependencies

1. **Install Jellyfin**:
   ```bash
   sudo apt install -y jellyfin
   ```

2. **Install additional multimedia packages**:
   ```bash
   # Hardware acceleration and codec support
   sudo apt install -y \
     vainfo \
     intel-media-va-driver-non-free \
     mesa-va-drivers \
     ffmpeg \
     libavcodec-extra \
     intel-opencl-icd
   ```

3. **Add jellyfin user to video group** (for hardware acceleration):
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
   # Keep Jellyfin config/database on fast SD card (default location is fine)
   # Only create a custom transcode directory on external drive if you have limited SD space
   
   # Create transcode directory on external drive (optional - see note below)
   sudo mkdir -p /media/jellyfin/transcodes
   sudo chown -R jellyfin:jellyfin /media/jellyfin/transcodes
   ```

   **Performance Note**: 
   - **Keep on SD card**: Configuration, database, cache (for fastest access)
   - **Move to external**: Only transcoding temp files (if SD card space is limited)
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
   # Custom transcode directory (optional - only if SD space is limited)
   Environment="JELLYFIN_TRANSCODE_DIR=/media/jellyfin/transcodes"
   # Performance optimizations
   Environment="JELLYFIN_FFMPEG_ARGS=-threads 4 -thread_queue_size 512"
   ```

   **Alternative for limited SD space** - move cache to external drive:
   ```bash
   # ONLY if your SD card is running low on space
   sudo systemctl stop jellyfin
   sudo mv /var/cache/jellyfin /media/jellyfin/cache/jellyfin
   sudo ln -s /media/jellyfin/cache/jellyfin /var/cache/jellyfin
   sudo chown -R jellyfin:jellyfin /media/jellyfin/cache/jellyfin
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
   - Add media libraries pointing to `/media/jellyfin/videos/`
   - Configure hardware acceleration (Settings → Playback → Hardware acceleration: Video Acceleration API (VAAPI))
   - Set transcode directory: `/media/jellyfin/transcodes`

---

## Integration with Tag Organization System

### Step 1: Install Dependencies for Tag Organizer

```bash
# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv

# Install Chrome and dependencies (for tag_organizer.py)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=arm64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# System dependencies for Selenium
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

### Step 2: Setup Tag Organization Environment

1. **Create organization directory**:
   ```bash
   mkdir -p /media/jellyfin/scripts
   cd /media/jellyfin/scripts
   ```

2. **Create Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python packages**:
   ```bash
   pip install --upgrade pip
   pip install "blinker<1.8" && \
   pip install selenium-wire && \
   pip install webdriver-manager && \
   pip install requests && \
   pip install setuptools
   ```

4. **Copy tag organization scripts**:
   ```bash
   # Copy from your development machine (adjust paths as needed)
   scp username@your-dev-machine:/path/to/scripts/tag_organizer.py .
   scp username@your-dev-machine:/path/to/scripts/list_tag.txt .
   chmod +x *.py
   ```

### Step 3: Configure Tag Organizer for Pi

1. **Create organization script**:
   ```bash
   nano organize_tags.sh
   ```
   Add:
   ```bash
   #!/bin/bash
   cd /media/jellyfin/scripts
   source venv/bin/activate
   
   echo "Starting tag organization process..."
   echo "This will create symlinks in /media/jellyfin/tags/ pointing to your source folders"
   
   # Run tag organizer (it will prompt for source folder selection)
   python3 tag_organizer.py
   
   echo "Updating Jellyfin library..."
   curl -X POST "http://localhost:8096/Library/Refresh" \
        -H "X-Emby-Authorization: MediaBrowser Token=YOUR_API_TOKEN"
   ```

2. **Make script executable**:
   ```bash
   chmod +x organize_tags.sh
   ```

### Step 4: Setup Automated Library Refresh

1. **Create Jellyfin API token**:
   - Go to Jellyfin Dashboard → API Keys
   - Create new API key
   - Note the token for use in scripts

2. **Update the organize_tags.sh script** with your API token:
   ```bash
   nano organize_tags.sh
   # Replace YOUR_API_TOKEN with your actual token
   ```

### Step 5: Running Tag Organization

**Flexible Deployment**: The tag_organizer.py script can be run either on the Pi or on your development machine, as long as the symlinks stay within the same drive/filesystem.

**Option A: Run on Development Machine** (Recommended for convenience):
```bash
# On your development machine where you have the download scripts
cd /path/to/your/scripts
source venv/bin/activate

# Mount or access the NTFS drive (e.g., via network share, direct USB connection, etc.)
# Make sure tag_organizer.py points to the correct paths on the drive

python3 tag_organizer.py
# When prompted for source folder, select the path to your media on the NTFS drive
# The script will create symlinks that stay within the same filesystem
```

**Option B: Run on Pi** (Original approach):
```bash
cd /media/jellyfin/scripts
./organize_tags.sh
```

**Key Points for Cross-Machine Symlink Creation:**
- ✅ **Symlinks work**: As long as source and target are on the same filesystem
- ✅ **Relative paths**: The script can use relative paths that work on both systems
- ✅ **NTFS compatibility**: NTFS supports symlinks when created properly
- ✅ **No network crossing**: All symlinks stay within the NTFS drive

**Example workflow:**
1. **Download videos** on your development machine
2. **Save directly to NTFS drive** (mounted via USB or network)
3. **Run tag_organizer.py** on development machine pointing to NTFS drive
4. **Transfer/connect NTFS drive** to Pi
5. **Symlinks work immediately** on Pi since they're relative to the drive

The script will:
- Prompt you to select your media source folder (e.g., `E:\sourcefolder` on Windows or `/mnt/usb/sourcefolder` on Linux)
- Read `list_tag.txt` to get tag/model URLs
- Crawl each tag/model page to find associated videos
- Create organized symlinks in the `tags/` folder on the same drive
- Structure: `tag [TagName]/`, `model [ModelName]/`, `tag no tag/`, `source [foldername]/`

### Step 6: Jellyfin Library Configuration

1. **Add media libraries in Jellyfin**:
   - **Source Media**: Point to `/media/jellyfin/sourcefolder`, `/media/jellyfin/sourcefolder2`, etc.
   - **Organized Tags**: Point to `/media/jellyfin/tags/` for browsing by tags/models
   - **Movies**: Point to `/media/jellyfin/movies/` if you have movies

2. **Library settings**:
   - Enable "Real-time monitoring" for automatic updates
   - Set content type appropriately for each library
   - Configure metadata providers as needed

### Workflow Summary

**Your flexible workflow options:**

**Option A - Development Machine Organization (Most Convenient):**
1. **Download videos** on your development machine using the download scripts
2. **Save directly to NTFS drive** (connected via USB or network)
3. **Run tag_organizer.py** on development machine pointing to the NTFS drive
4. **Connect/transfer NTFS drive** to Pi
5. **Jellyfin automatically detects** organized content via existing symlinks

**Option B - Pi Organization (Original approach):**
1. **Download videos** on your development machine using the download scripts
2. **Transfer media** to the Pi's NTFS drive (via network copy, direct connection, etc.)
3. **Run tag organization** on the Pi: `./organize_tags.sh`
4. **Jellyfin automatically detects** new organized content via symlinks

**Benefits of both approaches:**
- ✅ **Symlinks work properly** (stay within same filesystem)
- ✅ **No duplicate storage** (videos stay in source folders)
- ✅ **Organized browsing** (by tags, models, etc.)
- ✅ **NTFS compatibility** (symlinks work on Windows and Linux)
- ✅ **Fast access** (Jellyfin config on SD card, media on NTFS drive)
- ✅ **Flexible deployment** (organize wherever convenient)

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

1. **Create tmpfs for transcoding** (uses RAM for faster transcoding):
   ```bash
   sudo nano /etc/fstab
   ```
   Add:
   ```
   tmpfs /media/jellyfin/transcodes tmpfs defaults,noatime,size=2G 0 0
   ```

2. **Mount tmpfs**:
   ```bash
   sudo mount -a
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

## Conclusion

Your Raspberry Pi 5 is now configured as a powerful Jellyfin media server with:

✅ **Ubuntu Server 24.04 LTS** - Stable, long-term support OS  
✅ **Hardware-accelerated transcoding** - Smooth playback on all devices  
✅ **External NTFS storage** - Your existing media collection preserved  
✅ **Tag organization system** - Automated symlink organization via tag_organizer.py  
✅ **Security hardening** - Protected against common threats  
✅ **Performance optimized** - Configured for smooth media streaming  
✅ **Remote access capable** - Access your media from anywhere  

### Your Workflow Options:
**Option A (Most Convenient):**
1. **Download videos** on your development machine
2. **Save directly to NTFS drive** (USB/network connected)
3. **Run tag_organizer.py** on development machine
4. **Connect NTFS drive** to Pi → **Ready to serve!**

**Option B (Pi-based):**
1. **Download videos** on your development machine
2. **Transfer media files** to Pi's NTFS drive
3. **Run tag organization** on Pi: `./organize_tags.sh`
4. **Browse organized content** in Jellyfin

Your server is ready to serve your media collection with automatic organization through symlinks - created wherever it's most convenient for you!

---

**Setup complete!** Your Raspberry Pi 5 Jellyfin server is ready to serve your media collection across your network.
