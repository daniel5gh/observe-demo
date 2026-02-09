# observe-demo

Multi-service observability demo with distributed tracing, metrics, and structured logging across .NET, Python, and React — powered by ClickStack (ClickHouse + HyperDX).

## Architecture

```
React (browser) ──HTTP──▶ .NET API ──HTTP──▶ Python FastAPI (/enrich)
                           │    │
                      Postgres  RabbitMQ ──▶ Python worker (consumer)

All services ──OTLP──▶ ClickStack (collector + ClickHouse + HyperDX)
```

## Quick Start

```bash
docker compose up --build
```

Wait for all services to become healthy (first build takes a few minutes).

## URLs

| Service             | URL                          | Notes              |
|---------------------|------------------------------|---------------------|
| Frontend            | http://localhost:3000         | Order form + list   |
| .NET API            | http://localhost:5050         | REST API            |
| HyperDX             | http://localhost:8080         | Traces, logs, metrics |
| RabbitMQ Management | http://localhost:15672        | demo / demo         |
| RabbitMQ Prometheus | http://localhost:15692/metrics | Raw Prometheus metrics |
| Python Worker API   | http://localhost:8000/health  | Health check        |
| Locust Load Gen     | http://localhost:8089         | Load testing UI (optional) |

## Usage

1. Open http://localhost:3000
2. Submit an order (e.g., Customer: "Alice", Product: "widget", Qty: 2)
3. Open http://localhost:8080 (HyperDX) to see the distributed trace spanning:
   - React → .NET API → Python enrichment → Postgres → RabbitMQ → Python worker

## Error Scenario

Submit an order with product **"error"** to trigger an error-annotated trace. The .NET API will throw an exception, and HyperDX will show the error span with status code and exception details.

Submit an order with product **"worker error"** to trigger an error in the worker processing, showing error propagation through the queue.

## Load Testing

Start the Locust load generator to simulate traffic and observe system behavior under load:

```bash
# Start with web UI (configure load in browser)
docker compose --profile loadgen up locust

# Or run headless with specific load
export LOCUST_USERS=50
export LOCUST_SPAWN_RATE=5
export LOCUST_HEADLESS=true
docker compose --profile loadgen up locust
```

Access the Locust web UI at http://localhost:8089 to control the load test and view statistics.

**Note:** The load generator automatically includes error injection (~10% of orders) using "error" and "worker error" products to demonstrate error tracking and distributed tracing of failures.

See `loadgen/README.md` for detailed configuration options and examples.

### Observing Load Test Results

While the load test runs:
1. Open HyperDX at http://localhost:8080
2. View request latency distributions across services
3. Monitor custom metrics:
   - `orders.created` - Total orders created (display as gauge or rate)
   - `orders.errors` - Order creation errors by type
   - `order.processing.duration` - Worker processing times
4. Analyze trace waterfalls to identify bottlenecks

#### Key Metrics

The system exports several custom metrics for monitoring:

- **`orders.created`** (Counter) - Total orders created, with attributes:
  - `product` - Product name
  - `quantity` - Order quantity
  - Can be displayed as a gauge showing cumulative orders or as a rate (orders/min)

- **`orders.errors`** (Counter) - Order creation errors, with attributes:
  - `product` - Product that caused the error
  - `error.type` - Type of error (validation_error, simulated_error)

- **`order.processing.duration`** (Histogram) - Worker processing time in seconds, with attributes:
  - `order.product` - Product name
  - `status` - success or error

- **RabbitMQ Metrics** (Infrastructure) - Automatically scraped from RabbitMQ Prometheus endpoint:
  - `rabbitmq_queue_messages` - Messages in queue (gauge)
  - `rabbitmq_queue_messages_ready` - Messages ready for delivery
  - `rabbitmq_queue_messages_unacknowledged` - Messages delivered but not ack'd
  - `rabbitmq_queue_consumers` - Number of consumers per queue
  - `rabbitmq_channel_messages_published_total` - Total messages published
  - `rabbitmq_channel_messages_confirmed_total` - Total messages confirmed
  - Many more available at http://localhost:15692/metrics

### Configuring Worker Processing Time

The worker simulates realistic processing with random delays. Configure via environment variables:

```bash
# Set minimum and maximum processing time (seconds)
export WORKER_MIN_WAIT=0.5
export WORKER_MAX_WAIT=3.0
docker compose up worker
```

This allows you to simulate different processing patterns and observe their impact on system performance.

## RabbitMQ Metrics

RabbitMQ infrastructure metrics are automatically collected and displayed in HyperDX alongside application metrics:

- **Queue depth** (`rabbitmq_queue_messages`) - Total messages in queue
- **Ready messages** (`rabbitmq_queue_messages_ready`) - Messages waiting for delivery
- **Unacknowledged** (`rabbitmq_queue_messages_unacknowledged`) - Messages being processed
- **Consumer count** (`rabbitmq_queue_consumers`) - Active consumers
- **Publish rate** (`rabbitmq_channel_messages_published_total`) - Messages published over time

This enables you to:
1. Monitor queue backlog during load tests
2. Correlate queue depth with processing time
3. Detect consumer failures (consumer count drops to 0)
4. Track message flow through the system

See `RABBITMQ_METRICS.md` for complete metrics list and dashboard examples.

## Services

- **frontend** — Vite + React + TypeScript with OTel browser SDK
- **api** — .NET 8 Minimal API with Dapper, Npgsql, RabbitMQ.Client 7.x
- **worker** — Python FastAPI (/enrich endpoint) + aio-pika RabbitMQ consumer with processing time metrics
- **postgres** — Order storage
- **rabbitmq** — Message broker for order events with Prometheus metrics enabled
- **clickstack** — All-in-one observability backend (OTel Collector + ClickHouse + HyperDX)
- **otel-collector** — Scrapes RabbitMQ Prometheus metrics and forwards to ClickStack
- **locust** (optional) — Load testing tool to simulate user traffic and observe system behavior under load

## Teardown

```bash
docker compose down -v
```
