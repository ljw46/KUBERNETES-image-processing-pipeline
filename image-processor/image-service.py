import asyncio
import os 
import io

from PIL import Image, ImageOps
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

# Import the Google Cloud Storage client library
from google.cloud import storage

# --- Configuration ---
# Use the Kubernetes Service name (redpanda-service) and the internal port (29092)
redpanda_server = os.environ.get("REDPANDA_BROKERS", "redpanda-service:29092")
request_topic = "image-request"
reply_topic = "image-reply"

# Environment variables for GCS setup
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "image-pipeline-bucket")
# The Redpanda message now contains the object key (path) inside the bucket.

def _get_gcs_client():
    """Initializes and returns the GCS client. Handles local emulator host setting."""
    # The client automatically uses the GOOGLE_APPLICATION_CREDENTIALS for prod
    # and STORAGE_EMULATOR_HOST environment variable for local testing.
    return storage.Client()

async def read_requests():
    """Listens to the image-request topic for GCS object keys."""
    consumer = AIOKafkaConsumer(
        request_topic,
        bootstrap_servers=redpanda_server,
        group_id="image-process-group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            # The message value is now the GCS object key (path/filename)
            object_key = msg.value.decode('utf-8')
            print(f"Received request for GCS object: {object_key}")
            await process_image(object_key)
    finally:
        await consumer.stop()

async def send_to_topic(topic, message):
    """Sends a message (GCS object key) to a Redpanda topic."""
    producer = AIOKafkaProducer(bootstrap_servers=redpanda_server)
    await producer.start()
    try:
        await producer.send_and_wait(topic, message.encode('utf-8'))
    finally:
        await producer.stop()

async def process_image(object_key):
    """Downloads image from GCS, processes it, and uploads the result."""
    gcs_client = _get_gcs_client()
    bucket = gcs_client.bucket(GCS_BUCKET_NAME)

    try:
        # 1. Download the raw image data from GCS into memory (io.BytesIO)
        source_blob = bucket.blob(object_key)
        
        # Check if the file exists before attempting to download
        if not source_blob.exists():
             print(f"Error: Object key '{object_key}' not found in bucket '{GCS_BUCKET_NAME}'.")
             return

        print(f"Downloading raw image from GCS: {object_key}")
        image_bytes = source_blob.download_as_bytes()
        
        # 2. Process the image using PIL
        with Image.open(io.BytesIO(image_bytes)) as img:
            grayscale = ImageOps.grayscale(img)
            
            # Determine the new filename (and GCS key)
            original_filename = os.path.basename(object_key)
            new_filename = f"processed_{original_filename}"
            
            # 3. Save the processed image to an in-memory buffer
            output_buffer = io.BytesIO()
            # Save the image into the buffer, respecting its original format
            grayscale.save(output_buffer, format=img.format or 'JPEG') 
            output_buffer.seek(0)
            
            # 4. Upload the processed image buffer back to GCS
            dest_blob = bucket.blob(new_filename)
            dest_blob.upload_from_file(output_buffer, content_type=source_blob.content_type)
            
            print(f"Processed and uploaded: {new_filename}")
            
            # 5. Send the new GCS object key (path) to the reply topic
            await send_to_topic(reply_topic, new_filename)
            
    except Exception as e:
        print(f"Error processing GCS object {object_key}: {e}")

if __name__ == "__main__":
    print("Starting image service...")
    asyncio.run(read_requests())
