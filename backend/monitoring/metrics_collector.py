from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from time import time
from typing import Callable

registry = CollectorRegistry()

retrieval_latency = Histogram(
    'retrieval_latency_ms', 'Retrieval latency in milliseconds', ['service'], registry=registry
)
llm_latency = Histogram(
    'llm_latency_ms', 'LLM completion latency in milliseconds', ['service'], registry=registry
)
retrieval_confidence = Gauge(
    'retrieval_confidence_avg', 'Average retrieval confidence', registry=registry
)
gpu_utilization = Gauge(
    'gpu_utilization_percent', 'GPU utilization percent', ['service'], registry=registry
)


def timed(hist: Histogram, service: str) -> Callable:
    def decorator(fn: Callable):
        def wrapper(*args, **kwargs):
            start = time()
            try:
                return fn(*args, **kwargs)
            finally:
                dur_ms = (time() - start) * 1000.0
                hist.labels(service=service).observe(dur_ms)
        return wrapper
    return decorator


def render_prometheus() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST
