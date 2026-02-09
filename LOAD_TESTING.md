# Load Testing and Performance Observability

This document describes the load testing capabilities and performance metrics added to the observe-demo project.

## Overview

The project now includes:
1. **Locust-based load generator** - Simulate realistic user traffic
2. **Worker processing time metrics** - Track order processing duration via OpenTelemetry
3. **Configurable processing delays** - Simulate various system loads and processing patterns

## Quick Start

### 1. Start the Core System

```bash
docker compose up --build
```

Wait for all services to be healthy.

### 2. Start the Load Generator

```bash
# Interactive mode with web UI
docker compose --profile loadgen up locust
```

Then open http://localhost:8089 in your browser to configure and start the load test.

### 3. Monitor in HyperDX

Open http://localhost:8080 to observe:
- Request latency distributions
- The `order.processing.duration` histogram metric
- Distributed traces under load
- Queue depth and processing patterns

## Configuration Options

### Load Generator Settings

Configure via environment variables in `.env` or export them before starting:

```bash
# Number of concurrent users
export LOCUST_USERS=50

# Users spawned per second
export LOCUST_SPAWN_RATE=5

# Run without web UI (auto-start)
export LOCUST_HEADLESS=true

# Auto-stop after duration (e.g., 5m, 1h)
export LOCUST_RUN_TIME=10m

# Start the load test
docker compose --profile loadgen up locust
```

### Worker Processing Time

Control how long the worker takes to process each order:

```bash
# Minimum processing time (seconds)
export WORKER_MIN_WAIT=0.5

# Maximum processing time (seconds)
export WORKER_MAX_WAIT=3.0

# Restart the worker with new settings
docker compose up -d worker
```

## Load Test Scenarios

The load generator simulates three types of operations with weighted distribution and automatic error injection:

| Operation | Weight | Endpoint | Description |
|-----------|--------|----------|-------------|
| Create Order | 10 | `POST /orders` | Most common - creates new orders. **Includes automatic error injection:** 90% normal products, 5% "error" (API error), 5% "worker error" (async error) |
| List Orders | 3 | `GET /orders` | Moderate - fetches all orders |
| Get Order Detail | 1 | `GET /orders/{id}` | Rare - fetches specific order |

### Error Injection for Observability

The load generator automatically triggers errors to demonstrate error tracking:

- **API Errors (5%)** - Product "error" triggers an exception in the .NET API
  - Demonstrates error spans in distributed traces
  - Increments `orders.errors{error.type="simulated_error"}` counter
  - Shows error propagation and exception handling

- **Worker Errors (5%)** - Product "worker error" triggers an exception in the Python worker
  - Order creation succeeds, but background processing fails
  - Demonstrates async error tracking across message queues
  - Shows error correlation between API and worker services

This ~10% error rate helps you observe:
- Error rates in dashboards (`orders.errors` metric)
- Error traces in HyperDX (search for `status:error`)
- Impact of errors on system performance
- Error recovery and resilience patterns

## Observability Metrics

### Key Metrics to Monitor

1. **`orders.created`** (Counter → display as Gauge)
   - Tracks total number of orders created
   - Attributes:
     - `product` - Product name
     - `quantity` - Order quantity
   - Use in HyperDX: Rate per minute or cumulative gauge
   - Perfect for dashboards showing order volume over time

2. **`orders.errors`** (Counter)
   - Tracks order creation errors
   - Attributes:
     - `product` - Product that caused error
     - `error.type` - "validation_error" or "simulated_error"
   - Use to monitor error rates during load tests

3. **`order.processing.duration`** (Histogram)
   - Tracks worker processing time in seconds
   - Attributes:
     - `order.product` - Product name
     - `status` - "success" or "error"
   - View in HyperDX metrics explorer

4. **Request Latency** (Auto-instrumented)
   - HTTP request duration across all services
   - Available in traces and metrics

5. **RabbitMQ Infrastructure Metrics** (Auto-scraped)
   - `rabbitmq_queue_messages` - Total messages in queue
   - `rabbitmq_queue_messages_ready` - Messages ready for delivery
   - `rabbitmq_queue_messages_unacknowledged` - Delivered but not ack'd
   - `rabbitmq_queue_consumers` - Active consumers
   - `rabbitmq_channel_messages_published_total` - Total published
   - View in HyperDX alongside application metrics
   - Also available at http://localhost:15672 (management UI)

### Analyzing Performance

1. **Baseline Test** (Low Load)
   ```bash
   export LOCUST_USERS=5
   export LOCUST_SPAWN_RATE=1
   docker compose --profile loadgen up locust
   ```
   Establish baseline latency and throughput.

2. **Performance Test** (Medium Load)
   ```bash
   export LOCUST_USERS=50
   export LOCUST_SPAWN_RATE=5
   docker compose --profile loadgen up locust
   ```
   Identify when performance starts degrading.

3. **Stress Test** (High Load)
   ```bash
   export LOCUST_USERS=200
   export LOCUST_SPAWN_RATE=10
   docker compose --profile loadgen up locust
   ```
   Find system breaking points.

### HyperDX Queries

Example queries to run in HyperDX:

```
# Total orders created (as gauge)
orders.created | sum()

# Orders created rate (per minute)
orders.created | rate(1m)

# Orders by product (as gauge)
orders.created{product=*} | sum() by product

# Error rate
orders.errors | rate(1m)

# P95 processing time by product
order.processing.duration{product=*} | percentile(95)

# Error rate in worker processing
order.processing.duration{status="error"} | count()

# Request rate by endpoint
http.server.request.duration{endpoint=*} | rate(1m)

# RabbitMQ queue depth (messages waiting)
rabbitmq_queue_messages_ready{queue="order.processing"} | last()

# RabbitMQ message publish rate
rabbitmq_channel_messages_published_total | rate(1m)

# RabbitMQ consumer count
rabbitmq_queue_consumers{queue="order.processing"} | last()

# Unacknowledged messages (processing in progress)
rabbitmq_queue_messages_unacknowledged{queue="order.processing"} | last()
```

## Example Workflows

### Workflow 1: Compare Processing Times

```bash
# Test with fast processing
export WORKER_MIN_WAIT=0.1
export WORKER_MAX_WAIT=0.5
docker compose up -d worker

# Run load test for 5 minutes
export LOCUST_USERS=30
export LOCUST_SPAWN_RATE=5
export LOCUST_HEADLESS=true
export LOCUST_RUN_TIME=5m
docker compose --profile loadgen up locust

# Wait for test to complete, then change worker config
export WORKER_MIN_WAIT=2.0
export WORKER_MAX_WAIT=5.0
docker compose up -d worker

# Run another test
docker compose --profile loadgen up locust

# Compare metrics in HyperDX
```

### Workflow 2: Identify Bottlenecks

```bash
# Start with light load
export LOCUST_USERS=10
docker compose --profile loadgen up locust

# Gradually increase load in the web UI
# Watch HyperDX for:
# - Increasing latency
# - Growing queue depth
# - Error rates
# - Processing time distribution changes
```

### Workflow 3: Error Impact Analysis

```bash
# The load generator automatically injects errors (~10% of orders)
# Run load test
export LOCUST_USERS=50
docker compose --profile loadgen up locust

# In HyperDX, observe:

# 1. Error rate over time
orders.errors | rate(1m)

# 2. Error breakdown by type
orders.errors{error.type=*} | sum() by error.type

# 3. Compare successful vs error processing times
order.processing.duration{status="success"} | percentile(95)
order.processing.duration{status="error"} | percentile(95)

# 4. View error traces
# - Search for "status:error" in HyperDX traces
# - See full error propagation through services
# - Compare error spans with successful request spans

# 5. System impact
# - Does error rate correlate with increased latency?
# - How does queue depth change during error bursts?
# - Monitor rabbitmq_queue_messages_ready during high error periods
```

## Stopping Load Tests

```bash
# Stop the load generator
docker compose --profile loadgen down

# Or just Ctrl+C if running in foreground
```

## Troubleshooting

### High Memory Usage

If you see high memory usage:
- Reduce `LOCUST_USERS`
- Increase `LOCUST_SPAWN_RATE` (gradual ramp-up)
- Check RabbitMQ queue depth - may need to scale workers

### Connection Errors

If Locust shows connection errors:
- Ensure all services are healthy: `docker compose ps`
- Check API logs: `docker compose logs api`
- Verify network connectivity: `docker compose exec locust ping api`

### Metrics Not Showing

If metrics don't appear in HyperDX:
- Check OTEL_AUTHORIZATION is set correctly
- Verify clickstack is running: `docker compose logs clickstack`
- Check worker logs for export errors: `docker compose logs worker`

## Further Reading

- Locust documentation: https://docs.locust.io/
- OpenTelemetry metrics: https://opentelemetry.io/docs/concepts/signals/metrics/
- See `loadgen/README.md` for detailed load generator configuration
