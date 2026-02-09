import os
import json
import asyncio
import logging

import aio_pika
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def start_consumer():
    host = os.getenv("RABBITMQ_HOST", "localhost")
    username = os.getenv("RABBITMQ_USERNAME", "demo")
    password = os.getenv("RABBITMQ_PASSWORD", "demo")
    url = f"amqp://{username}:{password}@{host}/"

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
            with tracer.start_as_current_span("process_order") as span:
                body = json.loads(message.body.decode())
                span.set_attribute("order.id", str(body.get("Id", "")))
                span.set_attribute("order.product", body.get("Product", ""))
                logger.info("Processing order: %s", body)

                # Handle error/error2 triggers sent by the API
                if str(body.get("Product", "")).lower() == "worker error":
                    # Log when error2 is detected for traceability
                    if body.get("error2"):
                        logger.warning("Detected 'worker error' trigger in message for order %s", body.get("Id"))
                    # simulate error handling similar to existing 'error' behavior
                    # logger.error("Simulated processing error for order %s", body.get("Id"))
                    raise Exception("Simulated processing error for order %s" % body.get("Id"))

                # Simulate processing delay
                await asyncio.sleep(0.5)
                logger.info("Order processed: %s", body.get("Id"))

    await queue.consume(on_message)
    logger.info("Consumer started, waiting for messages...")
