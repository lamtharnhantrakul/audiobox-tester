# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker-based audio analysis toolkit that provides two complementary approaches to audio assessment:

1. **Audiobox-Aesthetics**: Meta's model analyzing 4 aesthetic dimensions - Content Enjoyment (CE), Content Usefulness (CU), Production Complexity (PC), and Production Quality (PQ)
2. **SQUIM**: TorchAudio's speech quality assessment providing objective metrics (STOI, PESQ, SI-SDR) and subjective metrics (MOS)

Both systems provide containerized solutions for analyzing audio/video files with automatic format conversion.

## Architecture

### Unified Docker Architecture
- **Single container**: Contains both audiobox-aesthetics and SQUIM dependencies
- **Base image**: Python 3.10-slim with PyTorch, TorchAudio, and audio processing tools
- **Flexible entrypoint**: Default audiobox-aesthetics, override for SQUIM processing

### Audiobox-Aesthetics System
- **Entry point scripts**: `run_audiobox_single_file.sh` and `run_audiobox_directory.sh` - Shell scripts for aesthetic analysis
- **Python wrapper**: `process_audiobox.py` - Custom wrapper with FFmpeg-based fallback for unsupported formats
- **Core model**: Located in `audiobox-aesthetics/` subdirectory (Meta's open-source model with WavLM backbone)

### SQUIM Speech Quality System
- **Entry point scripts**: `run_squim_single_file.sh` and `run_squim_directory.sh` - Shell scripts for speech quality analysis
- **Python wrapper**: `process_squim.py` - SQUIM processor with automatic format conversion and synthetic NMR
- **Core models**: TorchAudio's SQUIM_OBJECTIVE and SQUIM_SUBJECTIVE pretrained models

### Common Features
- **Format compatibility**: Automatic conversion system handles both audio and video files
- **Input/Output**: Processes media files via Docker volume mounts, outputs formatted text results

## Key Commands

### Audiobox-Aesthetics Commands
```bash
# Process single audio/video file for aesthetic metrics
./run_audiobox_single_file.sh /path/to/media.mp4 [output_filename.txt]

# Process all files in test directory for aesthetic analysis
./run_audiobox_directory.sh [output_filename.txt]

# Examples
./run_audiobox_single_file.sh test_files/song.aiff my_aesthetics.txt
./run_audiobox_single_file.sh test_files/video.mp4 video_aesthetics.txt
./run_audiobox_directory.sh aesthetics_results.txt
```

### SQUIM Speech Quality Commands
```bash
# Process single audio/video file for speech quality metrics
./run_squim_single_file.sh /path/to/speech.wav [output_filename.txt]

# Process all files in test directory for speech quality analysis
./run_squim_directory.sh [output_filename.txt]

# Examples
./run_squim_single_file.sh test_files/speech_hanoi.mp3 speech_quality.txt
./run_squim_single_file.sh test_files/interview.mp4 interview_quality.txt
./run_squim_directory.sh squim_results.txt
```

### Maintenance Commands
```bash
# Clean up generated test files and artifacts
./cleanup.sh                    # Standard cleanup
./cleanup.sh --dry-run          # Preview cleanup
./cleanup.sh --aggressive       # Include Docker images
```

### Manual Docker Usage
```bash
# Build unified container (supports both audiobox-aesthetics and SQUIM)
docker build -t audiobox-squim .

# Audiobox-Aesthetics (default entrypoint)
docker run --rm \
  -v "/path/to/media:/app/input:ro" \
  -v "$(pwd):/app/output" \
  audiobox-squim /app/input "/app/output/aesthetics_results.txt"

# SQUIM Speech Quality (override entrypoint)
docker run --rm \
  --entrypoint python \
  -v "/path/to/media:/app/input:ro" \
  -v "$(pwd):/app/output" \
  audiobox-squim /app/process_squim.py /app/input "/app/output/squim_results.txt"

# Test containers (legacy)
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
3. **process_audiobox.py** orchestrates processing with automatic format handling:
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

### Common Requirements
- Docker Desktop (required to be running)
- Python 3.10 (container)
- PyTorch 2.2+, torchaudio
- FFmpeg (handles all audio/video format conversion)
- tqdm (for progress display)

### Audiobox-Aesthetics Specific
- soundfile (for audio processing)
- audiobox-aesthetics package (Meta's model)

### SQUIM Specific
- TorchAudio 2.6.0+ (includes SQUIM models)
- Pre-trained SQUIM models (auto-downloaded from TorchAudio)

## Model Architecture

### Audiobox-Aesthetics Model
- **Backbone**: WavLM (Microsoft's audio foundation model)
- **Multi-output head**: Separate prediction layers for CE, CU, PC, PQ metrics
- **Processing**: Audio resampled to 16kHz mono, analyzed in 10-second overlapping windows
- **Checkpoint**: Auto-downloads from HuggingFace (`facebook/audiobox-aesthetics`) on first run
- **Device support**: CUDA, MPS (Apple Silicon), CPU fallback

### SQUIM Speech Quality Models
- **Objective Model**: Predicts STOI, PESQ, and SI-SDR metrics without reference audio
- **Subjective Model**: Predicts MOS (Mean Opinion Score) for overall quality assessment
- **Processing**: Audio resampled to 16kHz mono, minimum 0.5-second duration required
- **Checkpoints**: Pre-trained TorchAudio models (`SQUIM_OBJECTIVE`, `SQUIM_SUBJECTIVE`)
- **Device support**: CUDA, MPS (Apple Silicon), CPU fallback

#### SQUIM Metrics Explained
- **STOI** (0-1): Speech Intelligibility - higher values indicate better intelligibility
- **PESQ** (1-4.5): Perceptual Evaluation of Speech Quality - higher values indicate better quality
- **SI-SDR** (dB): Scale-Invariant Signal-to-Distortion Ratio - higher values indicate less distortion
- **MOS** (1-5): Mean Opinion Score - subjective quality rating, higher values indicate better perceived quality

#### SQUIM Implementation Notes
- **Non-Matching Reference (NMR)**: SQUIM_SUBJECTIVE requires a reference audio for MOS calculation
- **Synthetic NMR**: Uses generated multi-frequency tone (800Hz, 1200Hz, 2400Hz) as default reference
- **MOS Interpretation**: MOS scores may appear lower due to synthetic reference; focus on relative comparisons
- **Reference-Free Objective Metrics**: STOI, PESQ, and SI-SDR are reference-free and provide reliable absolute scores

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

## Test Infrastructure

### Test Files Directory
The `test_files/` directory contains diverse media samples for validation:
- **Audio formats**: .aiff, .m4a, .mp3 (Thai music, speech samples, reference tracks)
- **Video formats**: .MP4, .mp4 (drone footage, music videos)
- **Total**: 10+ test files, 365MB+ of test media
- **Purpose**: Format compatibility testing and processing validation

### Available Test Files
Notable test files include:
- `speech_hanoi.mp3` - Speech sample for SQUIM testing
- Various music and video files for audiobox-aesthetics testing
- Mixed format samples to validate FFmpeg conversion pipeline

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

### Audiobox-Aesthetics Results
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

### SQUIM Speech Quality Results
```
Speech Quality Assessment Results (SQUIM)
==================================================

File: example.wav
Path: /app/input/example.wav
Speech Quality Metrics:
  STOI (Speech Intelligibility): 0.892
  PESQ (Perceptual Quality): 3.247
  SI-SDR (Signal Distortion): 12.845 dB
  MOS (Mean Opinion Score): 4.132

------------------------------

Summary Statistics:
====================
Total files processed: 5
Average STOI: 0.874
Average PESQ: 3.182
Average SI-SDR: 11.923 dB
Average MOS: 4.067
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