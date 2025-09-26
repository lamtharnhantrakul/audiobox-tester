"""Audio Quality Assessment Toolkit.

A production-grade audio analysis toolkit providing comprehensive quality assessment
through three complementary approaches: aesthetic analysis, speech quality metrics,
and naturalness evaluation.

Copyright (c) 2024 Audio Quality Team
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Audio Quality Team"
__email__ = "team@example.com"

from . import processors, utils, models

__all__ = ["processors", "utils", "models", "__version__"]