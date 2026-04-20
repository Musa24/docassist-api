"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="DocAssist API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 once the app is up."""
    return {"status": "ok"}
