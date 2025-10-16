from dataclasses import dataclass


@dataclass
class PrometheusServiceConfig:
    """Configuration for PrometheusService.

    Controls a tiny HTTP server that exposes Prometheus metrics.
    All fields are optional and can be supplied either via DI-config
    or directly to the PrometheusService constructor.
    """

    address: str = "localhost"
    port: int = 9000
    endpoint: str = "/metrics"
    enabled: bool = True
