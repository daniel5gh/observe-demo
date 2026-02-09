FROM python:3.11-slim

WORKDIR /loadgen

# Install Locust
RUN pip install --no-cache-dir locust==2.31.8

# Copy the locustfile
COPY locustfile.py .

# Expose Locust web UI port
EXPOSE 8089

# Default command - can be overridden in docker-compose
CMD ["locust"]
