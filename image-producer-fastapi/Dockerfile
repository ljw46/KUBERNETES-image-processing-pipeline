# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy and install dependencies
# Note: Paths here are relative to the root build context ('.')
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application code and related files
COPY server.py .
COPY static ./static

# Expose the port
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]