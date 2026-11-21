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
    location = first["loc"]
    if "correct_text_answers" in location:
        field = "correct_text_answers"
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
            "max_attempts": "Максимум попыток должен быть целым числом от 1 до 1000 или null",
            "time_limit_minutes": "Ограничение времени должно быть целым числом от 1 до 1440 или null",
            "points": "Укажите баллы — целое число от 1 до 1000",
            "allow_partial_scoring": "Режим частичных баллов должен быть true или false",
            "is_correct": "Признак верного ответа должен быть true или false",
            "correct_text_answers": "Допустимые ответы должны быть списком строк",
            "grading_scale": "Шкала оценок должна быть списком строк шкалы",
            "min_percent": "Граница шкалы должна быть целым числом от 0 до 100",
            "grade": "Оценка должна быть строкой от 1 до 20 символов",
            "message": "Сообщение должно быть текстом до 1000 символов или null",
            "condition": "Укажите условие в формате {match_all, items}; у правила оно обязательно",
            "match_all": "Выберите связку условий: true — все, false — любое",
            "items": "Условия должны быть списком простых условий",
            "question": "Укажите ключ вопроса для условия",
            "operator": "Укажите оператор условия",
            "option": "Укажите ключ варианта ответа для условия",
            "text_answer": "Значение текстового условия должно быть строкой",
            "finish_rules": "Правила завершения должны быть списком",
        }.get(field, "Неверные данные запроса")
    if "questions" in location and field in {"points", "allow_partial_scoring", "is_correct", "correct_text_answers"}:
        index = location.index("questions")
        if len(location) > index + 1 and isinstance(location[index + 1], int):
            detail = f"Вопрос {location[index + 1] + 1}: {detail}"
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
