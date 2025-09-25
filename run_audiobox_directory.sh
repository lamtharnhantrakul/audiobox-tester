#!/bin/bash

# Script to run audiobox-aesthetics on all audio files in the test_files directory
# This is a convenience wrapper around run_audiobox.sh for testing purposes

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/test_files"
OUTPUT_FILE="${1:-test_results.txt}"

echo "Running audiobox-aesthetics on test directory..."
echo "Test directory: $TEST_DIR"
echo "Output file: $OUTPUT_FILE"

# Check if test directory exists
if [ ! -d "$TEST_DIR" ]; then
    echo "Error: Test directory '$TEST_DIR' does not exist."
    exit 1
fi

# Check if test directory has audio/video files
if ! find "$TEST_DIR" -type f \( -iname "*.wav" -o -iname "*.flac" -o -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.aac" -o -iname "*.wma" -o -iname "*.aiff" -o -iname "*.au" -o -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" -o -iname "*.mkv" -o -iname "*.wmv" -o -iname "*.flv" -o -iname "*.webm" -o -iname "*.m4v" \) | grep -q .; then
    echo "Error: No supported audio/video files found in '$TEST_DIR'."
    echo "Supported formats:"
    echo "  Audio: .wav, .flac, .mp3, .m4a, .ogg, .aac, .wma, .aiff, .au"
    echo "  Video: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker daemon is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Convert to absolute paths
TEST_DIR="$(cd "$TEST_DIR" && pwd)"
OUTPUT_DIR="$(pwd)"

echo "Building audiobox-aesthetics Docker container..."
docker build -t audiobox-aesthetics .

echo "Running audiobox-aesthetics on media files in: $TEST_DIR"
echo "Output will be saved to: $OUTPUT_DIR/$OUTPUT_FILE"

# Run the container with volume mounts
docker run --rm \
    -v "$TEST_DIR:/app/input:ro" \
    -v "$OUTPUT_DIR:/app/output" \
    audiobox-aesthetics /app/input "/app/output/$OUTPUT_FILE"

echo "Processing complete! Results saved to: $OUTPUT_DIR/$OUTPUT_FILE"

echo "Test run complete! Check $OUTPUT_FILE for results."