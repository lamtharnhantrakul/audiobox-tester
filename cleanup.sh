#!/bin/bash

# cleanup.sh - Script to clean up unnecessary files from the audiobox_test directory
# Usage: ./cleanup.sh [--dry-run] [--aggressive]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
DRY_RUN=false
AGGRESSIVE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --aggressive)
            AGGRESSIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--aggressive]"
            echo ""
            echo "Options:"
            echo "  --dry-run     Show what would be deleted without actually deleting"
            echo "  --aggressive  Also remove Docker images and system files"
            echo "  -h, --help    Show this help message"
            echo ""
            echo "Files that will be cleaned up:"
            echo "  - Test result files (*.txt output files)"
            echo "  - System files (.DS_Store)"
            echo "  - Temporary files"
            echo "  - With --aggressive: Docker images and build cache"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to remove files with confirmation
remove_files() {
    local pattern="$1"
    local description="$2"
    local files_found=false

    echo -e "${BLUE}Cleaning up: $description${NC}"

    for file in $pattern; do
        if [[ -e "$file" ]]; then
            files_found=true
            if [[ "$DRY_RUN" == "true" ]]; then
                echo -e "  ${YELLOW}[DRY RUN]${NC} Would remove: $file"
            else
                echo -e "  ${RED}Removing:${NC} $file"
                rm -f "$file"
            fi
        fi
    done

    if [[ "$files_found" == "false" ]]; then
        echo -e "  ${GREEN}✓${NC} No files to clean up"
    fi
    echo
}

# Function to remove directories
remove_directories() {
    local pattern="$1"
    local description="$2"
    local dirs_found=false

    echo -e "${BLUE}Cleaning up: $description${NC}"

    for dir in $pattern; do
        if [[ -d "$dir" ]]; then
            dirs_found=true
            if [[ "$DRY_RUN" == "true" ]]; then
                echo -e "  ${YELLOW}[DRY RUN]${NC} Would remove directory: $dir"
            else
                echo -e "  ${RED}Removing directory:${NC} $dir"
                rm -rf "$dir"
            fi
        fi
    done

    if [[ "$dirs_found" == "false" ]]; then
        echo -e "  ${GREEN}✓${NC} No directories to clean up"
    fi
    echo
}

echo -e "${GREEN}=== AudioBox Test Directory Cleanup ===${NC}"
echo "Directory: $(pwd)"
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}DRY RUN MODE: No files will be actually deleted${NC}"
fi
if [[ "$AGGRESSIVE" == "true" ]]; then
    echo -e "${RED}AGGRESSIVE MODE: Will clean Docker images and system files${NC}"
fi
echo

# Clean up test result files
remove_files "*.txt" "Test result files (*.txt)"

# Clean up system files
remove_files ".DS_Store" "macOS system files"
remove_files "test_files/.DS_Store" "macOS system files in test_files"

# Clean up temporary files and directories
remove_files "temp_*" "Temporary files"
remove_directories "temp_*" "Temporary directories"

# Aggressive cleanup
if [[ "$AGGRESSIVE" == "true" ]]; then
    echo -e "${RED}=== AGGRESSIVE CLEANUP ===${NC}"

    # Clean up Docker images
    if command -v docker >/dev/null 2>&1; then
        echo -e "${BLUE}Cleaning up: Docker images and containers${NC}"
        if [[ "$DRY_RUN" == "true" ]]; then
            echo -e "  ${YELLOW}[DRY RUN]${NC} Would remove Docker image: audiobox-aesthetics"
            echo -e "  ${YELLOW}[DRY RUN]${NC} Would remove Docker image: audiobox-aesthetics-test"
            echo -e "  ${YELLOW}[DRY RUN]${NC} Would prune Docker system"
        else
            # Remove specific Docker images
            docker rmi audiobox-aesthetics 2>/dev/null && echo -e "  ${RED}Removed:${NC} audiobox-aesthetics image" || echo -e "  ${GREEN}✓${NC} audiobox-aesthetics image not found"
            docker rmi audiobox-aesthetics-test 2>/dev/null && echo -e "  ${RED}Removed:${NC} audiobox-aesthetics-test image" || echo -e "  ${GREEN}✓${NC} audiobox-aesthetics-test image not found"

            # Prune Docker system
            echo -e "  ${BLUE}Pruning Docker system...${NC}"
            docker system prune -f >/dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} Docker system pruned" || echo -e "  ${YELLOW}⚠${NC} Docker system prune failed"
        fi
    else
        echo -e "  ${GREEN}✓${NC} Docker not found, skipping Docker cleanup"
    fi
    echo

    # Clean up IDE/editor files
    remove_files ".vscode" "VS Code settings"
    remove_files ".idea" "IntelliJ IDEA settings"
    remove_files "*.swp" "Vim swap files"
    remove_files "*.swo" "Vim swap files"
    remove_files "*~" "Editor backup files"

    # Clean up Python cache
    remove_directories "__pycache__" "Python cache directories"
    remove_files "*.pyc" "Python compiled files"
    remove_files "*.pyo" "Python optimized files"
fi

# Summary
echo -e "${GREEN}=== Cleanup Summary ===${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}DRY RUN completed. No files were actually removed.${NC}"
    echo "Run without --dry-run to perform actual cleanup."
else
    echo -e "${GREEN}Cleanup completed successfully!${NC}"
fi
echo
echo -e "${BLUE}Essential files preserved:${NC}"
echo "  ✓ CLAUDE.md (project documentation)"
echo "  ✓ Dockerfile & Dockerfile.test (container definitions)"
echo "  ✓ README.md (project readme)"
echo "  ✓ audiobox-aesthetics/ (core model code)"
echo "  ✓ process_audio.py (main processing script)"
echo "  ✓ run_*.sh (execution scripts)"
echo "  ✓ test_files/ (test media files)"