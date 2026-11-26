from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers.auth import router as auth_router
from app.routers.forms import router as forms_router
from app.routers.public import router as public_router
from app.routers.attempts import router as attempts_router
from app.routers.statistics import router as statistics_router
from app.services.attempt_errors import AttemptError
from app.config import settings
from app.routers.images import router as images_router
from app.routers.library import router as library_router

app = FastAPI(title="Конструктор опросов и тестов")
app.include_router(auth_router)
app.include_router(forms_router)
app.include_router(public_router)
app.include_router(attempts_router)
app.include_router(statistics_router)
app.include_router(images_router)
app.include_router(library_router)


@app.exception_handler(AttemptError)
async def attempt_error_handler(request, error):
    return JSONResponse(status_code=error.status, content=error.body)


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
            "image_id": "Номер картинки должен быть целым положительным числом или null",
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
            "tags": "Теги должны быть списком строк",
            "block": "Укажите блок с вопросами",
            "is_public": "Публичность должна быть true или false",
            "description": "Описание должно быть текстом или null",
            "scope": "Выберите scope: mine, public или all",
            "limit": "limit должен быть целым числом от 1 до 100",
            "offset": "offset должен быть целым неотрицательным числом",
        }.get(field, "Неверные данные запроса")
    if "answers" in location:
        detail = "Ответы должны содержать целый question_id, список целых option_ids или строку text"
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
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOADS_DIR),
    name="uploads",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
