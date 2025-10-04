# Use a base image that already contains the necessary GCS emulator components.
# The 'oittaa/gcp-storage-emulator' is a popular community-maintained image 
# based on the Java library that mimics the GCS API.
# We'll base our custom image on it for consistency, though we don't strictly
# need to modify it unless specific configurations were required.
FROM oittaa/gcp-storage-emulator:latest

# The emulator defaults to running on port 9023, which we will expose.
EXPOSE 9023

# The default entrypoint starts the emulator.
# ENTRYPOINT ["java", "-jar", "gcs-emulator.jar", "--port", "9023"]
