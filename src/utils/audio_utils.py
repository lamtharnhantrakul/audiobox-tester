"""Audio processing utilities for production-grade audio analysis.

This module provides robust audio processing capabilities with comprehensive
error handling, format validation, and device management for ML workloads.

Example:
    >>> from src.utils.audio_utils import AudioProcessor, DeviceManager
    >>> device_manager = DeviceManager()
    >>> processor = AudioProcessor(device_manager.get_optimal_device())
    >>> audio_data = processor.load_and_preprocess("audio.mp3")
"""

import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import torch
import torchaudio
from torchaudio.transforms import Resample

from .logging_utils import setup_logger


class AudioFormat(Enum):
    """Supported audio formats with metadata."""

    WAV = {"extension": ".wav", "codec": "pcm_s16le", "container": "wav"}
    MP3 = {"extension": ".mp3", "codec": "mp3", "container": "mp3"}
    FLAC = {"extension": ".flac", "codec": "flac", "container": "flac"}
    M4A = {"extension": ".m4a", "codec": "aac", "container": "mp4"}
    OGG = {"extension": ".ogg", "codec": "libvorbis", "container": "ogg"}
    AIFF = {"extension": ".aiff", "codec": "pcm_s16be", "container": "aiff"}

    @classmethod
    def from_extension(cls, extension: str) -> Optional["AudioFormat"]:
        """Get AudioFormat from file extension.

        Args:
            extension: File extension (with or without leading dot).

        Returns:
            AudioFormat enum member or None if not supported.
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'

        for format_type in cls:
            if format_type.value["extension"].lower() == extension.lower():
                return format_type
        return None

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Get list of all supported audio extensions."""
        return [format_type.value["extension"] for format_type in cls]


class DeviceManager:
    """Manages compute device selection and optimization for ML workloads.

    Provides intelligent device selection with fallback strategies and
    performance optimization for different hardware configurations.
    """

    def __init__(self) -> None:
        """Initialize device manager with automatic detection."""
        self.logger = setup_logger(__name__)
        self._available_devices = self._detect_devices()

    def _detect_devices(self) -> Dict[str, bool]:
        """Detect available compute devices.

        Returns:
            Dictionary mapping device types to availability.
        """
        devices = {
            "cuda": False,
            "mps": False,
            "cpu": True  # CPU is always available
        }

        # Check CUDA availability
        if torch.cuda.is_available():
            try:
                torch.cuda.current_device()
                devices["cuda"] = True
                self.logger.info("CUDA device detected and functional")
            except Exception as e:
                self.logger.warning("CUDA available but not functional", error=str(e))

        # Check MPS (Apple Silicon) availability
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            try:
                test_tensor = torch.tensor([1.0]).to("mps")
                devices["mps"] = True
                self.logger.info("MPS device detected and functional")
            except Exception as e:
                self.logger.warning("MPS available but not functional", error=str(e))

        return devices

    def get_optimal_device(self, prefer_gpu: bool = True) -> torch.device:
        """Get optimal compute device based on availability and preferences.

        Args:
            prefer_gpu: Whether to prefer GPU over CPU when available.

        Returns:
            Optimal torch.device for computation.
        """
        if prefer_gpu:
            if self._available_devices["cuda"]:
                self.logger.info("Using CUDA device for processing")
                return torch.device("cuda")
            elif self._available_devices["mps"]:
                self.logger.info("Using MPS device for processing")
                return torch.device("mps")

        self.logger.info("Using CPU device for processing")
        return torch.device("cpu")

    def get_device_info(self) -> Dict[str, Union[str, int, float]]:
        """Get detailed information about the selected device.

        Returns:
            Dictionary containing device specifications and capabilities.
        """
        device = self.get_optimal_device()
        info = {
            "device_type": device.type,
            "device_index": getattr(device, 'index', 0)
        }

        if device.type == "cuda":
            info.update({
                "cuda_version": torch.version.cuda,
                "device_name": torch.cuda.get_device_name(device),
                "memory_total": torch.cuda.get_device_properties(device).total_memory,
                "memory_allocated": torch.cuda.memory_allocated(device),
                "compute_capability": torch.cuda.get_device_capability(device)
            })
        elif device.type == "mps":
            info.update({
                "mps_available": torch.backends.mps.is_available(),
                "mps_built": torch.backends.mps.is_built()
            })

        return info


class AudioProcessor:
    """High-performance audio processor with format conversion and validation.

    Provides production-grade audio processing capabilities including format
    conversion, resampling, validation, and preprocessing for ML models.

    Attributes:
        device: Compute device for audio processing.
        supported_sample_rates: List of commonly used sample rates.
    """

    SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_CHANNELS = 1

    def __init__(self, device: Optional[torch.device] = None) -> None:
        """Initialize audio processor.

        Args:
            device: Compute device for processing. Auto-detected if None.
        """
        self.logger = setup_logger(__name__)
        self.device = device or DeviceManager().get_optimal_device()
        self.supported_sample_rates = [8000, 16000, 22050, 44100, 48000]

    def is_audio_file(self, file_path: Path) -> bool:
        """Check if file is a supported audio format.

        Args:
            file_path: Path to file to check.

        Returns:
            True if file is supported audio format.
        """
        return AudioFormat.from_extension(file_path.suffix) is not None

    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported video format.

        Args:
            file_path: Path to file to check.

        Returns:
            True if file is supported video format.
        """
        return file_path.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS

    def validate_audio_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate audio file integrity and format support.

        Args:
            file_path: Path to audio file to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"

        if not (self.is_audio_file(file_path) or self.is_video_file(file_path)):
            return False, f"Unsupported file format: {file_path.suffix}"

        try:
            if self.is_audio_file(file_path):
                # Quick validation by loading metadata
                info = torchaudio.info(str(file_path))
                if info.num_frames <= 0:
                    return False, "Audio file contains no frames"
                if info.sample_rate <= 0:
                    return False, "Invalid sample rate"
            return True, None
        except Exception as e:
            return False, f"Audio validation failed: {str(e)}"

    def extract_audio_from_video(self, video_path: Path, target_sample_rate: int = DEFAULT_SAMPLE_RATE) -> Optional[Path]:
        """Extract audio from video file using FFmpeg.

        Args:
            video_path: Path to video file.
            target_sample_rate: Target sample rate for extracted audio.

        Returns:
            Path to extracted audio file, or None if extraction failed.
        """
        try:
            temp_dir = Path(tempfile.mkdtemp())
            output_path = temp_dir / f"{video_path.stem}_extracted.wav"

            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-vn",  # No video output
                "-acodec", "pcm_s16le",  # 16-bit PCM
                "-ar", str(target_sample_rate),  # Sample rate
                "-ac", str(self.DEFAULT_CHANNELS),  # Mono
                "-y",  # Overwrite output file
                str(output_path)
            ]

            self.logger.info("Extracting audio from video", video_file=video_path.name)
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("Audio extraction successful", output_path=str(output_path))
                return output_path
            else:
                self.logger.error(
                    "Audio extraction failed",
                    stderr=result.stderr,
                    returncode=result.returncode
                )
                return None

        except Exception as e:
            self.logger.error("Audio extraction error", error=str(e))
            return None

    def convert_audio_format(
        self,
        input_path: Path,
        target_format: AudioFormat = AudioFormat.WAV,
        target_sample_rate: int = DEFAULT_SAMPLE_RATE,
        target_channels: int = DEFAULT_CHANNELS
    ) -> Optional[Path]:
        """Convert audio file to target format and specifications.

        Args:
            input_path: Path to input audio file.
            target_format: Target audio format.
            target_sample_rate: Target sample rate in Hz.
            target_channels: Target number of channels.

        Returns:
            Path to converted audio file, or None if conversion failed.
        """
        try:
            temp_dir = Path(tempfile.mkdtemp())
            output_path = temp_dir / f"{input_path.stem}_converted{target_format.value['extension']}"

            cmd = [
                "ffmpeg", "-i", str(input_path),
                "-acodec", target_format.value["codec"],
                "-ar", str(target_sample_rate),
                "-ac", str(target_channels),
                "-y",  # Overwrite output file
                str(output_path)
            ]

            self.logger.info(
                "Converting audio format",
                input_file=input_path.name,
                target_format=target_format.name,
                target_sample_rate=target_sample_rate
            )

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("Audio conversion successful", output_path=str(output_path))
                return output_path
            else:
                self.logger.error(
                    "Audio conversion failed",
                    stderr=result.stderr,
                    returncode=result.returncode
                )
                return None

        except Exception as e:
            self.logger.error("Audio conversion error", error=str(e))
            return None

    def load_and_preprocess(
        self,
        file_path: Path,
        target_sample_rate: int = DEFAULT_SAMPLE_RATE,
        normalize: bool = True
    ) -> Optional[Tuple[torch.Tensor, int]]:
        """Load and preprocess audio file for ML model consumption.

        Args:
            file_path: Path to audio file.
            target_sample_rate: Target sample rate for preprocessing.
            normalize: Whether to normalize audio amplitude.

        Returns:
            Tuple of (audio_tensor, sample_rate) or None if loading failed.
        """
        try:
            # Validate file first
            is_valid, error_msg = self.validate_audio_file(file_path)
            if not is_valid:
                self.logger.error("Audio validation failed", error=error_msg)
                return None

            processing_path = file_path

            # Handle video files by extracting audio
            if self.is_video_file(file_path):
                extracted_path = self.extract_audio_from_video(file_path, target_sample_rate)
                if not extracted_path:
                    return None
                processing_path = extracted_path

            # Handle non-WAV audio files by converting
            elif file_path.suffix.lower() != '.wav':
                converted_path = self.convert_audio_format(file_path)
                if not converted_path:
                    return None
                processing_path = converted_path

            # Load audio with torchaudio
            waveform, sample_rate = torchaudio.load(str(processing_path))

            # Resample if needed
            if sample_rate != target_sample_rate:
                resampler = Resample(sample_rate, target_sample_rate)
                waveform = resampler(waveform)
                sample_rate = target_sample_rate

            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Normalize amplitude
            if normalize:
                max_val = torch.max(torch.abs(waveform))
                if max_val > 0:
                    waveform = waveform / max_val

            # Move to target device
            waveform = waveform.to(self.device)

            self.logger.info(
                "Audio preprocessing completed",
                file=file_path.name,
                duration_s=waveform.shape[-1] / sample_rate,
                sample_rate=sample_rate,
                channels=waveform.shape[0]
            )

            # Clean up temporary files
            if processing_path != file_path and processing_path.exists():
                processing_path.unlink()

            return waveform, sample_rate

        except Exception as e:
            self.logger.error("Audio preprocessing failed", error=str(e))
            return None