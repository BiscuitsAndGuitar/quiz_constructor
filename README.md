# Конструктор опросов и тестов

Этап 1: FastAPI, SQLAlchemy 2, PostgreSQL, Alembic и минимальный Vue 3 frontend.
Единственный прикладной API — `GET /health`. Документация — `/docs`, файлы — `/uploads`.
Регистрация, вход, редактор и прохождение форм будут добавлены на следующих этапах.

## Как запустить

Нужны Python 3.11+, Node.js 22.12+ (или 24 LTS), npm и запущенный PostgreSQL.
Команды ниже предназначены для PowerShell. `createdb` и `psql` должны быть в PATH
(обычно они находятся в `C:\Program Files\PostgreSQL\<версия>\bin`).

### 1. Зависимости backend и настройки

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Копирование выполняется только при первой настройке: существующий `.env` сохраняйте.
В `backend/.env` укажите пароль PostgreSQL в `DATABASE_URL` и собственный `SECRET_KEY`.
Если пароль содержит специальные символы URL, закодируйте их (например, `@` → `%40`).
`ACCESS_TOKEN_EXPIRE_MINUTES=30` оставлено для будущего входа.
Случайный секрет можно получить командой:

```powershell
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Создание базы и миграция

Базу создаёт пользователь. Эти команды ещё не выполнялись при подготовке проекта.
Имя базы и пользователь должны совпадать с `DATABASE_URL`.

```powershell
createdb -h localhost -p 5432 -U postgres quiz_constructor
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
..\.venv\Scripts\python -m alembic upgrade head
```

Миграция создаёт 18 таблиц приложения, служебную `alembic_version`, четыре типа
вопросов и шесть операторов условий. Других начальных данных нет.

### 3. Запуск backend

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Откройте [health](http://localhost:8000/health) и [Swagger UI](http://localhost:8000/docs).
Для остановки сервера нажмите Ctrl+C.

### 4. Запуск frontend в другом терминале

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\frontend
npm ci
npm run dev
```

Откройте [страницу приложения](http://localhost:5173).
Порт 5173 фиксирован: если он занят, Vite сообщит об ошибке, а не выберет другой.
CORS backend разрешает источник `http://localhost:5173`.

## Как проверить

Тесты не подключаются к БД и не требуют настоящего `.env`:

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
..\.venv\Scripts\python -m pytest -q
```

Проверка сборки frontend:

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\frontend
npm run build
```

После создания базы и применения миграции:

```powershell
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c '\dt'
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c 'SELECT * FROM question_types;'
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c 'SELECT * FROM condition_operators;'
```

Ожидаются 19 таблиц вместе с `alembic_version`, 4 строки типов и 6 строк операторов.
Проверка отката на пустой учебной базе (удаляет все таблицы приложения и их данные):

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
..\.venv\Scripts\python -m alembic downgrade base
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c '\dt'
..\.venv\Scripts\python -m alembic upgrade head
..\.venv\Scripts\python -m alembic check
```

После online-отката Alembic может оставить пустую служебную `alembic_version`.
Повторный upgrade восстанавливает схему и справочники.

Без подключения к PostgreSQL можно проверить генерацию SQL:

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
..\.venv\Scripts\python -m alembic upgrade head --sql
..\.venv\Scripts\python -m alembic downgrade 0001:base --sql
```

Для этих команд нужны настройки из `.env`, но сервер БД не используется.
Начальная миграция автоматически сгенерирована из метаданных средствами Alembic
(`CreateTableOp`, `CreateIndexOp`, `render_python_code`) и проверена вручную.
Это позволило не создавать базу для обычного `revision --autogenerate`.
Проверка SQL не заменяет выполнение upgrade/downgrade на PostgreSQL.

## Согласованные решения

- Все ссылки на `users` используют `ON DELETE RESTRICT`; удаления пользователей в API нет.
- `questions.image_id` и `attempts.grading_scale_id` используют `SET NULL`.
  Ссылки на тип вопроса и оператор условия — `RESTRICT`.
  Остальные внешние ключи — `CASCADE`: удаляются принадлежащие родителю записи,
  ссылки ответов на удалённые вопросы/варианты и связанные условия.
- Все булевы поля — `NOT NULL`, по умолчанию `false`, кроме `condition_groups.match_all = true`.
- `created_at` получает UTC на стороне PostgreSQL: `timezone('utc', now())`.
  Тип остаётся `timestamp without time zone`, как в схеме; даты, задаваемые приложением,
  также нужно передавать в UTC. Для других дат автоматическое значение не задано.
- `blocks` проверяет, что заполнено ровно одно из `form_id` и `library_block_id`.
- По дополнительному указанию пользователя добавлен `ck_condition_groups_owner`:
  у верхней группы заполнено ровно одно из `block_id` и `question_id`, у вложенной —
  оба пусты. Правило описано в документах, а его реализация через CheckConstraint
  отдельно согласована в задаче.
- Список nullable-полей отдельно согласован с пользователем:
  `forms.description`, `forms.max_attempts`, `forms.time_limit_minutes`, `forms.published_at`,
  `blocks.title`, `blocks.form_id`, `blocks.library_block_id`, `questions.points`,
  `questions.image_id`, `library_blocks.description`, `attempts.user_id`,
  `attempts.finished_at`, `attempts.score`, `attempts.max_score`, `attempts.percent`,
  `attempts.grading_scale_id`, `attempt_answers.text_answer`, `attempt_answers.score`,
  `conditions.choice_id`, `conditions.text_answer`, `condition_groups.parent_group_id`,
  `condition_groups.block_id`, `condition_groups.question_id`. Остальные поля — `NOT NULL`.
- Созданы только восемь явно перечисленных в схеме индексов.
  PostgreSQL также создаёт индексы для первичных ключей и UNIQUE.
- Проверки предметной области при сохранении формы относятся к следующим этапам.
  Здесь нет API для сохранения, публикации или прохождения форм.
