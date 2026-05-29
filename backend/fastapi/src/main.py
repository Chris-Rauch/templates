from fastapi import FastAPI, Request, Response
import uvicorn
import sys
import os


# adding ./robotalker_backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.middleware.auth import AuthMiddleware
from src.middleware.logging import LoggingMiddleware
from src.routes import route

# my stuff

async def lifespan(app: FastAPI):
    """
    When the app first launches we need to a session to interact with the db.
    """
    # before the app goes live
    yield
    # stuff that executes after the life of the app goes here

tags = [
    {
        "name": "tag",
        "description": "what does your tag do?"
    },
]

app = FastAPI(
    title="This is a Template!",
    description="",
    version="1.0.0",
    root_path="/",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc UI
    openapi_tags=tags,
)
app.include_router(route.router, prefix="/pre")
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggingMiddleware)


# Run the app with Uvicorn if executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="debug")