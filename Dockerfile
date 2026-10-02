FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    liboqs \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY pqc_secure ./pqc_secure

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[pqc]"

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "pqc_secure.main:app", "--host", "0.0.0.0", "--port", "8000"]
