import os
import json
import asyncio
import logging
import random
import time

import aio_pika
from opentelemetry import trace, metrics

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create a histogram to track processing time
processing_time_histogram = meter.create_histogram(
    name="order.processing.duration",
    description="Time taken to process an order message",
    unit="s"
)


async def start_consumer():
    host = os.getenv("RABBITMQ_HOST", "localhost")
    username = os.getenv("RABBITMQ_USERNAME", "demo")
    password = os.getenv("RABBITMQ_PASSWORD", "demo")
    url = f"amqp://{username}:{password}@{host}/"

    # Configurable random wait times (in seconds)
    min_wait = float(os.getenv("WORKER_MIN_WAIT", "0.1"))
    max_wait = float(os.getenv("WORKER_MAX_WAIT", "2.0"))

    logger.info(f"Worker configured with random wait between {min_wait}s and {max_wait}s")

    connection = None
    for attempt in range(1, 21):
        try:
            connection = await aio_pika.connect_robust(url)
            logger.info("Connected to RabbitMQ")
            break
        except Exception:
            logger.warning("RabbitMQ connection attempt %d failed, retrying...", attempt)
            await asyncio.sleep(2)

    if connection is None:
        logger.error("Could not connect to RabbitMQ after retries")
        return

    channel = await connection.channel()
    exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue("order.processing", durable=True)
    await queue.bind(exchange, routing_key="order.created")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            # Start timing for metrics
            start_time = time.time()
            status = "success"
            product = ""

            with tracer.start_as_current_span("process_order") as span:
                try:
                    body = json.loads(message.body.decode())
                    order_id = str(body.get("Id", ""))
                    product = body.get("Product", "")

                    span.set_attribute("order.id", order_id)
                    span.set_attribute("order.product", product)
                    logger.info("Processing order: %s", body)

                    # Handle error/error2 triggers sent by the API
                    if str(product).lower() == "worker error":
                        # Log when error2 is detected for traceability
                        if body.get("error2"):
                            logger.warning("Detected 'worker error' trigger in message for order %s", order_id)
                        # simulate error handling similar to existing 'error' behavior
                        # logger.error("Simulated processing error for order %s", order_id)
                        status = "error"
                        raise Exception("Simulated processing error for order %s" % order_id)

                    # Simulate processing with random delay
                    processing_delay = random.uniform(min_wait, max_wait)
                    span.set_attribute("processing.delay_seconds", processing_delay)
                    logger.info(f"Simulating {processing_delay:.2f}s processing time for order {order_id}")
                    await asyncio.sleep(processing_delay)

                    logger.info("Order processed: %s", order_id)
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    # Record processing time metric
                    duration = time.time() - start_time
                    processing_time_histogram.record(
                        duration,
                        attributes={
                            "order.product": product,
                            "status": status
                        }
                    )

    await queue.consume(on_message)
    logger.info("Consumer started, waiting for messages...")
