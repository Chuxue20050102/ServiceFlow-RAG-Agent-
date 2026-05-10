from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import serviceflow
from app.database.base import Base
from app.database.session import engine


app = FastAPI(
    title="ServiceFlow RAG Agent API",
    description="After-sales ticket routing and handling suggestion API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(serviceflow.router, prefix="/api/serviceflow", tags=["serviceflow"])


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    add_trace_columns()


def add_trace_columns() -> None:
    statements = [
        "ALTER TABLE ticket_analysis ADD COLUMN parse_success BOOL NOT NULL DEFAULT TRUE",
        "ALTER TABLE ticket_analysis ADD COLUMN parse_error TEXT NULL",
    ]
    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                pass


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
