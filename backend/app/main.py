from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers.auth import router as auth_router

app = FastAPI(title="Конструктор опросов и тестов")
app.include_router(auth_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, error: RequestValidationError):
    # Не возвращаем исходные данные ошибки: среди них может быть пароль.
    first = error.errors()[0]
    field = first["loc"][-1] if first["loc"] else None
    if first["type"] == "auth":
        detail = first["msg"]
    else:
        detail = {
            "email": "Укажите корректный email",
            "password": "Укажите пароль",
            "name": "Имя должно содержать от 1 до 100 символов",
            "is_author": "Выберите роль: составитель или участник",
        }.get(field, "Неверные данные запроса")
    return JSONResponse(status_code=422, content={"detail": detail})


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
