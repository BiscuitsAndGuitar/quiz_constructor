from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers.auth import router as auth_router
from app.routers.forms import router as forms_router

app = FastAPI(title="Конструктор опросов и тестов")
app.include_router(auth_router)
app.include_router(forms_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, error: RequestValidationError):
    # Не возвращаем исходные данные ошибки: среди них может быть пароль.
    first = error.errors()[0]
    field = first["loc"][-1] if first["loc"] else None
    if first["type"] in {"auth", "form"}:
        detail = first["msg"]
    else:
        detail = {
            "email": "Укажите корректный email",
            "password": "Укажите пароль",
            "name": "Имя должно содержать от 1 до 100 символов",
            "is_author": "Выберите роль: составитель или участник",
            "title": "Название должно содержать от 1 до 255 символов",
            "is_test": "Укажите тип формы: опрос или тест",
            "blocks": "У формы должен быть хотя бы один блок",
            "completion_message": "Сообщение завершения должно быть не длиннее 1000 символов",
            "key": "Укажите непустой ключ элемента",
            "text": "Укажите текст; вариант ответа должен быть не длиннее 500 символов",
            "type": "Укажите тип вопроса",
            "max_attempts": "Максимум попыток должен быть целым числом допустимого размера или null",
            "time_limit_minutes": "Ограничение времени должно быть целым числом допустимого размера или null",
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
