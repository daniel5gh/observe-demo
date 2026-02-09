# Load Generator

This directory contains a Locust-based load generator for testing the observe-demo application under various load conditions.

## Quick Start

### Start with Web UI (Interactive)

```bash
# Start the load generator service
docker compose --profile loadgen up locust

# Open http://localhost:8089 in your browser
# Configure number of users and spawn rate in the UI
# Click "Start swarming" to begin the load test
```

### Start in Headless Mode (Automated)

```bash
# Set environment variables
export LOCUST_USERS=50
export LOCUST_SPAWN_RATE=5
export LOCUST_HEADLESS=true
export LOCUST_RUN_TIME=5m

# Start the load test
docker compose --profile loadgen up locust
```

## Configuration

Configure the load generator using environment variables in `.env` or by exporting them:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCUST_HOST` | Target API host | `http://api:8080` |
| `LOCUST_USERS` | Number of concurrent users | `10` |
| `LOCUST_SPAWN_RATE` | Users spawned per second | `2` |
| `LOCUST_HEADLESS` | Run without web UI | `false` |
| `LOCUST_RUN_TIME` | Auto-stop after duration (e.g., `5m`, `1h`) | (none) |

## Load Test Scenarios

The load generator simulates realistic user behavior with weighted tasks:

### Tasks

1. **Create Order** (Weight: 10)
   - `POST /orders`
   - Creates orders with random products and quantities
   - Most common operation

2. **List Orders** (Weight: 3)
   - `GET /orders`
   - Fetches all orders
   - Moderate frequency

3. **Get Order Detail** (Weight: 1)
   - `GET /orders/{id}`
   - Fetches a specific order by ID
   - Least common operation
   - Some requests will get 404 (expected behavior)

### Traffic Pattern

- Wait time between tasks: 1-3 seconds per user
- Simulates realistic user behavior with pauses

## Observability

When running load tests, you can observe:

1. **Request latency distribution** in HyperDX traces
2. **Queue processing metrics** showing worker performance under load
3. **Processing time histograms** for order processing
4. **System behavior** under various load patterns

Access HyperDX dashboard at http://localhost:8080 while the load test is running.

## Examples

### Light Load (Development Testing)

```bash
export LOCUST_USERS=5
export LOCUST_SPAWN_RATE=1
docker compose --profile loadgen up locust
```

### Medium Load (Performance Testing)

```bash
export LOCUST_USERS=50
export LOCUST_SPAWN_RATE=5
docker compose --profile loadgen up locust
```

### Heavy Load (Stress Testing)

```bash
export LOCUST_USERS=200
export LOCUST_SPAWN_RATE=10
docker compose --profile loadgen up locust
```

### Automated Test Run

```bash
# Run for 10 minutes with 100 users
export LOCUST_USERS=100
export LOCUST_SPAWN_RATE=10
export LOCUST_HEADLESS=true
export LOCUST_RUN_TIME=10m
docker compose --profile loadgen up locust
```

## Stopping the Load Generator

Press `Ctrl+C` or run:

```bash
docker compose --profile loadgen down
```
