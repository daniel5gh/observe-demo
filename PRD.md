# observe-demo — Product Requirements Document

## Overview

A hands-on demo of modern observability, built for internal team education. It showcases distributed tracing, metrics, and structured logging across .NET, Python, and React services — all containerized and orchestrated through Docker Compose.

The observability stack is powered by **ClickStack** (ClickHouse + OpenTelemetry Collector + HyperDX dashboard) via a single all-in-one container.

## Goals

- Demonstrate end-to-end distributed tracing from frontend to infrastructure
- Show traces following requests across HTTP calls, into the database, and through async message queues
- Provide a realistic multi-service architecture that a team can run with `docker compose up`
- Serve as a teaching tool for engineers learning OpenTelemetry concepts

## Architecture

```
┌────────────┐     HTTP      ┌────────────┐     HTTP      ┌────────────┐
│   React    │ ──────────▶   │  .NET API  │ ──────────▶   │  Python    │
│  Frontend  │               │  (Web API) │               │  (FastAPI) │
└────────────┘               └─────┬──┬───┘               └─────┬──────┘
                                   │  │                         │
                              write│  │publish             consume│
                                   ▼  ▼                         ▼
                            ┌──────────┐  ┌───────────┐   ┌──────────┐
                            │ Postgres │  │ RabbitMQ  │──▶│  Python  │
                            │          │  │           │   │ (worker) │
                            └──────────┘  └───────────┘   └──────────┘

                    All services export OTLP ──▶ ┌──────────────────┐
                                                 │   ClickStack     │
                                                 │  (collector +    │
                                                 │   ClickHouse +   │
                                                 │   HyperDX)       │
                                                 └──────────────────┘
```

## Services

### 1. React Frontend
- **Purpose:** Minimal UI to submit orders and view status
- **Tech:** React (functional, minimal styling)
- **Observability:** Browser-side OpenTelemetry traces for HTTP requests, propagating trace context to the backend
- **Container:** Nginx serving the built static assets

### 2. .NET Web API
- **Purpose:** Core backend — validates orders, persists to Postgres, calls Python service via HTTP for enrichment, publishes events to RabbitMQ
- **Tech:** .NET 8, ASP.NET Core Web API
- **Observability:**
  - Distributed tracing (HTTP in/out, DB queries, RabbitMQ publish)
  - Metrics (request duration, order counts)
  - Structured logging correlated with trace IDs
- **Endpoints:**
  - `POST /orders` — create an order
  - `GET /orders` — list orders
  - `GET /orders/{id}` — get order detail

### 3. Python FastAPI Service
- **Purpose:** Called by .NET for order enrichment (e.g., pricing/validation); also runs a RabbitMQ consumer worker that processes order events asynchronously
- **Tech:** Python, FastAPI, pika (RabbitMQ client)
- **Observability:**
  - Distributed tracing (HTTP in, RabbitMQ consume, DB reads if needed)
  - Structured logging correlated with trace IDs
- **Endpoints:**
  - `POST /enrich` — enrich/validate an order (called by .NET)
- **Worker:** Consumes `order.created` messages from RabbitMQ, performs background processing (e.g., send notification, update status)

### 4. PostgreSQL
- **Purpose:** Persistent storage for orders
- **Tech:** PostgreSQL (official Docker image)
- **Observability:** DB query tracing via instrumented clients in .NET and Python

### 5. RabbitMQ
- **Purpose:** Message broker for async workflows
- **Tech:** RabbitMQ (official Docker image with management plugin)
- **Observability:** Publish/consume spans with trace context propagation across the message boundary

### 6. ClickStack (Observability Backend)
- **Image:** `clickhouse/clickstack-all-in-one:2.9.0`
- **Purpose:** All-in-one observability backend
- **Provides:**
  - OpenTelemetry Collector on port **4317** (OTLP gRPC)
  - ClickHouse for telemetry storage
  - HyperDX dashboard for exploring traces, metrics, and logs
- **Config:** All application services point their OTLP exporter to `clickstack:4317`

## Demo Domain: Order Processing

A simple e-commerce-style order flow that touches every component:

1. **User submits an order** via the React frontend
2. **React** sends `POST /orders` to the .NET API (trace context propagated via HTTP headers)
3. **.NET API** validates the order, calls **Python FastAPI** at `POST /enrich` for enrichment
4. **.NET API** persists the order to **Postgres** (DB query traced)
5. **.NET API** publishes an `order.created` event to **RabbitMQ** (trace context injected into message headers)
6. **Python worker** consumes the event from RabbitMQ (trace context extracted, continuing the distributed trace)
7. **Python worker** performs background processing (e.g., marks order as confirmed)
8. The full trace — from browser click to background worker — is visible in **HyperDX**

## Key Observability Scenarios

| Scenario | What it demonstrates |
|---|---|
| **Distributed trace across HTTP** | React → .NET → Python, full waterfall in HyperDX |
| **Trace across RabbitMQ** | Trace context propagation through async messaging |
| **Database query tracing** | SQL queries visible as spans within the parent trace |
| **Error propagation** | Intentional error path (e.g., invalid order) shows error spans across services |
| **Latency metrics** | Request duration histograms per endpoint |
| **Structured logging** | Logs correlated with trace/span IDs for cross-referencing |

## Technical Decisions

- **Single `docker-compose.yml`** at project root — `docker compose up` runs everything
- **No separate OTel Collector** — ClickStack includes one at port 4317
- **No separate dashboard** — HyperDX is included in ClickStack
- **OTLP gRPC** as the telemetry export protocol for all services
- **Minimal frontend** — focus is on observability, not UI polish
- **.NET 8 LTS** for the API service

## Project Structure

```
observe-demo/
├── docker-compose.yml
├── frontend/              # React app
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── api/                   # .NET 8 Web API
│   ├── Dockerfile
│   └── Api/
├── worker/                # Python FastAPI + RabbitMQ consumer
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
├── PRD.md
└── README.md
```

## Success Criteria

- `docker compose up` brings up all services with no manual configuration
- Submitting an order in the React UI produces a full distributed trace visible in HyperDX
- The trace spans across: React → .NET API → Python FastAPI → Postgres → RabbitMQ → Python worker
- Error scenarios produce error-annotated traces
- Structured logs in all services include trace/span IDs
