"""
RabbitMQ Event Tracer

Consumes events from RabbitMQ's internal event exchange and converts them
to OpenTelemetry traces for visibility into RabbitMQ operations.
"""
import os
import json
import asyncio
import logging
from datetime import datetime

import aio_pika
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import SpanKind

# Set log level from environment variable (default INFO, use DEBUG for troubleshooting)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_telemetry():
    """Setup OpenTelemetry tracing"""
    service_name = os.getenv("OTEL_SERVICE_NAME", "rabbitmq-events")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_headers_str = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

    resource = Resource.create({"service.name": service_name})

    # Parse headers
    headers = {}
    if otlp_headers_str:
        for header in otlp_headers_str.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    logger.info(f"Telemetry configured: service={service_name}, endpoint={otlp_endpoint}")
    return trace.get_tracer(__name__)


async def process_event(event_body: dict, routing_key: str, tracer: trace.Tracer):
    """Convert RabbitMQ event to OpenTelemetry span"""

    # Extract event type from routing key (e.g., "connection.created")
    event_type = routing_key

    # Determine span name and kind
    span_name = f"rabbitmq.{event_type}"

    # Map event types to span kinds
    if "created" in event_type or "declared" in event_type:
        kind = SpanKind.INTERNAL
    elif "closed" in event_type or "deleted" in event_type:
        kind = SpanKind.INTERNAL
    else:
        kind = SpanKind.INTERNAL

    # Log event for debugging
    logger.debug(f"Processing event: {event_type}, body keys: {list(event_body.keys())}")

    # Create span
    with tracer.start_as_current_span(span_name, kind=kind) as span:
        # Add common attributes
        span.set_attribute("rabbitmq.event.type", event_type)

        # Only add attributes if they exist in the event body
        if "node" in event_body:
            span.set_attribute("rabbitmq.node", event_body.get("node", "unknown"))

        # If event body is empty or minimal, still create a span with routing key
        if not event_body or len(event_body) == 0:
            logger.debug(f"Empty event body for {event_type}, creating minimal span")
            span.set_attribute("rabbitmq.event.minimal", True)
            return

        # Add event-specific attributes
        if "connection" in event_type:
            span.set_attribute("rabbitmq.connection.name", event_body.get("name", ""))
            span.set_attribute("rabbitmq.connection.peer_host", event_body.get("peer_host", ""))
            span.set_attribute("rabbitmq.connection.peer_port", event_body.get("peer_port", 0))
            span.set_attribute("rabbitmq.connection.user", event_body.get("user", ""))
            span.set_attribute("rabbitmq.connection.vhost", event_body.get("vhost", ""))

        elif "channel" in event_type:
            span.set_attribute("rabbitmq.channel.number", event_body.get("number", 0))
            span.set_attribute("rabbitmq.channel.user", event_body.get("user", ""))
            span.set_attribute("rabbitmq.channel.vhost", event_body.get("vhost", ""))
            span.set_attribute("rabbitmq.channel.connection", event_body.get("connection_name", ""))

        elif "queue" in event_type:
            span.set_attribute("rabbitmq.queue.name", event_body.get("name", ""))
            span.set_attribute("rabbitmq.queue.vhost", event_body.get("vhost", ""))
            span.set_attribute("rabbitmq.queue.durable", event_body.get("durable", False))
            span.set_attribute("rabbitmq.queue.auto_delete", event_body.get("auto_delete", False))

        elif "consumer" in event_type:
            span.set_attribute("rabbitmq.consumer.tag", event_body.get("consumer_tag", ""))
            span.set_attribute("rabbitmq.consumer.queue", event_body.get("queue_name", ""))
            span.set_attribute("rabbitmq.consumer.channel", event_body.get("channel", ""))

        elif "exchange" in event_type:
            span.set_attribute("rabbitmq.exchange.name", event_body.get("name", ""))
            span.set_attribute("rabbitmq.exchange.type", event_body.get("type", ""))
            span.set_attribute("rabbitmq.exchange.vhost", event_body.get("vhost", ""))
            span.set_attribute("rabbitmq.exchange.durable", event_body.get("durable", False))

        elif "binding" in event_type:
            span.set_attribute("rabbitmq.binding.source", event_body.get("source_name", ""))
            span.set_attribute("rabbitmq.binding.destination", event_body.get("destination_name", ""))
            span.set_attribute("rabbitmq.binding.routing_key", event_body.get("routing_key", ""))
            span.set_attribute("rabbitmq.binding.vhost", event_body.get("vhost", ""))

        # Add timestamp if available
        if "timestamp" in event_body:
            span.set_attribute("rabbitmq.event.timestamp", event_body["timestamp"])

        logger.debug(f"Created span for event: {event_type}")


async def start_event_consumer():
    """Start consuming from RabbitMQ event exchange"""
    host = os.getenv("RABBITMQ_HOST", "localhost")
    username = os.getenv("RABBITMQ_USERNAME", "demo")
    password = os.getenv("RABBITMQ_PASSWORD", "demo")
    url = f"amqp://{username}:{password}@{host}/"

    tracer = setup_telemetry()

    # Connect with retry
    connection = None
    for attempt in range(1, 21):
        try:
            connection = await aio_pika.connect_robust(url)
            logger.info("Connected to RabbitMQ")
            break
        except Exception as e:
            logger.warning(f"RabbitMQ connection attempt {attempt} failed: {e}, retrying...")
            await asyncio.sleep(2)

    if connection is None:
        logger.error("Could not connect to RabbitMQ after retries")
        return

    channel = await connection.channel()

    # Create a queue to receive events
    queue = await channel.declare_queue("rabbitmq.events.trace", durable=False, auto_delete=True)

    # Bind to the RabbitMQ event exchange for various event types
    event_exchange = "amq.rabbitmq.event"

    event_patterns = [
        "connection.created",
        "connection.closed",
        "channel.created",
        "channel.closed",
        "queue.created",
        "queue.deleted",
        "queue.declared",
        "consumer.created",
        "consumer.deleted",
        "exchange.created",
        "exchange.deleted",
        "binding.created",
        "binding.deleted",
    ]

    for pattern in event_patterns:
        await queue.bind(event_exchange, routing_key=pattern)
        logger.info(f"Bound to event: {pattern}")

    async def on_event(message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                routing_key = message.routing_key or "unknown"

                # Try to decode message body
                body_raw = message.body.decode('utf-8', errors='replace')

                # RabbitMQ events might be in different formats
                # Try JSON first
                try:
                    body = json.loads(body_raw)
                except json.JSONDecodeError:
                    # If not JSON, create a minimal event from available data
                    logger.debug(f"Non-JSON event body for {routing_key}, using headers")
                    body = {}

                    # Extract what we can from message properties and headers
                    if message.headers:
                        body = dict(message.headers)

                # Add metadata from message properties
                if not body:
                    body = {}

                # Add timestamp from message
                if message.timestamp and 'timestamp' not in body:
                    body['timestamp'] = message.timestamp.timestamp()

                logger.info(f"Received event: {routing_key}")
                logger.debug(f"Event body: {body}")

                # Convert to trace
                await process_event(body, routing_key, tracer)

            except Exception as e:
                logger.error(f"Error processing event {routing_key}: {e}", exc_info=True)
                logger.error(f"Raw message body (first 200 chars): {body_raw[:200] if 'body_raw' in locals() else 'N/A'}")

    await queue.consume(on_event)
    logger.info("RabbitMQ event tracer started, waiting for events...")


async def main():
    """Main entry point"""
    logger.info("Starting RabbitMQ Event Tracer")
    await start_event_consumer()

    # Keep running
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
