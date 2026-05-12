# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Set work directory
WORKDIR /app

# Install system dependencies (needed for some ML packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create the instance folder for SQLite
RUN mkdir -p backend/instance && chmod 777 backend/instance

# Seed the database during build (pre-populates movies and ratings)
RUN python backend/scripts/seed_movielens.py

# Expose the port Hugging Face expects
EXPOSE 7860

# Start the application using Gunicorn on port 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]
