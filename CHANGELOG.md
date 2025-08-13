# Changelog - Video Download and Organization System

## Latest Changes - URL-Title Tracking and Duplicate Handling

### Issue Resolved
Fixed problem where videos with duplicate titles but different URLs were being skipped during download, resulting in fewer downloads than expected (329 vs 340).

### Key Changes

#### 1. Enhanced sitemap_video_parser.py
- **NEW FORMAT**: Now extracts both URLs and titles from video listing pages
- **DUPLICATE HANDLING**: Automatically detects duplicate titles and uses URL-based titles instead
- **FILENAME FORMATTING**: Uses spaces instead of dashes in filenames (user preference)
- **OUTPUT FORMAT**: Creates `list_video.txt` with pipe-separated format: `URL|TITLE`
- **FALLBACK**: If title extraction fails, derives title from URL path

#### 2. Enhanced download.py  
- **URL-BASED TRACKING**: Now tracks downloads by URL hash instead of just title
- **DUPLICATE PREVENTION**: Uses URL hash in filenames to ensure uniqueness
- **BACKWARDS COMPATIBLE**: Supports both new format (URL|TITLE) and legacy format (URL only)
- **IMPROVED DETECTION**: `check_file_exists_by_url()` prevents re-downloading same URL
- **UNIQUE FILENAMES**: Format: "Title [hash8].mp4" for uniqueness

#### 3. Enhanced unified_video_organizer.py
- **DUAL FORMAT SUPPORT**: Handles both URL|TITLE and legacy URL-only formats
- **TITLE PREFERENCE**: Uses predefined titles when available, falls back to extracted titles
- **BETTER MATCHING**: Improved video file matching using predefined titles

### New File Format
```
# Old format (list_video.txt):
https://example.com/video1
https://example.com/video2

# New format (list_video.txt):
https://example.com/video1|Amazing Video Title
https://example.com/video2|Another Great Video
https://example.com/video3|Unique Title Instead Of Duplicate|d4f8b9a2
```

### Benefits
1. **NO MORE SKIPPED VIDEOS**: Every unique URL gets processed, even with duplicate titles
2. **UNIQUE IDENTIFICATION**: Each video file has a unique identifier based on its URL
3. **BETTER ORGANIZATION**: Predefined titles improve video matching and organization
4. **BACKWARDS COMPATIBLE**: Existing workflows continue to work
5. **READABLE FILENAMES**: Still human-readable with short hash for uniqueness

### Usage
1. Run `python3 sitemap_video_parser.py` to generate new format list_video.txt
2. Run `python3 download.py` as usual (now tracks by URL)
3. Run `python3 unified_video_organizer.py` as usual (uses predefined titles)

### Technical Details
- URL hashes use MD5 first 8 characters for brevity
- Duplicate title detection happens during sitemap parsing
- Filename cleaning removes invalid characters and uses spaces
- Both scripts validate list_video.txt format and provide helpful error messages
