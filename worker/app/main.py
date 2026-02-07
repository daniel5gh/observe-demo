import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.telemetry import setup_telemetry
from app.consumer import start_consumer
from app.enrich import enrich_product

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_consumer())
    logger.info("RabbitMQ consumer started as background task")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Order Worker", lifespan=lifespan)
setup_telemetry(app)


class EnrichRequest(BaseModel):
    product: str
    quantity: int


@app.post("/enrich")
def enrich(request: EnrichRequest):
    return enrich_product(request.product, request.quantity)


@app.get("/health")
def health():
    return {"status": "ok"}
