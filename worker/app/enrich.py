import random
import logging

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

CATALOG = {
    "widget": 9.99,
    "gadget": 24.99,
    "gizmo": 14.50,
    "doohickey": 7.25,
}


def enrich_product(product: str, quantity: int) -> dict:
    with tracer.start_as_current_span("enrich_product") as span:
        span.set_attribute("enrich.product", product)
        span.set_attribute("enrich.quantity", quantity)

        base_price = CATALOG.get(product.lower(), round(random.uniform(5.0, 50.0), 2))
        total_price = round(base_price * quantity, 2)
        category = "known" if product.lower() in CATALOG else "dynamic"

        result = {
            "product": product,
            "quantity": quantity,
            "unit_price": base_price,
            "price": total_price,
            "category": category,
            "currency": "USD",
        }

        span.set_attribute("enrich.price", total_price)
        span.set_attribute("enrich.category", category)
        logger.info("Enriched product=%s quantity=%d price=%.2f", product, quantity, total_price)
        return result
