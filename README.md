# Audiobox Aesthetics Docker Setup

This setup provides a Docker container for testing audiobox-aesthetics on your audio and video files. It extends the original Meta audiobox-aesthetics model with Docker containerization, automatic format conversion, and support for video file processing.

## Prerequisites

1. Docker Desktop must be installed and running
2. Audio or video files in a directory (supports audio: .wav, .flac, .mp3, .m4a, .ogg, .aac, .wma, .aiff, .au; video: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v)

## Quick Start

1. **Start Docker Desktop** (make sure it's running)

2. **Run the analysis** on your audio or video files:
   ```bash
   ./run_single_file.sh /path/to/media/file.mp4 [output_filename.txt]
   ./run_test_files.sh [output_filename.txt]
   ```

   Examples:
   ```bash
   ./run_single_file.sh ~/Music/song.mp3 results.txt
   ./run_single_file.sh ~/Videos/movie.mp4 video_analysis.txt
   ./run_test_files.sh batch_results.txt
   ```

3. **View results** in the generated text file

## What the Analysis Provides

The tool analyzes audio content from both audio and video files and provides 4 aesthetic metrics:

- **Content Enjoyment (CE)**: How enjoyable the content is
- **Content Usefulness (CU)**: How useful the content is
- **Production Complexity (PC)**: How complex the production is
- **Production Quality (PQ)**: How high the production quality is

Each metric is scored on a scale (typically 1-10).

## Output Format

The results are saved to a text file with the following format:

```
Audio File Aesthetics Metrics
==================================================

File: song1.wav
Path: /app/input/song1.wav
Metrics:
  Content Enjoyment (CE): 5.146
  Content Usefulness (CU): 5.779
  Production Complexity (PC): 2.148
  Production Quality (PQ): 7.220

------------------------------

File: song2.flac
...
```

## Manual Docker Commands

If you prefer to run Docker commands manually:

1. **Build the container:**
   ```bash
   docker build -t audiobox-aesthetics .
   ```

2. **Run the analysis:**
   ```bash
   docker run --rm \
     -v "/path/to/your/audio:/app/input:ro" \
     -v "$(pwd):/app/output" \
     audiobox-aesthetics /app/input "/app/output/results.txt"
   ```

## Troubleshooting

- **Docker daemon not running**: Start Docker Desktop
- **Permission denied**: Make sure the script is executable with `chmod +x run_audiobox.sh`
- **No media files found**: Check that your directory contains supported audio or video formats
- **Out of memory**: The model requires significant memory; ensure Docker has enough RAM allocated

## Key Features

- **Docker containerization**: Eliminates dependency management and ensures consistent execution
- **Video file support**: Automatically extracts audio from video files using FFmpeg
- **Format conversion**: Handles unsupported audio formats with automatic FFmpeg fallback
- **Progress tracking**: Real-time progress bars with file count and ETA
- **Batch processing**: Process entire directories or single files
- **Clean output formatting**: Structured text results with clear metrics

## Files in This Setup

- `Dockerfile`: Container definition with audiobox-aesthetics, FFmpeg, and dependencies
- `process_audio.py`: Python script that processes audio/video files with format conversion
- `run_single_file.sh`: Process individual audio or video files
- `run_test_files.sh`: Batch process all files in test_files directory
- `cleanup.sh`: Clean up generated test files and Docker artifacts
- `audiobox-aesthetics/`: Cloned repository with the original Meta codebase