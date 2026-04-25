"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.database import Base, engine
from app.models import Document  # noqa: F401  # pyright: ignore[reportUnusedImport]  -- registers model with Base.metadata
from app.routes import documents_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocAssist API")
app.include_router(documents_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 once the app is up."""
    return {"status": "ok"}
