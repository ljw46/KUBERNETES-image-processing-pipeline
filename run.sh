#!/bin/bash
#
# FULL DEPLOYMENT SCRIPT FOR REDPANDA/KUBERNETES ON MINIKUBE
# This script handles environment setup, building all 4 images,
# and deploying all 5 Kubernetes manifests.
#
# MUST be run from the root of your project directory.

set -e # Exit immediately if a command exits with a non-zero status.

# --- 1. ENVIRONMENT SETUP AND VERIFICATION ---
echo "--- 1. Setting Minikube Docker Environment ---"
# This command configures your shell to use the Docker daemon running inside Minikube.
# It is required so the images built in step 2 are accessible to Kubernetes.
eval $(minikube docker-env)

echo "--- 2. Verifying Minikube Node Status ---"
# Check the cluster is running and accessible using the guaranteed wrapper.
if minikube kubectl -- get nodes | grep " Ready"; then
    echo "✅ Minikube node is Ready."
else
    echo "❌ ERROR: Minikube node is not Ready. Please check 'minikube status'."
    exit 1
fi

# --- 2. IMAGE BUILDING AND LOADING ---
echo "--- 3. Building and Loading Custom Images into Minikube ---"
echo "--- (Images will be tagged 'latest') ---"

# Save the current directory to return after building
PROJECT_ROOT=$PWD

# 2.1 Build Redpanda Base Image (if custom Dockerfile is used)
echo "Building Redpanda base image..."
cd "$PROJECT_ROOT/redpanda"
docker build -t redpanda:latest .
cd "$PROJECT_ROOT"

# 2.2 Build GCP Storage Emulator Image
echo "Building GCP Storage Emulator image..."
cd "$PROJECT_ROOT/gcp-storage-emulator"
docker build -t gcp-storage-emulator:latest .
cd "$PROJECT_ROOT"

# 2.3 Build Image Producer (FastAPI) Image
echo "Building Image Producer (FastAPI) image..."
cd "$PROJECT_ROOT/image-producer-fastapi"
docker build -t image-producer-fastapi:latest .
cd "$PROJECT_ROOT"

# 2.4 Build Image Processor (Consumer) Image
echo "Building Image Processor (Consumer) image..."
cd "$PROJECT_ROOT/image-processor"
docker build -t image-processor:latest .
cd "$PROJECT_ROOT"

# 2.5 Build Redpanda Console Image
echo "Building Redpanda Console image..."
cd "$PROJECT_ROOT/redpanda_console"
docker build -t redpanda-console:latest .
cd "$PROJECT_ROOT"

echo "✅ All 5 images built and loaded successfully into Minikube's Docker daemon."


# --- 3. DEPLOYMENT OF MANIFESTS ---
echo "--- 4. Applying Kubernetes Manifests (Using 'minikube kubectl --') ---"

# 3.1 Deploy Redpanda Broker and Service
echo "Applying Redpanda Service..."
minikube kubectl -- apply -f redpanda/red-panda-service.yaml

# 3.2 Deploy GCP Storage Emulator
echo "Applying GCP Storage Emulator..."
minikube kubectl -- apply -f gcp-storage-emulator/gcp-storage-emulator.yaml

# 3.3 Deploy Producer and Consumer Services
echo "Applying Image Producer Service..."
minikube kubectl -- apply -f image-producer-fastapi/fastapi-image-producer.yaml
echo "Applying Image Processor Consumer..."
minikube kubectl -- apply -f image-processor/Image-processor-consumer.yaml

# 3.4 Deploy Redpanda Console
echo "Applying Redpanda Console..."
minikube kubectl -- apply -f redpanda_console/red-panda-console.yaml

echo "--- Deployment Complete! ---"

# --- 4. POST-DEPLOYMENT VERIFICATION ---
echo "--- 5. Verifying Pods (Wait a few minutes for them to become 'Running') ---"
minikube kubectl -- get pods -A

echo "--- Final Step: Accessing the Redpanda Console ---"
echo "To access the web console, use the following command after all Pods are Running:"
echo "minikube service -n default redpanda-console"

