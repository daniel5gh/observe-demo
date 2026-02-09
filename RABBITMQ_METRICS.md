# RabbitMQ Metrics Integration

This document explains how RabbitMQ metrics are collected and displayed alongside application metrics in HyperDX.

## Architecture

```
RabbitMQ (port 15692)
    │
    │ Prometheus metrics endpoint
    │
    ▼
OpenTelemetry Collector
    │
    │ Scrapes every 15s
    │ Converts to OTLP format
    │ Adds service.name=rabbitmq
    │
    ▼
ClickStack (port 4317)
    │
    │ Stores in ClickHouse
    │
    ▼
HyperDX Dashboard
    │
    └─ View alongside app metrics
```

## How It Works

1. **RabbitMQ Prometheus Plugin** - Enabled on startup, exposes metrics on port 15692
2. **OpenTelemetry Collector** - Dedicated service that scrapes RabbitMQ metrics every 15 seconds
3. **OTLP Export** - Collector converts Prometheus metrics to OTLP and forwards to ClickStack
4. **Unified Dashboard** - All metrics (app + RabbitMQ) visible in HyperDX

## Available Metrics

### Queue Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rabbitmq_queue_messages` | Gauge | Total messages in queue |
| `rabbitmq_queue_messages_ready` | Gauge | Messages ready for delivery |
| `rabbitmq_queue_messages_unacknowledged` | Gauge | Messages delivered but not acknowledged |
| `rabbitmq_queue_consumers` | Gauge | Number of active consumers |
| `rabbitmq_queue_consumer_utilisation` | Gauge | Consumer utilization (0-1) |

### Channel Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rabbitmq_channel_messages_published_total` | Counter | Total messages published |
| `rabbitmq_channel_messages_confirmed_total` | Counter | Total messages confirmed |
| `rabbitmq_channel_messages_unroutable_dropped_total` | Counter | Unroutable messages dropped |
| `rabbitmq_channel_messages_unroutable_returned_total` | Counter | Unroutable messages returned |

### Connection Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rabbitmq_connections` | Gauge | Number of active connections |
| `rabbitmq_connections_opened_total` | Counter | Total connections opened |
| `rabbitmq_connections_closed_total` | Counter | Total connections closed |
| `rabbitmq_channels` | Gauge | Number of active channels |

### Node Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rabbitmq_process_open_fds` | Gauge | Open file descriptors |
| `rabbitmq_process_max_fds` | Gauge | Maximum file descriptors |
| `rabbitmq_resident_memory_limit_bytes` | Gauge | Memory limit |
| `rabbitmq_disk_space_available_bytes` | Gauge | Available disk space |

## Using Metrics in HyperDX

### View Raw Metrics

Access the Prometheus endpoint directly:
```bash
curl http://localhost:15692/metrics
```

### Query in HyperDX

All metrics have the `service_name=rabbitmq` label for filtering.

#### Monitor Queue Depth

```
rabbitmq_queue_messages{queue="order.processing"}
```

This shows the total number of messages in the queue over time.

#### Track Message Processing Rate

```
rate(rabbitmq_channel_messages_published_total[1m])
```

Shows messages published per second (averaged over 1 minute).

#### Consumer Health Check

```
rabbitmq_queue_consumers{queue="order.processing"}
```

Should show 1 consumer (the worker service). If it drops to 0, the worker is down.

#### Queue Backlog Alert

```
rabbitmq_queue_messages_ready{queue="order.processing"} > 100
```

Alert when more than 100 messages are waiting to be processed.

#### Unacknowledged Messages

```
rabbitmq_queue_messages_unacknowledged{queue="order.processing"}
```

Shows messages currently being processed by consumers.

## Dashboard Ideas

### Queue Health Dashboard

Create a HyperDX dashboard with:

1. **Queue Depth Over Time**
   - Graph: `rabbitmq_queue_messages{queue="order.processing"}`
   - Shows how queue depth changes under load

2. **Message Flow**
   - Graph: `rate(rabbitmq_channel_messages_published_total[1m])`
   - Shows publish rate

3. **Processing Status**
   - Gauge: `rabbitmq_queue_messages_ready` (waiting)
   - Gauge: `rabbitmq_queue_messages_unacknowledged` (processing)

4. **Consumer Status**
   - Gauge: `rabbitmq_queue_consumers` (should be >= 1)

### Correlation with Application Metrics

Compare RabbitMQ metrics with application metrics:

```
# Queue depth vs worker processing time
rabbitmq_queue_messages_ready AND order.processing.duration
```

This helps identify if queue backlog correlates with slower processing times.

### Load Test Analysis

During a load test, monitor:

1. **Order Creation Rate** (API)
   ```
   rate(orders.created[1m])
   ```

2. **Queue Ingestion Rate** (RabbitMQ)
   ```
   rate(rabbitmq_channel_messages_published_total[1m])
   ```

3. **Queue Backlog** (RabbitMQ)
   ```
   rabbitmq_queue_messages_ready
   ```

4. **Processing Rate** (Worker)
   ```
   rate(order.processing.duration_count[1m])
   ```

These four metrics together show the full pipeline health.

## Troubleshooting

### Metrics Not Appearing

1. **Check RabbitMQ Prometheus endpoint:**
   ```bash
   curl http://localhost:15692/metrics
   ```
   Should return Prometheus-format metrics.

2. **Check OTEL Collector logs:**
   ```bash
   docker compose logs otel-collector
   ```
   Look for scrape errors or export failures.

3. **Verify ClickStack is receiving metrics:**
   ```bash
   docker compose logs clickstack | grep rabbitmq
   ```

### RabbitMQ Prometheus Plugin Not Enabled

If you see connection refused on port 15692:

```bash
# Access RabbitMQ container
docker compose exec rabbitmq rabbitmq-plugins list

# Should show rabbitmq_prometheus as enabled
# If not, enable it:
docker compose exec rabbitmq rabbitmq-plugins enable rabbitmq_prometheus

# Restart RabbitMQ
docker compose restart rabbitmq
```

### High Cardinality Warning

RabbitMQ exposes many metrics with multiple labels. If you see performance issues in HyperDX:

1. Reduce scrape interval in `otel-collector/config.yaml` (currently 15s)
2. Add metric filters to exclude unnecessary metrics
3. Use metric relabeling to drop high-cardinality labels

## Advanced Configuration

### Custom Scrape Interval

Edit `otel-collector/config.yaml`:

```yaml
scrape_configs:
  - job_name: 'rabbitmq'
    scrape_interval: 30s  # Change from 15s to 30s
```

### Filter Specific Metrics

Add to the Prometheus receiver config:

```yaml
metric_relabel_configs:
  # Only keep queue-related metrics
  - source_labels: [__name__]
    regex: 'rabbitmq_queue_.*'
    action: keep
```

### Add Custom Labels

```yaml
metric_relabel_configs:
  # Add environment label
  - target_label: environment
    replacement: 'demo'
```

## Reference

- RabbitMQ Prometheus Plugin: https://www.rabbitmq.com/prometheus.html
- Full metrics list: http://localhost:15692/metrics
- OTEL Prometheus Receiver: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/prometheusreceiver
