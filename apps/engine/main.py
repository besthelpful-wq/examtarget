import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import export_pdf, generate, webhooks

app = FastAPI(title="ExamTarget Engine")

_allowed_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(webhooks.router)
app.include_router(generate.router)
app.include_router(export_pdf.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
