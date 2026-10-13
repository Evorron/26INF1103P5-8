# Python runtime
FROM python:3.11-slim

# Set working directory in the Docker container
WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy source code (Non-essential files specified in ".dockerignore")
COPY . .

# Script execution
CMD ["python", "main.py"]