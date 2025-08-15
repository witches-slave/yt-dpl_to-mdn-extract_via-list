#!/bin/bash

# Script to find files with the same file size in a directory
# Usage: ./find_duplicate_sizes.sh [directory] [options]

# Function to display usage
show_usage() {
    echo "Usage: $0 [directory] [options]"
    echo ""
    echo "Options:"
    echo "  -r, --recursive    Search recursively in subdirectories"
    echo "  -h, --help         Show this help message"
    echo "  -s, --sort         Sort by file size (ascending)"
    echo "  -S, --sort-desc    Sort by file size (descending)"
    echo "  -m, --min-size     Minimum file size in bytes (default: 1)"
    echo "  -c, --count        Show count of files per size"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/folder"
    echo "  $0 /path/to/folder -r"
    echo "  $0 . --recursive --sort --count"
    echo "  $0 /videos -r -m 1000000  # Files >= 1MB"
}

# Function to format file size for display
format_size() {
    local size=$1
    if [ $size -ge 1073741824 ]; then
        echo "$(echo "scale=1; $size/1073741824" | bc)GB"
    elif [ $size -ge 1048576 ]; then
        echo "$(echo "scale=1; $size/1048576" | bc)MB"
    elif [ $size -ge 1024 ]; then
        echo "$(echo "scale=1; $size/1024" | bc)KB"
    else
        echo "${size}B"
    fi
}

# Default values
DIRECTORY="."
RECURSIVE=false
SORT_ORDER=""
MIN_SIZE=1
SHOW_COUNT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--recursive)
            RECURSIVE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -s|--sort)
            SORT_ORDER="asc"
            shift
            ;;
        -S|--sort-desc)
            SORT_ORDER="desc"
            shift
            ;;
        -m|--min-size)
            MIN_SIZE="$2"
            shift 2
            ;;
        -c|--count)
            SHOW_COUNT=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            DIRECTORY="$1"
            shift
            ;;
    esac
done

# Check if directory exists
if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory '$DIRECTORY' does not exist."
    exit 1
fi

# Check if bc is available for size formatting
if ! command -v bc &> /dev/null; then
    echo "Warning: 'bc' command not found. File sizes will be shown in bytes only."
    format_size() { echo "$1B"; }
fi

echo "Searching for files with duplicate sizes in: $DIRECTORY"
echo "Recursive: $RECURSIVE"
echo "Minimum size: $(format_size $MIN_SIZE)"
echo "=================================="

# Create temporary file for processing
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Get file sizes and paths using proper find syntax
if [ "$RECURSIVE" = false ]; then
    find "$DIRECTORY" -maxdepth 1 -type f -size +${MIN_SIZE}c -exec stat -c "%s %n" {} \; | sort -n > "$TEMP_FILE"
else
    find "$DIRECTORY" -type f -size +${MIN_SIZE}c -exec stat -c "%s %n" {} \; | sort -n > "$TEMP_FILE"
fi

# Process the results
current_size=""
current_files=()
duplicate_groups=0
total_duplicates=0

while IFS=' ' read -r size filepath; do
    if [ "$size" = "$current_size" ]; then
        # Same size as previous file
        current_files+=("$filepath")
    else
        # Different size - process previous group if it had duplicates
        if [ ${#current_files[@]} -gt 1 ]; then
            ((duplicate_groups++))
            
            echo ""
            echo "Files with size $(format_size $current_size):"
            if [ "$SHOW_COUNT" = true ]; then
                echo "  Count: ${#current_files[@]} files"
            fi
            echo "  ----------------------------------------"
            
            for file in "${current_files[@]}"; do
                echo "  $file"
                ((total_duplicates++))
            done
        fi
        
        # Start new group
        current_size="$size"
        current_files=("$filepath")
    fi
done < "$TEMP_FILE"

# Handle the last group
if [ ${#current_files[@]} -gt 1 ]; then
    ((duplicate_groups++))
    
    echo ""
    echo "Files with size $(format_size $current_size):"
    if [ "$SHOW_COUNT" = true ]; then
        echo "  Count: ${#current_files[@]} files"
    fi
    echo "  ----------------------------------------"
    
    for file in "${current_files[@]}"; do
        echo "  $file"
        ((total_duplicates++))
    done
fi

# Summary
echo ""
echo "=================================="
echo "Summary:"
echo "  Duplicate size groups found: $duplicate_groups"
echo "  Total files with duplicate sizes: $total_duplicates"

if [ $duplicate_groups -eq 0 ]; then
    echo ""
    echo "No files with duplicate sizes found."
    exit 0
fi

echo ""
echo "Note: Files with the same size may not be identical."
echo "Use 'md5sum' or 'sha256sum' to verify actual duplicates."
