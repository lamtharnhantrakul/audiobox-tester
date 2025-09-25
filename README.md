# Audiobox Aesthetics Docker Setup

This setup provides a Docker container for testing audiobox-aesthetics on your audio files.

## Prerequisites

1. Docker Desktop must be installed and running
2. Audio files in a directory (supports: .wav, .flac, .mp3, .m4a, .ogg)

## Quick Start

1. **Start Docker Desktop** (make sure it's running)

2. **Run the analysis** on your audio files:
   ```bash
   ./run_audiobox.sh /path/to/your/audio/files [output_filename.txt]
   ```

   Example:
   ```bash
   ./run_audiobox.sh ~/Music/samples results.txt
   ```

3. **View results** in the generated text file

## What the Analysis Provides

The tool analyzes each audio file and provides 4 aesthetic metrics:

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
- **No audio files found**: Check that your directory contains supported audio formats
- **Out of memory**: The model requires significant memory; ensure Docker has enough RAM allocated

## Files in This Setup

- `Dockerfile`: Container definition with audiobox-aesthetics and dependencies
- `process_audio.py`: Python script that processes audio files and generates metrics
- `run_audiobox.sh`: Convenience script to build and run the container
- `audiobox-aesthetics/`: Cloned repository with the original codebase