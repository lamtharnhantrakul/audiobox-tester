#!/bin/bash

# Script to run audiobox-aesthetics on a single audio file
# Usage: ./run_single_file.sh <path_to_audio_file> [output_filename]

set -e

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker daemon is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <path_to_audio_file> [output_filename]"
    echo "Example: $0 /path/to/song.wav results.txt"
    echo ""
    echo "Supported formats:"
    echo "  Audio: .wav, .flac, .mp3, .m4a, .ogg, .aac, .wma, .aiff, .au"
    echo "  Video: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v (audio will be extracted)"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-single_file_results.txt}"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist."
    exit 1
fi

# Get absolute paths
INPUT_FILE="$(cd "$(dirname "$INPUT_FILE")" && pwd)/$(basename "$INPUT_FILE")"
INPUT_DIR="$(dirname "$INPUT_FILE")"
FILENAME="$(basename "$INPUT_FILE")"
OUTPUT_DIR="$(pwd)"

echo "Building audiobox-aesthetics Docker container..."
docker build -t audiobox-aesthetics .

echo "Processing single file: $INPUT_FILE"
echo "Output will be saved to: $OUTPUT_DIR/$OUTPUT_FILE"

# Create temporary directory with just the single file
TEMP_DIR="$(pwd)/temp_single_$(date +%s)"
mkdir -p "$TEMP_DIR"
cp "$INPUT_FILE" "$TEMP_DIR/"

# Run the container
docker run --rm \
    -v "$TEMP_DIR:/app/input:ro" \
    -v "$OUTPUT_DIR:/app/output" \
    audiobox-aesthetics /app/input "/app/output/$OUTPUT_FILE"

# Clean up
rm -rf "$TEMP_DIR"

echo "Processing complete! Results saved to: $OUTPUT_DIR/$OUTPUT_FILE"