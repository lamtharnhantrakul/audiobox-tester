#!/usr/bin/env python3
"""
Audio Quality Assessment Toolkit
=================================

A comprehensive audio analysis toolkit providing three complementary approaches
to audio quality assessment through containerized, production-ready solutions.

This package integrates:
- Audiobox-Aesthetics: Meta's aesthetic dimension analysis
- SQUIM: TorchAudio's speech quality assessment
- UTMOSv2: University of Tokyo's speech naturalness evaluation
"""

import sys
from pathlib import Path
from setuptools import setup, find_packages

if sys.version_info < (3, 9):
    raise RuntimeError("Python 3.9+ is required")

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path, encoding="utf-8") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

# Read long description
readme_path = Path(__file__).parent / "README.md"
with open(readme_path, encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="audio-quality-toolkit",
    version="1.0.0",
    description="Production-grade audio quality assessment toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Audio Quality Team",
    author_email="team@example.com",
    url="https://github.com/example/audio-quality-toolkit",
    license="MIT",

    packages=find_packages(where="src"),
    package_dir={"": "src"},

    python_requires=">=3.9",
    install_requires=requirements,

    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.9.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.4.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
    },

    entry_points={
        "console_scripts": [
            "audio-quality=processors.cli:main",
            "audiobox-assess=processors.audiobox_processor:main",
            "squim-assess=processors.squim_processor:main",
            "utmosv2-assess=processors.utmosv2_processor:main",
        ],
    },

    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
    ],

    keywords=[
        "audio", "quality", "assessment", "speech", "music",
        "aesthetics", "squim", "utmosv2", "pytorch", "ai"
    ],

    project_urls={
        "Bug Reports": "https://github.com/example/audio-quality-toolkit/issues",
        "Documentation": "https://audio-quality-toolkit.readthedocs.io/",
        "Source": "https://github.com/example/audio-quality-toolkit",
    },

    include_package_data=True,
    zip_safe=False,
)