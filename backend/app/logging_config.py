"""Central logging setup.

One place decides the format and level so every module can just do
``logging.getLogger(__name__)`` and get consistent, timestamped output that
includes the per-request id (see app/middleware.py) when one is in scope.
"""

import logging
import sys
from contextvars import ContextVar

# Set by RequestContextMiddleware for the duration of each request so log
# lines emitted anywhere down the call stack can be correlated.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_CONFIGURED = False


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Idempotent — safe to call from both app startup and test fixtures."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # uvicorn ships its own handlers; let our root formatter own the output.
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(noisy)
        lg.handlers.clear()
        lg.propagate = True

    _CONFIGURED = True
