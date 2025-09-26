#!/bin/bash

# Script to run UTMOSv2 speech quality assessment on all audio files in the test_files directory
# Usage: ./run_utmosv2_directory.sh [output_filename] [--rebuild]

set -e

# Parse arguments for rebuild flag
REBUILD=false
ARGS=()
for arg in "$@"; do
    case $arg in
        --rebuild)
            REBUILD=true
            ;;
        *)
            ARGS+=("$arg")
            ;;
    esac
done

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/test_files"
OUTPUT_FILE="${ARGS[0]:-utmosv2_test_results.txt}"

echo "Running UTMOSv2 speech quality assessment on test directory..."
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

# Check if container exists and decide whether to build
CONTAINER_NAME="audiobox-squim"
BUILD_REQUIRED=false

if $REBUILD; then
    echo "🔄 Force rebuild requested - rebuilding Docker container..."
    BUILD_REQUIRED=true
elif ! docker image inspect $CONTAINER_NAME >/dev/null 2>&1; then
    echo "🏗️  Docker image not found - building unified container with UTMOSv2..."
    BUILD_REQUIRED=true
else
    echo "✅ Using existing Docker image '$CONTAINER_NAME' (use --rebuild to force rebuild)"
fi

if $BUILD_REQUIRED; then
    docker build -t $CONTAINER_NAME .
fi

echo "Running UTMOSv2 assessment on media files in: $TEST_DIR"
echo "Output will be saved to: $OUTPUT_DIR/$OUTPUT_FILE"

# Run the container with UTMOSv2 entrypoint
docker run --rm \
    --entrypoint python \
    -v "$TEST_DIR:/app/input:ro" \
    -v "$OUTPUT_DIR:/app/output" \
    $CONTAINER_NAME /app/process_utmosv2.py /app/input "/app/output/$OUTPUT_FILE"

echo "Processing complete! Results saved to: $OUTPUT_DIR/$OUTPUT_FILE"

echo "UTMOSv2 assessment complete! Check $OUTPUT_FILE for speech naturalness metrics."