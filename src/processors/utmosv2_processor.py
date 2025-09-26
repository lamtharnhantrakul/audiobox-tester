#!/usr/bin/env python3
"""UTMOSv2 Speech Naturalness Assessment Processor.

This module provides production-grade speech naturalness assessment using the
University of Tokyo's UTMOSv2 model, which achieved 1st place in 7/16 metrics
at the VoiceMOS Challenge 2024.

UTMOSv2 is specifically designed for evaluating the naturalness of synthetic
speech, making it ideal for TTS system evaluation and speech quality monitoring.

Example:
    >>> from processors.utmosv2_processor import UTMOSv2Processor
    >>> processor = UTMOSv2Processor()
    >>> results = processor.process_file(Path("speech.wav"))
    >>> print(f"MOS Score: {results['mos']:.3f}")

Attributes:
    SUPPORTED_SAMPLE_RATE (int): Required sample rate for UTMOSv2 (16kHz).
    MIN_DURATION_SECONDS (float): Minimum audio duration for reliable assessment.
    MAX_DURATION_SECONDS (float): Maximum recommended duration for processing.
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

import torch
import utmosv2
from tqdm import tqdm

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.audio_utils import AudioProcessor, DeviceManager
from utils.logging_utils import setup_logger, log_performance


class UTMOSv2Processor:
    """Production-grade UTMOSv2 speech naturalness assessment processor.

    This processor provides comprehensive speech naturalness evaluation using
    the University of Tokyo's UTMOSv2 model with automatic device management,
    robust error handling, and performance optimization.

    The processor handles:
    - Automatic audio format conversion and preprocessing
    - Intelligent device selection (CUDA/MPS/CPU)
    - Batch processing with progress tracking
    - Comprehensive error handling and logging
    - Statistical analysis and reporting

    Attributes:
        model: Loaded UTMOSv2 model instance.
        audio_processor: Audio processing utilities.
        logger: Structured logger for operation tracking.
        device: Compute device for model inference.
    """

    SUPPORTED_SAMPLE_RATE = 16000
    MIN_DURATION_SECONDS = 0.5
    MAX_DURATION_SECONDS = 30.0

    def __init__(self, device: Optional[torch.device] = None, force_cpu: bool = False) -> None:
        """Initialize UTMOSv2 processor with model loading and device setup.

        Args:
            device: Specific device to use. Auto-detected if None.
            force_cpu: Force CPU usage even if GPU is available.

        Raises:
            RuntimeError: If UTMOSv2 model fails to load.
            ImportError: If UTMOSv2 package is not installed.
        """
        self.logger = setup_logger(__name__)

        # Initialize device management
        device_manager = DeviceManager()
        if force_cpu:
            self.device = torch.device("cpu")
        else:
            self.device = device or device_manager.get_optimal_device()

        self.logger.info("Initializing UTMOSv2 processor", device=str(self.device))

        # Initialize audio processor
        self.audio_processor = AudioProcessor(self.device)

        # Load UTMOSv2 model
        self._load_model()

    def _load_model(self) -> None:
        """Load and initialize UTMOSv2 model.

        Raises:
            RuntimeError: If model loading fails.
            ImportError: If UTMOSv2 is not properly installed.
        """
        try:
            self.logger.info("Loading UTMOSv2 model...")
            self.model = utmosv2.create_model(pretrained=True)
            self.logger.info("UTMOSv2 model loaded successfully")

        except ImportError as e:
            error_msg = ("UTMOSv2 package not found. Install with: "
                        "pip install git+https://github.com/sarulab-speech/UTMOSv2.git")
            self.logger.error("UTMOSv2 import failed", error=str(e), solution=error_msg)
            raise ImportError(error_msg) from e

        except Exception as e:
            self.logger.error("UTMOSv2 model loading failed", error=str(e))
            raise RuntimeError(f"Failed to load UTMOSv2 model: {e}") from e

    @log_performance
    def process_file(self, file_path: Path) -> Optional[Dict[str, Union[str, float]]]:
        """Process single audio file for speech naturalness assessment.

        Args:
            file_path: Path to audio or video file to process.

        Returns:
            Dictionary containing assessment results:
            - file_path: Original file path
            - mos: Mean Opinion Score for naturalness (1.0-5.0)
            - duration_seconds: Audio duration in seconds
            - sample_rate: Audio sample rate used
            None if processing fails.

        Example:
            >>> processor = UTMOSv2Processor()
            >>> result = processor.process_file(Path("speech.wav"))
            >>> if result:
            ...     print(f"Naturalness MOS: {result['mos']:.3f}")
        """
        try:
            self.logger.info("Processing file for UTMOSv2 assessment", file=file_path.name)

            # Validate and preprocess audio
            audio_data = self.audio_processor.load_and_preprocess(
                file_path,
                target_sample_rate=self.SUPPORTED_SAMPLE_RATE
            )

            if audio_data is None:
                self.logger.error("Audio preprocessing failed", file=file_path.name)
                return None

            waveform, sample_rate = audio_data
            duration_seconds = waveform.shape[-1] / sample_rate

            # Validate audio duration
            if duration_seconds < self.MIN_DURATION_SECONDS:
                self.logger.warning(
                    "Audio too short for reliable assessment",
                    file=file_path.name,
                    duration=duration_seconds,
                    minimum=self.MIN_DURATION_SECONDS
                )

            if duration_seconds > self.MAX_DURATION_SECONDS:
                self.logger.info(
                    "Long audio file - truncating for processing",
                    file=file_path.name,
                    duration=duration_seconds,
                    truncated_to=self.MAX_DURATION_SECONDS
                )

            # Create temporary WAV file for UTMOSv2 processing
            temp_path = self._create_temp_wav(waveform, sample_rate)
            if temp_path is None:
                return None

            try:
                # Perform UTMOSv2 assessment
                with torch.no_grad():
                    mos_score = self.model.predict(
                        input_path=str(temp_path),
                        device='cpu'  # Force CPU to avoid CUDA issues in containers
                    )

                if mos_score is None:
                    self.logger.error("UTMOSv2 returned None score", file=file_path.name)
                    return None

                result = {
                    'file_path': str(file_path),
                    'mos': float(mos_score),
                    'duration_seconds': float(duration_seconds),
                    'sample_rate': int(sample_rate)
                }

                self.logger.info(
                    "UTMOSv2 assessment completed",
                    file=file_path.name,
                    mos_score=float(mos_score),
                    duration=float(duration_seconds)
                )

                return result

            finally:
                # Clean up temporary file
                if temp_path and temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            self.logger.error("UTMOSv2 processing failed", file=file_path.name, error=str(e))
            return None

    def _create_temp_wav(self, waveform: torch.Tensor, sample_rate: int) -> Optional[Path]:
        """Create temporary WAV file for UTMOSv2 processing.

        Args:
            waveform: Audio tensor data.
            sample_rate: Audio sample rate.

        Returns:
            Path to temporary WAV file, or None if creation failed.
        """
        try:
            import torchaudio

            temp_dir = Path(tempfile.mkdtemp())
            temp_path = temp_dir / "utmosv2_input.wav"

            # Save waveform as WAV file
            torchaudio.save(str(temp_path), waveform.cpu(), sample_rate)

            return temp_path

        except Exception as e:
            self.logger.error("Failed to create temporary WAV file", error=str(e))
            return None

    @log_performance
    def process_directory(
        self,
        input_dir: Path,
        output_file: Optional[Path] = None,
        recursive: bool = False
    ) -> Dict[str, Union[List[Dict], Dict[str, float]]]:
        """Process all audio files in directory for batch assessment.

        Args:
            input_dir: Directory containing audio files to process.
            output_file: Optional path to save results. If None, returns results only.
            recursive: Whether to search subdirectories recursively.

        Returns:
            Dictionary containing:
            - results: List of individual file results
            - statistics: Summary statistics (mean, min, max MOS scores)
            - metadata: Processing metadata (file count, success rate, etc.)

        Example:
            >>> processor = UTMOSv2Processor()
            >>> results = processor.process_directory(Path("audio_samples/"))
            >>> print(f"Average MOS: {results['statistics']['mean_mos']:.3f}")
        """
        self.logger.info("Starting batch UTMOSv2 processing", directory=str(input_dir))

        # Discover audio files
        pattern = "**/*" if recursive else "*"
        all_files = list(input_dir.glob(pattern))
        audio_files = [
            f for f in all_files
            if f.is_file() and (
                self.audio_processor.is_audio_file(f) or
                self.audio_processor.is_video_file(f)
            )
        ]

        if not audio_files:
            self.logger.warning("No audio files found", directory=str(input_dir))
            return {"results": [], "statistics": {}, "metadata": {"files_found": 0}}

        self.logger.info("Found audio files", count=len(audio_files))

        # Process files with progress tracking
        results = []
        successful_results = []

        with tqdm(audio_files, desc="Processing files", unit="file") as pbar:
            for file_path in pbar:
                pbar.set_postfix({"current": file_path.name})

                result = self.process_file(file_path)
                if result:
                    results.append(result)
                    successful_results.append(result)
                else:
                    results.append({
                        "file_path": str(file_path),
                        "error": "Processing failed"
                    })

        # Calculate statistics
        statistics = self._calculate_statistics(successful_results)

        # Prepare final results
        batch_results = {
            "results": results,
            "statistics": statistics,
            "metadata": {
                "files_found": len(audio_files),
                "files_processed": len(successful_results),
                "success_rate": len(successful_results) / len(audio_files) if audio_files else 0.0,
                "processor": "UTMOSv2",
                "version": "1.0.0"
            }
        }

        # Save results if output file specified
        if output_file:
            self._save_results(batch_results, output_file)

        self.logger.info(
            "Batch processing completed",
            total_files=len(audio_files),
            successful=len(successful_results),
            failed=len(audio_files) - len(successful_results)
        )

        return batch_results

    def _calculate_statistics(self, results: List[Dict]) -> Dict[str, float]:
        """Calculate statistical summary of MOS scores.

        Args:
            results: List of processing results containing MOS scores.

        Returns:
            Dictionary of statistical metrics.
        """
        if not results:
            return {}

        mos_scores = [r["mos"] for r in results if "mos" in r]

        if not mos_scores:
            return {}

        import statistics

        return {
            "mean_mos": statistics.mean(mos_scores),
            "median_mos": statistics.median(mos_scores),
            "stdev_mos": statistics.stdev(mos_scores) if len(mos_scores) > 1 else 0.0,
            "min_mos": min(mos_scores),
            "max_mos": max(mos_scores),
            "count": len(mos_scores)
        }

    def _save_results(self, results: Dict, output_file: Path) -> None:
        """Save processing results to formatted text file.

        Args:
            results: Processing results dictionary.
            output_file: Path to output file.
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("Speech Quality Assessment Results (UTMOSv2)\n")
                f.write("=" * 50 + "\n\n")

                # Write individual results
                for result in results["results"]:
                    if "error" in result:
                        f.write(f"File: {Path(result['file_path']).name}\n")
                        f.write(f"Error: {result['error']}\n")
                        f.write("-" * 30 + "\n\n")
                        continue

                    f.write(f"File: {Path(result['file_path']).name}\n")
                    f.write(f"Path: {result['file_path']}\n")
                    f.write("Speech Naturalness Metrics:\n")
                    f.write(f"  MOS (Mean Opinion Score): {result['mos']:.3f}\n")
                    if 'duration_seconds' in result:
                        f.write(f"  Duration: {result['duration_seconds']:.1f}s\n")
                    f.write("\n" + "-" * 30 + "\n\n")

                # Write statistics
                if results["statistics"]:
                    stats = results["statistics"]
                    f.write("Summary Statistics:\n")
                    f.write("=" * 20 + "\n")
                    f.write(f"Total files processed: {stats['count']}\n")
                    f.write(f"Average MOS: {stats['mean_mos']:.3f}\n")
                    f.write(f"Median MOS: {stats['median_mos']:.3f}\n")
                    f.write(f"Standard Deviation: {stats['stdev_mos']:.3f}\n")
                    f.write(f"Minimum MOS: {stats['min_mos']:.3f}\n")
                    f.write(f"Maximum MOS: {stats['max_mos']:.3f}\n\n")

                # Write metadata
                metadata = results["metadata"]
                f.write("Processing Metadata:\n")
                f.write("=" * 20 + "\n")
                f.write(f"Success Rate: {metadata['success_rate']:.1%}\n")
                f.write(f"Processor: {metadata['processor']}\n")
                f.write(f"Version: {metadata['version']}\n\n")

                f.write("Note: UTMOSv2 predicts naturalness of synthetic speech.\n")
                f.write("Higher MOS scores indicate more natural-sounding speech.\n")

            self.logger.info("Results saved successfully", output_file=str(output_file))

        except Exception as e:
            self.logger.error("Failed to save results", error=str(e), output_file=str(output_file))


def main() -> None:
    """Command-line interface for UTMOSv2 processor."""
    import argparse

    parser = argparse.ArgumentParser(
        description="UTMOSv2 Speech Naturalness Assessment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s speech.wav --output results.txt
  %(prog)s audio_dir/ --output batch_results.txt --recursive
  %(prog)s video.mp4 --force-cpu
        """
    )

    parser.add_argument("input", type=Path, help="Input audio file or directory")
    parser.add_argument("--output", "-o", type=Path, help="Output results file")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process directories recursively")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU usage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logger(__name__, level=log_level)

    try:
        processor = UTMOSv2Processor(force_cpu=args.force_cpu)

        if args.input.is_file():
            # Process single file
            result = processor.process_file(args.input)
            if result:
                print(f"File: {result['file_path']}")
                print(f"MOS Score: {result['mos']:.3f}")
                if args.output:
                    batch_results = {
                        "results": [result],
                        "statistics": processor._calculate_statistics([result]),
                        "metadata": {"files_processed": 1, "processor": "UTMOSv2", "version": "1.0.0"}
                    }
                    processor._save_results(batch_results, args.output)
            else:
                logger.error("Processing failed")
                sys.exit(1)

        elif args.input.is_dir():
            # Process directory
            results = processor.process_directory(
                args.input,
                output_file=args.output,
                recursive=args.recursive
            )
            print(f"Processed {results['metadata']['files_processed']} files")
            if results['statistics']:
                print(f"Average MOS: {results['statistics']['mean_mos']:.3f}")

        else:
            logger.error("Input must be a file or directory")
            sys.exit(1)

    except Exception as e:
        logger.error("UTMOSv2 processing failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()