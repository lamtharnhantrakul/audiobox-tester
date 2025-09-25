#!/usr/bin/env python3
"""
Process audio/video files in a directory using audiobox-aesthetics
Usage: python process_audio.py <input_directory> <output_file>
"""

import sys
import os
import json
from pathlib import Path
from tqdm import tqdm

# Supported audio and video formats
AUDIO_EXTENSIONS = {'.wav', '.flac', '.mp3', '.m4a', '.ogg', '.aac', '.wma', '.aiff', '.au'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}

def find_media_files(directory):
    """Find all supported audio and video files in directory"""
    media_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()

            if ext in AUDIO_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                media_files.append(file_path)

    return sorted(media_files)

def extract_audio_from_video(video_path):
    """Extract audio from video file using FFmpeg"""
    import tempfile
    import subprocess

    try:
        # Print will be handled by progress bar in calling function
        pass

        # Create temporary audio file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio_path = temp_audio.name
        temp_audio.close()

        # Use FFmpeg to extract audio
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,          # Input video file
            '-vn',                     # Disable video output
            '-acodec', 'pcm_s16le',    # Use 16-bit PCM audio codec
            '-ar', '16000',            # Set sample rate to 16kHz (required by model)
            '-ac', '1',                # Convert to mono
            '-y',                      # Overwrite output file if exists
            temp_audio_path
        ]

        # Run FFmpeg command
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Check if the output file was created and has content
            if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 0:
                return temp_audio_path
            else:
                return None
        else:
            return None

    except FileNotFoundError:
        return None
    except Exception as e:
        return None

def convert_audio_format(audio_path):
    """Convert unsupported audio formats to WAV using FFmpeg"""
    import tempfile
    import subprocess

    try:
        # Print will be handled by progress bar in calling function
        pass

        # Create temporary audio file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio_path = temp_audio.name
        temp_audio.close()

        # Use FFmpeg to convert audio
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', audio_path,          # Input audio file
            '-acodec', 'pcm_s16le',    # Use 16-bit PCM audio codec
            '-ar', '16000',            # Set sample rate to 16kHz (required by model)
            '-ac', '1',                # Convert to mono
            '-y',                      # Overwrite output file if exists
            temp_audio_path
        ]

        # Run FFmpeg command
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Check if the output file was created and has content
            if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 0:
                return temp_audio_path
            else:
                return None
        else:
            return None

    except FileNotFoundError:
        return None
    except Exception as e:
        return None

def main():
    if len(sys.argv) != 3:
        print("Usage: python process_audio.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    # Find all media files
    media_files = find_media_files(input_dir)

    if not media_files:
        print(f"No supported media files found in {input_dir}")
        print(f"Supported formats: Audio: {', '.join(AUDIO_EXTENSIONS)}")
        print(f"                   Video: {', '.join(VIDEO_EXTENSIONS)}")
        sys.exit(1)

    print(f"Found {len(media_files)} media files to process")

    try:
        from audiobox_aesthetics.infer import initialize_predictor

        print("Initializing predictor...")
        predictor = initialize_predictor()

        results = []
        temp_audio_files = []  # Track temporary files for cleanup

        # Create progress bar for file processing
        progress_bar = tqdm(media_files, desc="Processing files", unit="file")

        for media_file in progress_bar:
            # Update progress bar description with current file
            current_file = os.path.basename(media_file)
            progress_bar.set_description(f"Processing: {current_file[:30]}{'...' if len(current_file) > 30 else ''}")

            file_ext = os.path.splitext(media_file)[1].lower()
            audio_file = media_file

            # Extract audio from video if needed
            if file_ext in VIDEO_EXTENSIONS:
                progress_bar.write(f"🎥 Extracting audio from video: {os.path.basename(media_file)}")
                audio_file = extract_audio_from_video(media_file)
                if audio_file is None:
                    progress_bar.write(f"✗ Failed to extract audio from {os.path.basename(media_file)}")
                    results.append({
                        'file': os.path.basename(media_file),
                        'path': media_file,
                        'error': 'Failed to extract audio'
                    })
                    continue
                progress_bar.write(f"✓ Successfully extracted audio from {os.path.basename(media_file)}")
                temp_audio_files.append(audio_file)

            try:
                # Run prediction
                prediction = predictor.forward([{"path": audio_file}])

                if prediction and len(prediction) > 0:
                    result = prediction[0]
                    results.append({
                        'file': os.path.basename(media_file),
                        'path': media_file,
                        'metrics': result
                    })
                else:
                    results.append({
                        'file': os.path.basename(media_file),
                        'path': media_file,
                        'error': 'No prediction returned'
                    })

            except Exception as e:
                error_message = str(e)
                progress_bar.write(f"✗ Error processing {os.path.basename(media_file)}: {e}")

                # Check if this is an audio format issue and we haven't already converted
                if ("Format not recognised" in error_message or "Error opening" in error_message) and audio_file == media_file:
                    progress_bar.write(f"🔄 Attempting format conversion for {os.path.basename(media_file)}")
                    converted_audio_file = convert_audio_format(media_file)

                    if converted_audio_file is not None:
                        temp_audio_files.append(converted_audio_file)
                        try:
                            # Retry prediction with converted audio
                            prediction = predictor.forward([{"path": converted_audio_file}])

                            if prediction and len(prediction) > 0:
                                result = prediction[0]
                                results.append({
                                    'file': os.path.basename(media_file),
                                    'path': media_file,
                                    'metrics': result
                                })
                                progress_bar.write(f"✓ Successfully processed {os.path.basename(media_file)} after format conversion")
                            else:
                                results.append({
                                    'file': os.path.basename(media_file),
                                    'path': media_file,
                                    'error': 'No prediction returned after format conversion'
                                })
                        except Exception as retry_error:
                            progress_bar.write(f"✗ Error processing converted audio for {os.path.basename(media_file)}: {retry_error}")
                            results.append({
                                'file': os.path.basename(media_file),
                                'path': media_file,
                                'error': f'Failed after format conversion: {str(retry_error)}'
                            })
                    else:
                        results.append({
                            'file': os.path.basename(media_file),
                            'path': media_file,
                            'error': f'Format conversion failed: {error_message}'
                        })
                else:
                    # Other types of errors or already converted files
                    results.append({
                        'file': os.path.basename(media_file),
                        'path': media_file,
                        'error': error_message
                    })

        # Close progress bar
        progress_bar.close()

        # Clean up temporary audio files
        for temp_file in temp_audio_files:
            try:
                os.unlink(temp_file)
            except:
                pass

        # Write results to file
        with open(output_file, 'w') as f:
            f.write("Audio File Aesthetics Metrics\n")
            f.write("=" * 50 + "\n\n")

            for result in results:
                f.write(f"File: {result['file']}\n")
                f.write(f"Path: {result['path']}\n")

                if 'error' in result:
                    f.write(f"Error: {result['error']}\n")
                else:
                    f.write("Metrics:\n")
                    metrics = result['metrics']
                    f.write(f"  Content Enjoyment (CE): {metrics.get('CE', 'N/A'):.3f}\n")
                    f.write(f"  Content Usefulness (CU): {metrics.get('CU', 'N/A'):.3f}\n")
                    f.write(f"  Production Complexity (PC): {metrics.get('PC', 'N/A'):.3f}\n")
                    f.write(f"  Production Quality (PQ): {metrics.get('PQ', 'N/A'):.3f}\n")

                f.write("\n" + "-" * 30 + "\n\n")

        print(f"Results saved to: {output_file}")
        print(f"Processed {len(results)} files")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()