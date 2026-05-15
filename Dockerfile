FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
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

# ✅ Expose port
EXPOSE 8080

# ✅ Add healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Create non-root user
RUN useradd -m appuser
USER appuser

# Run application
CMD ["python", "src/main.py"]