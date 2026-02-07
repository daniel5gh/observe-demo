import os
import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def setup_telemetry(app):
    service_name = os.getenv("OTEL_SERVICE_NAME", "order-worker")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    
    # Parse headers from environment variable
    headers = {}
    if otlp_headers:
        for header in otlp_headers.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
    
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    AioPikaInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    logging.basicConfig(level=logging.INFO)
