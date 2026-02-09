import os
import logging

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def setup_telemetry(app):
    service_name = os.getenv("OTEL_SERVICE_NAME", "order-worker")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

    resource = Resource.create({"service.name": service_name})

    # Parse headers from environment variable
    headers = {}
    if otlp_headers:
        for header in otlp_headers.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()

    # Setup tracing
    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True, headers=headers)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # Setup metrics
    metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True, headers=headers)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
    metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metric_provider)

    FastAPIInstrumentor.instrument_app(app)
    AioPikaInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    logging.basicConfig(level=logging.INFO)
