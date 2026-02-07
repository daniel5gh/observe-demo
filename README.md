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
| Python Worker API   | http://localhost:8000/health  | Health check        |

## Usage

1. Open http://localhost:3000
2. Submit an order (e.g., Customer: "Alice", Product: "widget", Qty: 2)
3. Open http://localhost:8080 (HyperDX) to see the distributed trace spanning:
   - React → .NET API → Python enrichment → Postgres → RabbitMQ → Python worker

## Error Scenario

Submit an order with product **"error"** to trigger an error-annotated trace. The .NET API will throw an exception, and HyperDX will show the error span with status code and exception details.

## Services

- **frontend** — Vite + React + TypeScript with OTel browser SDK
- **api** — .NET 8 Minimal API with Dapper, Npgsql, RabbitMQ.Client 7.x
- **worker** — Python FastAPI (/enrich endpoint) + aio-pika RabbitMQ consumer
- **postgres** — Order storage
- **rabbitmq** — Message broker for order events
- **clickstack** — All-in-one observability backend (OTel Collector + ClickHouse + HyperDX)

## Teardown

```bash
docker compose down -v
```
