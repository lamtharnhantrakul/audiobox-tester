FROM python:3.10-slim

# Install system dependencies including video processing tools and audio backends
RUN apt-get update && apt-get install -y \
    git \
    wget \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the audiobox-aesthetics repository
COPY audiobox-aesthetics /app/audiobox-aesthetics

# Copy requirements file for dependency installation
COPY requirements.txt /app/

# Install all dependencies from requirements.txt (includes UTMOSv2 and additional dependencies)
RUN pip install --no-cache-dir --timeout=120 -r requirements.txt

# Install audiobox-aesthetics (includes additional ML dependencies)
RUN cd audiobox-aesthetics && pip install -e .

# Create directories for input and output
RUN mkdir -p /app/input /app/output

# Copy all processing scripts
COPY process_audiobox.py /app/
COPY process_squim.py /app/
COPY process_utmosv2.py /app/
RUN chmod +x /app/process_audiobox.py /app/process_squim.py /app/process_utmosv2.py

# Default entrypoint (can be overridden)
ENTRYPOINT ["python", "/app/process_audiobox.py"]