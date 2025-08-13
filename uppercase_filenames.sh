#!/bin/bash

# Script to convert all filenames in a folder to uppercase (preserving file extensions)
# Usage: ./uppercase_filenames.sh <relative_folder_path>

set -e  # Exit on any error

# Function to display usage
show_usage() {
    echo "Usage: $0 <relative_folder_path>"
    echo ""
    echo "This script converts all filenames in the specified folder to uppercase"
    echo "while preserving the file extensions in their original case."
    echo ""
    echo "Examples:"
    echo "  $0 ./videos"
    echo "  $0 downloads"
    echo "  $0 ../media"
    echo ""
    echo "Note: Only the filename (without extension) will be converted to uppercase."
    echo "      File extensions will remain unchanged."
}

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if argument is provided
if [ $# -ne 1 ]; then
    echo "Error: Please provide exactly one argument (relative folder path)"
    echo ""
    show_usage
    exit 1
fi

FOLDER_PATH="$1"

# Check if folder exists
if [ ! -d "$FOLDER_PATH" ]; then
    echo "Error: Folder '$FOLDER_PATH' does not exist!"
    exit 1
fi

# Convert to absolute path for better logging
ABSOLUTE_PATH=$(realpath "$FOLDER_PATH")

log_message "Starting filename conversion to uppercase in: $ABSOLUTE_PATH"

# Counter for renamed files
RENAMED_COUNT=0
SKIPPED_COUNT=0

# Process all files in the directory (non-recursive)
while IFS= read -r -d '' file; do
    # Get the directory and filename
    dir_path=$(dirname "$file")
    original_filename=$(basename "$file")
    
    # Skip if it's a directory
    if [ -d "$file" ]; then
        continue
    fi
    
    # Extract filename without extension and the extension
    filename_no_ext="${original_filename%.*}"
    extension="${original_filename##*.}"
    
    # If there's no extension (no dot in filename), treat whole name as filename
    if [ "$filename_no_ext" = "$extension" ]; then
        filename_no_ext="$original_filename"
        extension=""
    fi
    
    # Convert filename to uppercase
    uppercase_filename=$(echo "$filename_no_ext" | tr '[:lower:]' '[:upper:]')
    
    # Construct new filename
    if [ -n "$extension" ]; then
        new_filename="${uppercase_filename}.${extension}"
    else
        new_filename="$uppercase_filename"
    fi
    
    # Check if renaming is needed
    if [ "$original_filename" = "$new_filename" ]; then
        log_message "  Skipped (already uppercase): $original_filename"
        ((SKIPPED_COUNT++))
        continue
    fi
    
    # Construct full paths
    old_path="$dir_path/$original_filename"
    new_path="$dir_path/$new_filename"
    
    # Check if target filename already exists
    if [ -e "$new_path" ]; then
        log_message "  ⚠️  Warning: Target file already exists, skipping: $original_filename -> $new_filename"
        ((SKIPPED_COUNT++))
        continue
    fi
    
    # Rename the file
    if mv "$old_path" "$new_path"; then
        log_message "  ✅ Renamed: $original_filename -> $new_filename"
        ((RENAMED_COUNT++))
    else
        log_message "  ❌ Failed to rename: $original_filename"
        ((SKIPPED_COUNT++))
    fi
    
done < <(find "$FOLDER_PATH" -maxdepth 1 -type f -print0)

# Summary
log_message ""
log_message "📊 Summary:"
log_message "   • Files renamed: $RENAMED_COUNT"
log_message "   • Files skipped: $SKIPPED_COUNT"
log_message "   • Total files processed: $((RENAMED_COUNT + SKIPPED_COUNT))"

if [ $RENAMED_COUNT -gt 0 ]; then
    log_message "✅ Filename conversion completed successfully!"
else
    log_message "ℹ️  No files needed renaming."
fi
