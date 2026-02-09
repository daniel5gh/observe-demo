# RabbitMQ Event Tracing

This document explains how RabbitMQ internal events are captured and converted to OpenTelemetry traces.

## Overview

The system captures **two levels of RabbitMQ tracing**:

### 1. Application-Level Traces (Already Enabled)
- **Publish operations** - .NET API creates spans when publishing messages
- **Consume operations** - Python worker creates spans when consuming messages
- **Trace context propagation** - Trace IDs flow through message headers
- **End-to-end visibility** - See message flow from API → RabbitMQ → Worker

### 2. RabbitMQ Internal Event Traces (New)
- **Connection lifecycle** - When clients connect/disconnect
- **Channel operations** - When channels are created/closed
- **Queue operations** - When queues are declared/deleted
- **Consumer events** - When consumers start/stop
- **Exchange operations** - When exchanges are created/deleted
- **Binding operations** - When bindings are created/deleted

## Architecture

```
RabbitMQ Server
    │
    ├─ Application Operations (publish/consume)
    │   │
    │   ├─ .NET API (publish) ──────────┐
    │   │                                │
    │   └─ Python Worker (consume) ──────┤
    │                                    │
    │                                    ├─> ClickStack → HyperDX
    │                                    │
    └─ Internal Events                  │
        │                                │
        └─ amq.rabbitmq.event ───────────┤
            │                            │
            └─ RabbitMQ Tracer ──────────┘
                (converts to OTLP)
```

## How It Works

### RabbitMQ Event Exchange

RabbitMQ has a built-in topic exchange called `amq.rabbitmq.event` that publishes internal events:

- **Plugin:** Requires `rabbitmq_event_exchange` plugin (enabled automatically in docker-compose)
- Events are published with routing keys like `connection.created`, `queue.declared`, etc.
- Events contain JSON payloads with operation details
- No performance impact - events are published asynchronously

**Verify plugin is enabled:**
```bash
docker compose exec rabbitmq rabbitmq-plugins list | grep event_exchange
```

Should show:
```
[E*] rabbitmq_event_exchange
```

### RabbitMQ Tracer Service

The `rabbitmq-tracer` service:

1. **Connects** to RabbitMQ and binds to `amq.rabbitmq.event`
2. **Receives** internal events (connections, queues, consumers, etc.)
3. **Converts** each event to an OpenTelemetry span
4. **Exports** spans to ClickStack via OTLP
5. **Enriches** spans with event-specific attributes

## Event Types and Traces

### Connection Events

**Event:** `connection.created`
- **Span:** `rabbitmq.connection.created`
- **Attributes:**
  - `rabbitmq.connection.name` - Connection name
  - `rabbitmq.connection.peer_host` - Client IP
  - `rabbitmq.connection.peer_port` - Client port
  - `rabbitmq.connection.user` - Username
  - `rabbitmq.connection.vhost` - Virtual host

**Event:** `connection.closed`
- **Span:** `rabbitmq.connection.closed`
- Same attributes as connection.created

### Channel Events

**Event:** `channel.created`
- **Span:** `rabbitmq.channel.created`
- **Attributes:**
  - `rabbitmq.channel.number` - Channel number
  - `rabbitmq.channel.user` - User who created channel
  - `rabbitmq.channel.vhost` - Virtual host
  - `rabbitmq.channel.connection` - Parent connection name

**Event:** `channel.closed`
- **Span:** `rabbitmq.channel.closed`
- Same attributes as channel.created

### Queue Events

**Event:** `queue.declared` / `queue.created` / `queue.deleted`
- **Span:** `rabbitmq.queue.declared` / `created` / `deleted`
- **Attributes:**
  - `rabbitmq.queue.name` - Queue name
  - `rabbitmq.queue.vhost` - Virtual host
  - `rabbitmq.queue.durable` - Is queue durable?
  - `rabbitmq.queue.auto_delete` - Auto-delete enabled?

### Consumer Events

**Event:** `consumer.created` / `consumer.deleted`
- **Span:** `rabbitmq.consumer.created` / `deleted`
- **Attributes:**
  - `rabbitmq.consumer.tag` - Consumer tag
  - `rabbitmq.consumer.queue` - Queue name
  - `rabbitmq.consumer.channel` - Channel info

### Exchange Events

**Event:** `exchange.created` / `exchange.deleted`
- **Span:** `rabbitmq.exchange.created` / `deleted`
- **Attributes:**
  - `rabbitmq.exchange.name` - Exchange name
  - `rabbitmq.exchange.type` - Exchange type (topic, direct, fanout, etc.)
  - `rabbitmq.exchange.vhost` - Virtual host
  - `rabbitmq.exchange.durable` - Is exchange durable?

### Binding Events

**Event:** `binding.created` / `binding.deleted`
- **Span:** `rabbitmq.binding.created` / `deleted`
- **Attributes:**
  - `rabbitmq.binding.source` - Source exchange
  - `rabbitmq.binding.destination` - Destination queue/exchange
  - `rabbitmq.binding.routing_key` - Routing key
  - `rabbitmq.binding.vhost` - Virtual host

## Viewing Traces in HyperDX

### View All RabbitMQ Events

Search for spans from the `rabbitmq-events` service:

```
service.name:rabbitmq-events
```

### View Specific Event Types

**Connection events:**
```
rabbitmq.event.type:connection.created
rabbitmq.event.type:connection.closed
```

**Queue operations:**
```
rabbitmq.event.type:queue.*
```

**Consumer lifecycle:**
```
rabbitmq.event.type:consumer.created
rabbitmq.event.type:consumer.deleted
```

### Correlate with Application Traces

Find when your worker consumer started:

```
rabbitmq.consumer.queue:"order.processing" AND rabbitmq.event.type:consumer.created
```

See connection activity:

```
rabbitmq.connection.user:demo
```

## Use Cases

### 1. Debug Connection Issues

**Question:** Why did my worker disconnect?

**Query:**
```
service.name:rabbitmq-events AND rabbitmq.event.type:connection.closed
```

View the trace to see which connection closed and when.

### 2. Track Consumer Lifecycle

**Question:** When did my consumer start/stop?

**Query:**
```
rabbitmq.consumer.queue:"order.processing"
```

See `consumer.created` and `consumer.deleted` events.

### 3. Monitor Queue Creation

**Question:** What queues are being created dynamically?

**Query:**
```
rabbitmq.event.type:queue.declared
```

View all queue declaration events with queue names and properties.

### 4. Audit Configuration Changes

**Question:** Who created/deleted exchanges or bindings?

**Query:**
```
rabbitmq.event.type:exchange.created OR rabbitmq.event.type:binding.created
```

See all configuration changes with user attribution.

### 5. Correlate Events with Load Tests

During a load test, view:
- Connection spikes (`connection.created`)
- Channel creation patterns (`channel.created`)
- Consumer behavior (`consumer.created`)

Compare event traces with metrics:
```
# Connections created (traces)
service.name:rabbitmq-events AND rabbitmq.event.type:connection.created

# vs

# Active connections (metric)
rabbitmq_connections
```

## Example Trace Timeline

When the worker starts up, you'll see this sequence of events:

1. **`connection.created`** - Worker connects to RabbitMQ
2. **`channel.created`** - Worker creates a channel
3. **`exchange.declared`** - Worker declares "orders" exchange (if not exists)
4. **`queue.declared`** - Worker declares "order.processing" queue
5. **`binding.created`** - Worker binds queue to exchange with routing key
6. **`consumer.created`** - Worker starts consuming messages

When the worker stops:

1. **`consumer.deleted`** - Consumer stops
2. **`channel.closed`** - Channel closes
3. **`connection.closed`** - Connection closes

## Performance Considerations

### Overhead

- **RabbitMQ side:** Minimal - events are published asynchronously
- **Tracer side:** Low - simple JSON parsing and span creation
- **Network:** One event per RabbitMQ operation (connection, queue, etc.)

### Volume

Event volume depends on your workload:
- **Stable systems:** Low (only startup/shutdown events)
- **Dynamic systems:** Higher (frequent connections/disconnections)
- **Load tests:** Spike during test start/end

### Scaling

The tracer service:
- Runs as a single instance (one consumer)
- Events are lightweight and processed quickly
- Can be disabled without affecting application functionality

## Disabling Event Tracing

If you don't need RabbitMQ event traces, simply don't start the service:

```bash
# docker-compose.yml - comment out or remove:
# rabbitmq-tracer:
#   ...
```

Application-level traces (publish/consume) will still work.

## Troubleshooting

### No Events Appearing

**1. Check event exchange plugin is enabled:**
```bash
docker compose exec rabbitmq rabbitmq-plugins list | grep event_exchange
```

Should show `[E*] rabbitmq_event_exchange` (E = enabled, * = running).

If not enabled:
```bash
docker compose exec rabbitmq rabbitmq-plugins enable rabbitmq_event_exchange
docker compose restart rabbitmq
```

**2. Verify exchange exists:**
```bash
docker compose exec rabbitmq rabbitmqctl list_exchanges
```

Should see `amq.rabbitmq.event` in the list.

**3. Check tracer logs:**
```bash
docker compose logs rabbitmq-tracer
```

Should see:
```
Bound to event: connection.created
Bound to event: queue.declared
...
RabbitMQ event tracer started, waiting for events...
```

**4. Trigger an event manually:**
```bash
# Create a new connection (should generate connection.created event)
docker compose restart worker

# Check tracer received it
docker compose logs rabbitmq-tracer --tail 20
```

### Too Many Events

If events are noisy, filter in HyperDX:

```
# Only show queue and consumer events, ignore connections
rabbitmq.event.type:queue.* OR rabbitmq.event.type:consumer.*
```

Or modify `rabbitmq-tracer/main.py` to reduce `event_patterns` list.

### Events Not Exporting to ClickStack

**Check OTLP endpoint:**
```bash
docker compose logs rabbitmq-tracer | grep -i error
```

**Verify ClickStack is running:**
```bash
docker compose ps clickstack
```

## Reference

- RabbitMQ Event Exchange: https://www.rabbitmq.com/event-exchange.html
- OpenTelemetry Tracing: https://opentelemetry.io/docs/concepts/signals/traces/
- List of all RabbitMQ events: See RabbitMQ documentation for complete event list
