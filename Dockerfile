FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code and data
COPY . .

# Verify data files exist
RUN ls -la /app/data/ || echo "Warning: data directory not found"

# Create non-root user
RUN useradd -m appuser
USER appuser

# Run application
CMD ["python", "src/main.py"]
