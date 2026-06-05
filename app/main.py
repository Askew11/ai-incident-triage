from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.database import init_db
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Incident Triage Assistant",
    description=(
        "A backend AI service that ingests incident records, summarizes issues, "
        "classifies and prioritizes tickets, flags process/compliance gaps, "
        "and recommends next actions."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
