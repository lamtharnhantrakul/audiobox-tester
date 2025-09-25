# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker-based wrapper for Meta's audiobox-aesthetics model that analyzes audio/video files for aesthetic metrics. The project provides a containerized solution to run audio analysis on media files with 4 aesthetic dimensions: Content Enjoyment (CE), Content Usefulness (CU), Production Complexity (PC), and Production Quality (PQ).

## Architecture

- **Entry point scripts**: `run_single_file.sh` and `run_test_files.sh` - Shell scripts that build and run the Docker container
- **Docker container**: Contains the audiobox-aesthetics Python package and dependencies
- **Python wrapper**: `process_audio.py` - Custom wrapper with FFmpeg-based fallback for unsupported formats
- **Core model**: Located in `audiobox-aesthetics/` subdirectory (Meta's open-source model with WavLM backbone)
- **Format compatibility**: Automatic conversion system handles both audio and video files
- **Input/Output**: Processes media files via Docker volume mounts, outputs formatted text results

## Key Commands

### Primary Usage
```bash
# Process single audio/video file
./run_single_file.sh /path/to/media.mp4 [output_filename.txt]

# Process all files in test directory
./run_test_files.sh [output_filename.txt]

# Examples
./run_single_file.sh test_files/song.aiff my_results.txt
./run_single_file.sh test_files/video.mp4 video_analysis.txt
./run_test_files.sh test_results.txt

# Clean up generated test files and artifacts
./cleanup.sh                    # Standard cleanup
./cleanup.sh --dry-run          # Preview cleanup
./cleanup.sh --aggressive       # Include Docker images
```

### Manual Docker Usage
```bash
# Build container
docker build -t audiobox-aesthetics .

# Process directory manually
docker run --rm \
  -v "/path/to/media:/app/input:ro" \
  -v "$(pwd):/app/output" \
  audiobox-aesthetics /app/input "/app/output/results.txt"

# Build test container
docker build -f Dockerfile.test -t audiobox-aesthetics-test .
```

### Direct Model CLI (within container)
```bash
# JSONL batch processing
audio-aes input.jsonl --batch-size 100 > output.jsonl

# With SLURM for large-scale processing
audio-aes input.jsonl --batch-size 100 --remote --array 5 --job-dir $HOME/slurm_logs/ --chunk 1000 > output.jsonl
```

## Data Flow Architecture

1. **Shell script** creates temporary directories and handles file path resolution
2. **Docker container** mounts input (read-only) and output directories
3. **process_audio.py** orchestrates processing with automatic format handling:
   - Displays real-time progress bar with file count and ETA
   - Scans for supported media files
   - **Video files**: Extracts audio using FFmpeg with progress notifications
   - **Unsupported audio formats**: Converts to WAV using FFmpeg fallback
   - Calls audiobox-aesthetics model via `initialize_predictor()`
   - Shows status updates with emojis (🎥 video extraction, 🔄 format conversion, ✓ success, ✗ errors)
4. **Model inference** processes audio in 10-second windows with weighted aggregation
5. **Output generation** creates formatted text file with metrics
6. **Cleanup** removes temporary files automatically

## Supported Media Formats

**Audio**: .wav, .flac, .mp3, .m4a, .ogg, .aac, .wma, .aiff, .au (with automatic FFmpeg conversion fallback)
**Video**: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v (audio extracted automatically using FFmpeg)

## Core Dependencies

- Docker Desktop (required to be running)
- Python 3.10 (container)
- PyTorch 2.2+, torchaudio
- FFmpeg (handles all audio/video format conversion)
- soundfile, tqdm (for audio processing and progress display)
- audiobox-aesthetics package (Meta's model)

## Model Architecture

- **Backbone**: WavLM (Microsoft's audio foundation model)
- **Multi-output head**: Separate prediction layers for CE, CU, PC, PQ metrics
- **Processing**: Audio resampled to 16kHz mono, analyzed in 10-second overlapping windows
- **Checkpoint**: Auto-downloads from HuggingFace (`facebook/audiobox-aesthetics`) on first run
- **Device support**: CUDA, MPS (Apple Silicon), CPU fallback

## Format Conversion System

The system includes robust automatic format conversion:

### Video Processing
- **FFmpeg-based extraction**: Direct FFmpeg audio extraction (no moviepy dependency)
- **Automatic fallback**: Any video format supported by FFmpeg works automatically
- **Optimized output**: Converts to 16kHz mono WAV (model requirements)

### Audio Processing
- **Primary loading**: Uses torchaudio for direct supported formats
- **Conversion fallback**: Automatically converts unsupported formats (M4A, etc.) via FFmpeg
- **Error recovery**: Detects format errors and retries with converted files
- **Progress tracking**: Real-time progress bar shows file processing status and ETA

## Development Notes

- This is primarily a Docker containerization project, not a Python development environment
- All processing should go through Docker containers for consistency
- Core model is in `audiobox-aesthetics/` subdirectory (standard Python package with pyproject.toml)
- No traditional unit tests - validation through Docker builds and sample file processing
- Container requires significant memory allocation for model inference
- Test files in `test_files/` include various audio/video formats for validation

## Project Maintenance

```bash
# Regular cleanup of test artifacts
./cleanup.sh --dry-run      # Preview cleanup
./cleanup.sh               # Clean test files and system artifacts

# Deep cleanup including Docker images
./cleanup.sh --aggressive --dry-run  # Preview aggressive cleanup
./cleanup.sh --aggressive           # Full cleanup including Docker cache
```

## Output Format

Results are saved as formatted text files:
```
Audio File Aesthetics Metrics
==================================================

File: example.wav
Path: /app/input/example.wav
Metrics:
  Content Enjoyment (CE): 5.146
  Content Usefulness (CU): 5.779
  Production Complexity (PC): 2.148
  Production Quality (PQ): 7.220

------------------------------
```

## Progress Display

The system provides real-time feedback during processing:
- **Progress bar**: Shows percentage complete, files processed, and estimated time remaining
- **Status messages**: Emoji-coded updates for different operations:
  - 🎥 Video audio extraction
  - 🔄 Audio format conversion
  - ✓ Successful processing
  - ✗ Processing errors

Example output:
```
Processing: filename.mp4: 44%|████▍ | 4/9 [00:16<00:19, 3.88s/file]
🎥 Extracting audio from video: filename.mp4
✓ Successfully extracted audio from filename.mp4
```

## Troubleshooting

- **Memory requirements**: Model requires substantial RAM - ensure Docker has adequate memory allocation
- **Docker daemon**: Ensure Docker Desktop is running before executing scripts
- **Format compatibility**: All common audio/video formats supported via automatic FFmpeg conversion
- **Permission issues**: Make scripts executable with `chmod +x run_*.sh cleanup.sh`