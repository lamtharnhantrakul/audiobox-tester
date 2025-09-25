#!/usr/bin/env python3
"""
SQUIM Speech Quality Assessment Tool

This script uses TorchAudio's SQUIM models to assess speech quality metrics
including objective metrics (PESQ, STOI, SI-SDR) and subjective metrics (MOS).
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import warnings

import torch
import torchaudio
from tqdm import tqdm

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")


class SquimProcessor:
    """SQUIM speech quality assessment processor."""

    def __init__(self):
        """Initialize SQUIM models."""
        self.device = self._get_device()
        print(f"Using device: {self.device}")

        # Load SQUIM models
        print("Loading SQUIM objective model...")
        self.objective_bundle = torchaudio.pipelines.SQUIM_OBJECTIVE
        self.objective_model = self.objective_bundle.get_model().to(self.device)

        print("Loading SQUIM subjective model...")
        self.subjective_bundle = torchaudio.pipelines.SQUIM_SUBJECTIVE
        self.subjective_model = self.subjective_bundle.get_model().to(self.device)

        # Create a default non-matching reference for MOS calculation
        # Using a simple synthetic tone as NMR since we don't have clean references
        self.default_nmr = self._create_default_nmr()

        # Expected sample rate
        self.sample_rate = self.objective_bundle.sample_rate
        print(f"Expected sample rate: {self.sample_rate} Hz")

    def _get_device(self) -> torch.device:
        """Get the best available device."""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")

    def _load_audio(self, file_path: Path) -> Optional[Tuple[torch.Tensor, int]]:
        """Load audio file and handle format conversion."""
        try:
            # Try loading with torchaudio first
            waveform, orig_sr = torchaudio.load(file_path)

            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Resample if necessary
            if orig_sr != self.sample_rate:
                resampler = torchaudio.transforms.Resample(orig_sr, self.sample_rate)
                waveform = resampler(waveform)

            return waveform.to(self.device), self.sample_rate

        except Exception as e:
            print(f"❌ Error loading {file_path.name}: {e}")
            return None

    def _extract_audio_from_video(self, file_path: Path) -> Optional[Path]:
        """Extract audio from video file using FFmpeg."""
        try:
            import subprocess

            # Create temporary audio file
            temp_audio = file_path.parent / f"{file_path.stem}_temp_audio.wav"

            print(f"🎥 Extracting audio from video: {file_path.name}")

            # Use FFmpeg to extract audio
            cmd = [
                "ffmpeg", "-i", str(file_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", str(self.sample_rate),
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

    def process_file(self, file_path: Path) -> Optional[dict]:
        """Process a single file and return SQUIM metrics."""
        print(f"🔍 Processing: {file_path.name}")

        # Check if it's a video file
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        temp_audio_path = None

        if file_path.suffix.lower() in video_extensions:
            temp_audio_path = self._extract_audio_from_video(file_path)
            if temp_audio_path is None:
                return None
            processing_path = temp_audio_path
        else:
            processing_path = file_path

        try:
            # Load audio
            audio_data = self._load_audio(processing_path)
            if audio_data is None:
                return None

            waveform, sr = audio_data

            # Ensure minimum length for SQUIM
            min_length = int(0.5 * sr)  # 0.5 seconds minimum
            if waveform.shape[1] < min_length:
                print(f"⚠️  Warning: Audio too short ({waveform.shape[1]}/{min_length} samples). Padding...")
                padding = min_length - waveform.shape[1]
                waveform = torch.nn.functional.pad(waveform, (0, padding))

            with torch.no_grad():
                # Objective metrics: STOI, PESQ, SI-SDR
                stoi_est, pesq_est, si_sdr_est = self.objective_model(waveform)

                # Subjective metric: MOS
                mos_est = self.subjective_model(waveform)

            metrics = {
                'file_path': str(file_path),
                'stoi': float(stoi_est.cpu()),
                'pesq': float(pesq_est.cpu()),
                'si_sdr': float(si_sdr_est.cpu()),
                'mos': float(mos_est.cpu())
            }

            print(f"✅ Successfully processed {file_path.name}")
            return metrics

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            return None

        finally:
            # Clean up temporary audio file
            if temp_audio_path and temp_audio_path.exists():
                temp_audio_path.unlink()

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

                metrics = self.process_file(file_path)
                if metrics:
                    results.append(metrics)

                pbar.set_description("Processing")

        # Write results
        self._write_results(results, output_file)
        print(f"📝 Results saved to: {output_file}")

    def _write_results(self, results: List[dict], output_file: Path) -> None:
        """Write results to formatted text file."""
        with open(output_file, 'w') as f:
            f.write("Speech Quality Assessment Results (SQUIM)\n")
            f.write("=" * 50 + "\n\n")

            for result in results:
                f.write(f"File: {Path(result['file_path']).name}\n")
                f.write(f"Path: {result['file_path']}\n")
                f.write("Speech Quality Metrics:\n")
                f.write(f"  STOI (Speech Intelligibility): {result['stoi']:.3f}\n")
                f.write(f"  PESQ (Perceptual Quality): {result['pesq']:.3f}\n")
                f.write(f"  SI-SDR (Signal Distortion): {result['si_sdr']:.3f} dB\n")
                f.write(f"  MOS (Mean Opinion Score): {result['mos']:.3f}\n")
                f.write("\n" + "-" * 30 + "\n\n")

            # Summary statistics
            if results:
                f.write("Summary Statistics:\n")
                f.write("=" * 20 + "\n")
                f.write(f"Total files processed: {len(results)}\n")

                stoi_avg = sum(r['stoi'] for r in results) / len(results)
                pesq_avg = sum(r['pesq'] for r in results) / len(results)
                si_sdr_avg = sum(r['si_sdr'] for r in results) / len(results)
                mos_avg = sum(r['mos'] for r in results) / len(results)

                f.write(f"Average STOI: {stoi_avg:.3f}\n")
                f.write(f"Average PESQ: {pesq_avg:.3f}\n")
                f.write(f"Average SI-SDR: {si_sdr_avg:.3f} dB\n")
                f.write(f"Average MOS: {mos_avg:.3f}\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="SQUIM Speech Quality Assessment")
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
        processor = SquimProcessor()
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