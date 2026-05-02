from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api import data, intelligence
from app.rag.pipeline import rag_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables
    Base.metadata.create_all(bind=engine)
    # Initialise RAG pipeline (loads embedding model + builds FAISS index)
    rag_pipeline.initialise()
    yield
    # Cleanup (if needed)


app = FastAPI(
    title="AI Procurement Negotiation Assistant",
    description=(
        "GenAI-powered procurement assistant that evaluates vendors, "
        "analyses historical pricing trends, and generates RAG-grounded "
        "negotiation strategies via REST APIs."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "AI Procurement Negotiation Assistant"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy", "rag_ready": rag_pipeline.index is not None}
