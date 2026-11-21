from app.services.form_validation import InvalidFormError


def question_index(blocks: list[dict]) -> dict:
    result = {}
    number = 0
    for block_position, block in enumerate(blocks):
        for position, question in enumerate(block.get("questions", [])):
            number += 1
            result[question["key"]] = (question, (block_position, position), number)
    return result


def validate_condition(condition, questions, owner_position, label, operators, *, include_self=False):
    if not condition["items"]:
        raise InvalidFormError(f"{label}: добавьте хотя бы одно условие")
    for item in condition["items"]:
        source = questions.get(item["question"])
        if source is None:
            raise InvalidFormError(f"{label}: вопрос «{item['question']}» не найден")
        question, position, number = source
        prefix = f"{label}: ссылка на вопрос {number}"
        if question["type"] == "info":
            raise InvalidFormError(f"{prefix} — на «Текст без вопроса» ссылаться нельзя")
        if position > owner_position or (position == owner_position and not include_self):
            requirement = "не позже вопроса правила" if include_self else "раньше"
            raise InvalidFormError(f"{prefix} недопустима: вопрос должен стоять {requirement}")
        operator = item["operator"]
        if operator not in operators:
            raise InvalidFormError(f"{prefix}: неизвестный оператор «{operator}»")
        option, text = item.get("option"), item.get("text_answer")
        if operator in {"chosen", "not_chosen"}:
            if question["type"] not in {"single", "multiple"}:
                raise InvalidFormError(f"{prefix}: оператор выбора требует вопрос с вариантами")
            if not option or option not in {choice["key"] for choice in question.get("options", [])}:
                raise InvalidFormError(f"{prefix}: выберите вариант именно этого вопроса")
            if text is not None:
                raise InvalidFormError(f"{prefix}: для выбора варианта text_answer не нужен")
        elif operator in {"equals", "contains"}:
            if question["type"] != "text":
                raise InvalidFormError(f"{prefix}: этот оператор допустим только для текстового вопроса")
            if text is None or not text.strip() or len(text) > 500:
                raise InvalidFormError(f"{prefix}: введите текст от 1 до 500 символов, не только пробелы")
            if option is not None:
                raise InvalidFormError(f"{prefix}: для текстового условия вариант не нужен")
        elif operator in {"answered", "not_answered"}:
            if question["type"] not in {"single", "multiple", "text"}:
                raise InvalidFormError(f"{prefix}: вопрос не предусматривает ответа")
            if option is not None or text is not None:
                raise InvalidFormError(f"{prefix}: оператор ответа не требует варианта или текста")


def validate_conditions(blocks: list[dict], is_test: bool, operators: set[str]) -> None:
    """Проверяем итоговый порядок; функция не зависит от HTTP и базы данных."""
    questions = question_index(blocks)
    for block_position, block in enumerate(blocks):
        condition = block.get("condition")
        if is_test and "condition" in block:
            raise InvalidFormError("Условия показа есть только у опросов")
        if condition is not None:
            # Позиция -1 исключает все вопросы самого блока, включая первый.
            validate_condition(condition, questions, (block_position, -1),
                               f"Условие блока {block_position + 1}", operators)
        for question in block.get("questions", []):
            _, position, number = questions[question["key"]]
            condition = question.get("condition")
            rules = question.get("finish_rules", [])
            if is_test and ("condition" in question or "finish_rules" in question):
                raise InvalidFormError("Условия показа и правила завершения есть только у опросов")
            if condition is not None:
                validate_condition(condition, questions, position, f"Условие вопроса {number}", operators)
            if question["type"] == "info" and rules:
                raise InvalidFormError(f"Вопрос {number}: у «Текста без вопроса» не может быть правил завершения")
            for rule_number, rule in enumerate(rules, 1):
                label = f"Правило {rule_number} вопроса {number}"
                if rule.get("message") is not None and len(rule["message"]) > 1000:
                    raise InvalidFormError(f"{label}: сообщение должно быть не длиннее 1000 символов")
                if rule.get("condition") is None:
                    raise InvalidFormError(f"{label}: условие обязательно")
                validate_condition(rule["condition"], questions, position, label, operators, include_self=True)
