import asyncio
import os 
import time
from uuid import uuid4

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from google.cloud import storage # New Import

# --- Configuration ---
# Use the Kubernetes Service name (redpanda-service) and the internal port (29092)
redpanda_server = os.environ.get("REDPANDA_BROKERS", "redpanda-service:29092")
request_topic = "image-request"
reply_topic = "image-reply"

# GCS Configuration
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "image-pipeline-bucket")


def _get_gcs_client():
    """Initializes and returns the GCS client. Automatically uses STORAGE_EMULATOR_HOST if set."""
    # This automatically handles credentials for prod and the emulator host for local dev.
    return storage.Client()


# Startup event handler
@asynccontextmanager
async def startup(app):
    """Initializes and cleans up connections for Redpanda."""
    print("Starting Redpanda producer and consumer...")
    app.producer = AIOKafkaProducer(bootstrap_servers=[redpanda_server])
    await app.producer.start()
    
    app.consumer = AIOKafkaConsumer(
        reply_topic,
        bootstrap_servers=[redpanda_server],
        group_id="image-reply-group"
    )
    await app.consumer.start()

    try:
        yield
    finally:
        print("Stopping Redpanda producer and consumer...")
        await app.producer.stop()
        await app.consumer.stop()

app = FastAPI(lifespan=startup)

# Mount the static directory to serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Redirect root URL to the static index.html
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# Endpoint to upload an image
@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    """
    Uploads the file to GCS and sends the GCS object key to the Redpanda request topic.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    gcs_client = _get_gcs_client()
    bucket = gcs_client.bucket(GCS_BUCKET_NAME)

    # 1. Generate a unique key/path for the GCS object
    timestamp = int(time.time())
    unique_id = uuid4().hex[:8]
    # Use original filename extension or default to 'bin'
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    
    # Define the GCS object key (path in the bucket)
    gcs_object_key = f"raw/{timestamp}-{unique_id}.{file_extension}"

    try:
        # 2. Read the uploaded file contents into memory
        file_contents = await file.read()
        
        # 3. Create a new Blob and upload the data directly from memory
        blob = bucket.blob(gcs_object_key)
        blob.upload_from_string(
            file_contents,
            content_type=file.content_type
        )
        print(f"Uploaded raw file to GCS key: {gcs_object_key}")

        # 4. Send the GCS key to the Redpanda image-request topic
        # The Redpanda message is now the GCS object key, not the local filename.
        await app.producer.send(request_topic, gcs_object_key.encode('utf-8'))

        return JSONResponse(content={
            "message": "File uploaded and processing request sent.",
            "original_file_key": gcs_object_key,
            "processed_file_key_expected": f"processed_{os.path.basename(gcs_object_key)}",
            "bucket": GCS_BUCKET_NAME
        })

    except Exception as e:
        print(f"Error during GCS upload or Kafka send: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during upload: {str(e)}")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async def send_message_to_websocket(msg):
        # The message value is now the GCS object key of the processed image
        await websocket.send_text(msg.value.decode('utf-8'))

    async def consume_from_topic(topic, callback):
        print(f"Consuming from {topic}")
        async for msg in app.consumer:
            print(f"Received processed GCS key: {msg.value.decode('utf-8')}")
            await callback(msg)

    # Start consuming
    asyncio.create_task(consume_from_topic(reply_topic, send_message_to_websocket))

    # Keep the connection open
    while True:
        await asyncio.sleep(10)
