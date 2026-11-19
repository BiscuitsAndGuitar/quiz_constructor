# Конструктор опросов и тестов

Этап 3, часть 1: регистрация, вход по JWT и конструктор простых черновиков форм.
API: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `GET /health`.
Формы: `GET /my/forms`, `POST /forms`, `GET /forms/{id}`, `PUT /forms/{id}`, `DELETE /forms/{id}`.
Документация — `/docs`, файлы — `/uploads`. Публикация и прохождение появятся позже.

## Как запустить

Нужны Python 3.11+, Node.js 22.12+ (или 24 LTS), npm и запущенный PostgreSQL.
Команды ниже предназначены для PowerShell. `createdb` и `psql` должны быть в PATH
(обычно они находятся в `C:\Program Files\PostgreSQL\<версия>\bin`).

### 1. Зависимости backend и настройки

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
if (!(Test-Path .venv)) { py -3.11 -m venv .venv }
.\.venv\Scripts\python -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Копирование выполняется только при первой настройке: существующий `.env` сохраняйте.
В `backend/.env` укажите пароль PostgreSQL в `DATABASE_URL` и собственный `SECRET_KEY`.
Если пароль содержит специальные символы URL, закодируйте их (например, `@` → `%40`).
В существующий `.env` добавьте `ALGORITHM=HS256`; срок жизни JWT задаёт
`ACCESS_TOKEN_EXPIRE_MINUTES=30`. Без строки `ALGORITHM` используется HS256.
Случайный секрет можно получить командой:

```powershell
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Создание базы и миграция

Базу создаёт пользователь. Если база уже есть, команду `createdb` пропустите.
Имя базы и пользователь должны совпадать с `DATABASE_URL`.

```powershell
createdb -h localhost -p 5432 -U postgres quiz_constructor
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
.\.venv\Scripts\python -m alembic upgrade head
```

Две миграции создают 19 таблиц приложения, служебную `alembic_version`, четыре типа
вопросов и шесть операторов условий. Вторая миграция добавляет правила досрочного
завершения и поля сообщений. Других начальных данных нет.

### 3. Запуск backend

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Откройте [health](http://localhost:8000/health) и [Swagger UI](http://localhost:8000/docs).
Для остановки сервера нажмите Ctrl+C.

### 4. Запуск frontend в другом терминале

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\frontend
npm ci
if (!(Test-Path .env)) { Copy-Item .env.example .env }
npm run dev
```

Откройте [страницу приложения](http://localhost:5173).
Порт 5173 фиксирован: если он занят, Vite сообщит об ошибке, а не выберет другой.
CORS backend разрешает источник `http://localhost:5173`.
Адрес API задаётся в `frontend/.env`: `VITE_API_BASE_URL=http://localhost:8000`.
После изменения `.env` перезапустите Vite. Секрет JWT во frontend не передаётся.

## Работа с backend и frontend отдельно

Открывайте `backend` отдельным проектом PyCharm, а `frontend` — другим проектом.
Для backend выберите существующий интерпретатор:
`C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend\.venv\Scripts\python.exe`.
Рабочая папка для Python, pytest и Alembic — `backend`.
Для запуска сервера используйте модуль `uvicorn` с параметрами `app.main:app --reload`.
Для frontend рабочая папка — `frontend`, запуск — `npm run dev`.

Python-окружение находится в `backend/.venv`, npm-зависимости — в
`frontend/node_modules`. Оба каталога исключены из Git. Репозиторий остаётся
общим для backend, frontend и документов.

## Как проверить

HTTP-тестам нужны запущенный PostgreSQL, применённые миграции и `backend/.env`.
Они используют подключение из `DATABASE_URL`, каждый тест работает во внешней
транзакции с откатом; `commit()` сервиса завершает только SAVEPOINT. Тестовые
пользователи не остаются в базе, существующие записи не меняются. Последовательность
номеров пользователей может увеличиться — пропуски в id нормальны.
Отдельная тестовая база не создаётся. Для токенов тесты используют свой секрет.

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
.\.venv\Scripts\python -m pytest -q
```

Без подключения к БД можно проверить функции безопасности, health и метаданные:

```powershell
.\.venv\Scripts\python -m pytest tests/test_security.py tests/test_health.py tests/test_models.py -q
```

Проверка фронтенда (тесты используют встроенный тестовый модуль Node.js):

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\frontend
npm run build
node --test src/utils/password.test.js src/utils/formEditor.test.js
```

### Проверка конструктора

1. Войдите составителем и откройте «Мои формы». Создайте опрос, указав название.
2. Добавьте вопросы трёх типов: один вариант, несколько вариантов, текстовый ответ.
   Добавьте варианты ответа, отметьте обязательность, сохраните и обновите страницу.
3. Проверьте изменение названия и описания, удаление вопросов и вариантов, повторное
   сохранение. Пустые тексты вопросов и неполные списки вариантов допустимы в черновике.
4. Создайте тест: обязательность вопроса не отображается, видна подсказка о следующем этапе.
5. В списке проверьте фильтры типа и статуса, отмену удаления и подтверждение удаления.
6. Участнику редактор недоступен. Чужая форма даёт 403, отсутствующая — 404.
   Для опубликованной формы редактор доступен только для чтения, PUT возвращает 409.
   Публикации через интерфейс на этом этапе нет.

Редактор показывает один блок; API сохраняет порядок всех переданных блоков, вопросов
и вариантов. Скрытые настройки формы сохраняются при редактировании. Сохранение
заменяет содержимое черновика в одной транзакции; при ошибке прежнее содержимое остаётся.
Тесты backend проверяют также откат, права, коллизию публичного кода и каскадное удаление
без изменения библиотеки. Новых зависимостей и миграций на этом этапе нет.

### Проверка регистрации и входа

1. В [Swagger UI](http://localhost:8000/docs) выполните `POST /auth/register`
   с новым email, именем, паролем и `is_author: true` или `false`: ожидается 201.
   Повторный email даёт 409; неверные данные — 422 с русским текстом в `detail`.
2. Выполните `POST /auth/login`. Скопируйте `access_token`, нажмите **Authorize**
   и вставьте сам токен (без слова Bearer). `GET /auth/me` вернёт пользователя;
   без токена — 401. В ответах не должно быть `password_hash`.
3. На [фронтенде](http://localhost:5173) зарегистрируйте составителя и участника
   с разными email. Проверьте автоматический вход, выход, повторный вход и обновление страницы.
4. Гостем откройте `/my/forms`: откроется вход с `redirect`. После входа составителем
   вернётесь туда. Для участника `/my/forms` покажет «Нет доступа», для составителя
   то же произойдёт на `/my/attempts`. Неизвестный адрес покажет «Не найдено».
5. На регистрации проверьте короткий пароль, слишком длинный пароль, несовпадение
   повторного пароля и занятый email. Подсказка «Не менее 8 символов» видна постоянно.
   При входе неверный пароль любой длины даёт 401.

Пароль: минимум 8 символов Unicode, максимум 72 байта UTF-8; разрешены кириллица
и эмодзи. Пробелы сохраняются, обрезки нет. 36 русских букв или 18 обычных эмодзи
занимают ровно 72 байта. В интерфейсе и ошибках API единица «байт» не используется.
Токен хранится в localStorage; при его недействительности удаляется. Если браузер
запретил localStorage, вход работает в памяти до обновления страницы.

Добавлены `bcrypt` для хеширования паролей, `PyJWT` для подписи и проверки JWT,
`email-validator` для проверки email в Pydantic. `app/dependencies.py` содержит
общие проверки пользователя и роли через Depends; файл добавлен в структуру AGENTS.md.

После создания базы и применения миграции:

```powershell
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c '\dt'
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c 'SELECT * FROM question_types;'
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c 'SELECT * FROM condition_operators;'
```

Ожидаются 20 таблиц вместе с `alembic_version`, 4 строки типов и 6 строк операторов.
Проверка отката только второй миграции из папки `backend`:

```powershell
.\.venv\Scripts\python -m alembic downgrade -1
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m alembic check
```

Откат второй миграции удаляет правила досрочного завершения, их группы и условия,
а также новые поля сообщений и ссылки на правила. Прежние группы показа сохраняются.
Проверка отката на пустой учебной базе (удаляет все таблицы приложения и их данные):

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
.\.venv\Scripts\python -m alembic downgrade base
psql -h localhost -p 5432 -U postgres -d quiz_constructor -c '\dt'
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m alembic check
```

После online-отката Alembic может оставить пустую служебную `alembic_version`.
Повторный upgrade восстанавливает схему и справочники.

Без подключения к PostgreSQL можно проверить генерацию SQL:

```powershell
cd C:\Users\azatk\PycharmProjects\QUIZ_CONSTRUCTOR\backend
.\.venv\Scripts\python -m alembic upgrade head --sql
.\.venv\Scripts\python -m alembic downgrade 0001:base --sql
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
- Во второй миграции обновлён `ck_condition_groups_owner`: у верхней группы заполнено
  ровно одно из `block_id`, `question_id`, `early_finish_rule_id`, у вложенной — все три пусты.
- Список nullable-полей отдельно согласован с пользователем:
  `forms.description`, `forms.max_attempts`, `forms.time_limit_minutes`, `forms.published_at`,
  `blocks.title`, `blocks.form_id`, `blocks.library_block_id`, `questions.points`,
  `questions.image_id`, `library_blocks.description`, `attempts.user_id`,
  `attempts.finished_at`, `attempts.score`, `attempts.max_score`, `attempts.percent`,
  `attempts.grading_scale_id`, `attempt_answers.text_answer`, `attempt_answers.score`,
  `conditions.choice_id`, `conditions.text_answer`, `condition_groups.parent_group_id`,
  `condition_groups.block_id`, `condition_groups.question_id`. Остальные поля — `NOT NULL`.
- Созданы восемь явно перечисленных в схеме индексов и индекс
  `early_finish_rules.question_id`, согласованный в доработке этапа 1.
  PostgreSQL также создаёт индексы для первичных ключей и UNIQUE.
- Реализовано сохранение простых черновиков. Проверки публикации, баллов, условий
  и прохождения форм относятся к следующим этапам.
