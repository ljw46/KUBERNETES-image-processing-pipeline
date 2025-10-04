# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies first for better caching
# Your dependencies are: aiokafka, pillow (for PIL)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the background worker application code
COPY image-service.py .

# Command to run the application when the container starts
CMD ["python", "image-service.py"]