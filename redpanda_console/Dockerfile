# Dockerfile for the Redpanda Console Web UI
# We use the official image provided by Redpanda Data.
FROM docker.redpanda.com/redpandadata/console:latest

# The Console image is designed to run immediately.
# Configuration is handled via environment variables (like KAFKA_BROKERS)
# which are defined in your Kubernetes Deployment YAML.

# The UI exposes port 8080.
EXPOSE 8080

# No further customization is typically required here.
