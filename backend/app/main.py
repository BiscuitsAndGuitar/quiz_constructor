from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Конструктор опросов и тестов")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/uploads",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "uploads"),
    name="uploads",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
