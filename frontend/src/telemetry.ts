import { WebTracerProvider, SimpleSpanProcessor } from "@opentelemetry/sdk-trace-web";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { Resource } from "@opentelemetry/resources";
import { ZoneContextManager } from "@opentelemetry/context-zone";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";

export function initTelemetry() {
  const resource = new Resource({
    "service.name": "order-frontend",
  });

  const exporter = new OTLPTraceExporter({
    url: "http://localhost:4318/v1/traces",
    headers: {
      authorization: import.meta.env.VITE_OTEL_AUTHORIZATION || "",
    },
  });

  const provider = new WebTracerProvider({
    resource,
  });
  provider.addSpanProcessor(new SimpleSpanProcessor(exporter));

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [/localhost:5050/],
      }),
    ],
  });
}
