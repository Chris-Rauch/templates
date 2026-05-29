from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.util.logging_config import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = Response("Internal Server Error", status_code=500)
        logger.info(f"Received request: {request.method} {request.url}")
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception(f"Exception: {e}")
        finally:
            logger.info(f"Response status: {response.status_code}")
        return response