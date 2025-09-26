#!/usr/bin/env python3
"""
UTMOSv2 Speech Quality Assessment Tool

This script uses UTMOSv2 to predict Mean Opinion Score (MOS) for synthetic speech naturalness.
UTMOSv2 achieved 1st place in 7/16 metrics at VoiceMOS Challenge 2024.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import warnings

import torch
import torchaudio
from tqdm import tqdm

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

try:
    import utmosv2
except ImportError:
    print("❌ Error: UTMOSv2 not installed. Please install with:")
    print("pip install git+https://github.com/sarulab-speech/UTMOSv2.git")
    sys.exit(1)


class UTMOSv2Processor:
    """UTMOSv2 speech quality assessment processor."""

    def __init__(self):
        """Initialize UTMOSv2 model."""
        self.device = self._get_device()
        print(f"Using device: {self.device}")

        print("Loading UTMOSv2 model...")
        try:
            # Force CPU mode to avoid CUDA compatibility issues in Docker
            self.model = utmosv2.create_model(pretrained=True)
            if hasattr(self.model, 'to'):
                self.model = self.model.to('cpu')
            print("✅ UTMOSv2 model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load UTMOSv2 model: {e}")
            # Try alternative initialization approaches
            print("🔄 Trying alternative model initialization...")
            try:
                # Set environment variable to force CPU mode
                os.environ['CUDA_VISIBLE_DEVICES'] = ''
                torch.cuda.is_available = lambda: False
                self.model = utmosv2.create_model(pretrained=True)
                if hasattr(self.model, 'to'):
                    self.model = self.model.to('cpu')
                print("✅ UTMOSv2 model loaded successfully (CPU mode)")
            except Exception as e2:
                print(f"❌ Alternative initialization also failed: {e2}")
                raise

    def _get_device(self) -> torch.device:
        """Get the best available device (forced to CPU for Docker compatibility)."""
        # Force CPU mode to avoid CUDA compatibility issues in Docker
        return torch.device("cpu")

    def _extract_audio_from_video(self, file_path: Path) -> Optional[Path]:
        """Extract audio from video file using FFmpeg."""
        try:
            import subprocess

            # Create temporary audio file
            temp_audio = file_path.parent / f"{file_path.stem}_temp_audio.wav"

            print(f"🎥 Extracting audio from video: {file_path.name}")

            # Use FFmpeg to extract audio (16kHz mono WAV for UTMOSv2)
            cmd = [
                "ffmpeg", "-i", str(file_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000",
                "-ac", "1", "-y", str(temp_audio)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Successfully extracted audio from {file_path.name}")
                return temp_audio
            else:
                print(f"❌ Failed to extract audio from {file_path.name}")
                return None

        except Exception as e:
            print(f"❌ Error extracting audio from {file_path.name}: {e}")
            return None

    def _convert_audio_format(self, file_path: Path) -> Optional[Path]:
        """Convert audio to WAV format using FFmpeg."""
        try:
            import subprocess

            # Create temporary WAV file
            temp_wav = file_path.parent / f"{file_path.stem}_temp_converted.wav"

            print(f"🔄 Converting audio format: {file_path.name}")

            # Use FFmpeg to convert to 16kHz mono WAV
            cmd = [
                "ffmpeg", "-i", str(file_path),
                "-acodec", "pcm_s16le", "-ar", "16000",
                "-ac", "1", "-y", str(temp_wav)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Successfully converted {file_path.name}")
                return temp_wav
            else:
                print(f"❌ Failed to convert {file_path.name}")
                return None

        except Exception as e:
            print(f"❌ Error converting {file_path.name}: {e}")
            return None

    def process_file(self, file_path: Path) -> Optional[dict]:
        """Process a single file and return UTMOSv2 MOS score."""
        print(f"🔍 Processing: {file_path.name}")

        # Check if it's a video file
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        audio_extensions = {'.wav', '.flac', '.mp3', '.m4a', '.ogg', '.aac', '.wma', '.aiff', '.au'}
        temp_file_path = None

        if file_path.suffix.lower() in video_extensions:
            temp_file_path = self._extract_audio_from_video(file_path)
            if temp_file_path is None:
                return None
            processing_path = temp_file_path
        elif file_path.suffix.lower() in audio_extensions:
            # Try direct processing first, fallback to conversion if needed
            processing_path = file_path
        else:
            print(f"❌ Unsupported file format: {file_path.suffix}")
            return None

        try:
            # Set environment variables to force CPU mode before prediction
            import os
            original_cuda_devices = os.environ.get('CUDA_VISIBLE_DEVICES', '')
            os.environ['CUDA_VISIBLE_DEVICES'] = ''

            # Try to predict MOS using UTMOSv2
            with torch.no_grad():
                # Ensure model is on CPU
                if hasattr(self.model, 'to'):
                    self.model = self.model.to('cpu')

                # UTMOSv2 API might use different method names
                if hasattr(self.model, 'predict'):
                    mos_score = self.model.predict(input_path=str(processing_path))
                elif hasattr(self.model, '__call__'):
                    # Try direct call with file path
                    mos_score = self.model(str(processing_path))
                else:
                    # Try to load audio and use the model directly
                    import torchaudio
                    waveform, sample_rate = torchaudio.load(str(processing_path))
                    # Resample to 16kHz if needed
                    if sample_rate != 16000:
                        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                        waveform = resampler(waveform)
                    mos_score = self.model(waveform)

            if mos_score is None:
                # If direct processing failed, try format conversion
                if processing_path == file_path:  # Only if we haven't already converted
                    print(f"🔄 Direct processing failed, trying format conversion...")
                    temp_file_path = self._convert_audio_format(file_path)
                    if temp_file_path is None:
                        return None
                    processing_path = temp_file_path
                    with torch.no_grad():
                        # Try the same API approach as before
                        if hasattr(self.model, 'predict'):
                            mos_score = self.model.predict(input_path=str(processing_path))
                        elif hasattr(self.model, '__call__'):
                            mos_score = self.model(str(processing_path))
                        else:
                            import torchaudio
                            waveform, sample_rate = torchaudio.load(str(processing_path))
                            if sample_rate != 16000:
                                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                                waveform = resampler(waveform)
                            mos_score = self.model(waveform)

                if mos_score is None:
                    print(f"❌ UTMOSv2 prediction failed for {file_path.name}")
                    return None

            # Restore original CUDA_VISIBLE_DEVICES
            os.environ['CUDA_VISIBLE_DEVICES'] = original_cuda_devices

            result = {
                'file_path': str(file_path),
                'mos': float(mos_score)
            }

            print(f"✅ Successfully processed {file_path.name} (MOS: {mos_score:.3f})")
            return result

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            return None

        finally:
            # Clean up temporary file
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink()

    def process_directory(self, input_dir: Path, output_file: Path) -> None:
        """Process all supported audio/video files in a directory."""
        # Supported extensions
        audio_extensions = {'.wav', '.flac', '.mp3', '.m4a', '.ogg', '.aac', '.wma', '.aiff', '.au'}
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        supported_extensions = audio_extensions | video_extensions

        # Find all supported files
        media_files = []
        for ext in supported_extensions:
            media_files.extend(input_dir.glob(f"*{ext}"))
            media_files.extend(input_dir.glob(f"*{ext.upper()}"))

        media_files = sorted(set(media_files))

        if not media_files:
            print("❌ No supported audio/video files found in the directory.")
            return

        print(f"Found {len(media_files)} media file(s) to process")

        results = []

        # Process files with progress bar
        with tqdm(media_files, desc="Processing", unit="file") as pbar:
            for file_path in pbar:
                pbar.set_description(f"Processing: {file_path.name}")

                result = self.process_file(file_path)
                if result:
                    results.append(result)

                pbar.set_description("Processing")

        # Write results
        self._write_results(results, output_file)
        print(f"📝 Results saved to: {output_file}")

    def _write_results(self, results: List[dict], output_file: Path) -> None:
        """Write results to formatted text file."""
        with open(output_file, 'w') as f:
            f.write("Speech Quality Assessment Results (UTMOSv2)\n")
            f.write("=" * 50 + "\n\n")

            for result in results:
                f.write(f"File: {Path(result['file_path']).name}\n")
                f.write(f"Path: {result['file_path']}\n")
                f.write("Speech Naturalness Metrics:\n")
                f.write(f"  MOS (Mean Opinion Score): {result['mos']:.3f}\n")
                f.write("\n" + "-" * 30 + "\n\n")

            # Summary statistics
            if results:
                f.write("Summary Statistics:\n")
                f.write("=" * 20 + "\n")
                f.write(f"Total files processed: {len(results)}\n")

                mos_avg = sum(r['mos'] for r in results) / len(results)
                mos_min = min(r['mos'] for r in results)
                mos_max = max(r['mos'] for r in results)

                f.write(f"Average MOS: {mos_avg:.3f}\n")
                f.write(f"Minimum MOS: {mos_min:.3f}\n")
                f.write(f"Maximum MOS: {mos_max:.3f}\n")
                f.write("\nNote: UTMOSv2 predicts naturalness of synthetic speech.\n")
                f.write("Higher MOS scores indicate more natural-sounding speech.\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="UTMOSv2 Speech Quality Assessment")
    parser.add_argument("input_path", help="Input directory containing audio/video files")
    parser.add_argument("output_file", help="Output file for results")

    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_file = Path(args.output_file)

    if not input_path.exists():
        print(f"❌ Error: Input path '{input_path}' does not exist.")
        sys.exit(1)

    if not input_path.is_dir():
        print(f"❌ Error: Input path '{input_path}' is not a directory.")
        sys.exit(1)

    # Initialize processor and run
    try:
        processor = UTMOSv2Processor()
        processor.process_directory(input_path, output_file)
        print("🎉 Processing complete!")

    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()