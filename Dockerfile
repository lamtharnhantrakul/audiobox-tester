FROM python:3.10-slim

# Install system dependencies including video processing tools and audio backends
RUN apt-get update && apt-get install -y \
    git \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the audiobox-aesthetics repository
COPY audiobox-aesthetics /app/audiobox-aesthetics

# Install audio processing packages
RUN pip install --no-cache-dir soundfile tqdm

# Install audiobox-aesthetics (includes torch and other ML dependencies)
RUN cd audiobox-aesthetics && pip install -e .

# Create directories for input and output
RUN mkdir -p /app/input /app/output

# Copy our processing script
COPY process_audio.py /app/

# Set the entrypoint
ENTRYPOINT ["python", "/app/process_audio.py"]