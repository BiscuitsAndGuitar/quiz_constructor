from app.schemas.forms import FormSave, GradeData, QuestionData


class InvalidFormError(Exception):
    pass


def publication_problems(form: dict) -> list[str]:
    problems = []
    questions = [question for block in form["blocks"] for question in block["questions"]]
    if not questions:
        problems.append("В форме должен быть хотя бы один вопрос")
    for number, question in enumerate(questions, 1):
        kind = question["type"]
        if kind == "info":
            continue
        choices = question.get("options", [])
        if kind in {"single", "multiple"} and len(choices) < 2:
            problems.append(f"В вопросе {number} меньше двух вариантов")
        if form["is_test"]:
            correct = (bool(question.get("correct_text_answers")) if kind == "text"
                       else any(choice.get("is_correct") for choice in choices))
            if not correct:
                problems.append(f"В вопросе {number} нет правильного ответа")
            points = question.get("points")
            if type(points) is not int or points <= 0:
                problems.append(f"В вопросе {number} не заданы баллы — целое число больше 0")
    return problems


def normalize_text_answers(answers: list[str], number: int) -> list[str]:
    result = []
    seen = set()
    for answer in answers:
        answer = answer.strip()
        if not answer:
            continue
        if len(answer) > 255:
            raise InvalidFormError(f"Вопрос {number}: допустимый ответ должен быть не длиннее 255 символов")
        # Сохраняем написание первого ответа, сравниваем без регистра и лишних пробелов.
        normalized = " ".join(answer.split()).casefold()
        if normalized not in seen:
            result.append(answer)
            seen.add(normalized)
    return result


def validate_grading_scale(scale: list[GradeData]) -> None:
    seen = set()
    for number, row in enumerate(scale, 1):
        if not 0 <= row.min_percent <= 100:
            raise InvalidFormError(f"Шкала, строка {number}: процент должен быть целым числом от 0 до 100")
        if row.min_percent in seen:
            raise InvalidFormError("Границы процентов в шкале оценок не должны повторяться")
        seen.add(row.min_percent)
        row.grade = row.grade.strip()
        if not 1 <= len(row.grade) <= 20:
            raise InvalidFormError(f"Шкала, строка {number}: оценка должна содержать от 1 до 20 символов")
        if row.message is not None and len(row.message) > 1000:
            raise InvalidFormError(f"Шкала, строка {number}: сообщение должно быть не длиннее 1000 символов")
    if scale and 0 not in seen:
        raise InvalidFormError("В шкале оценок должна быть строка с границей 0%")


def validate_test_question(question: QuestionData, number: int) -> None:
    if question.points is None or not 1 <= question.points <= 1000:
        raise InvalidFormError(f"Вопрос {number}: укажите баллы — целое число от 1 до 1000")
    question.allow_partial_scoring = bool(question.allow_partial_scoring) if question.type == "multiple" else False
    if question.type == "single" and sum(bool(option.is_correct) for option in question.options) > 1:
        raise InvalidFormError(f"Вопрос {number}: у типа «Один ответ» может быть не больше одного верного варианта")
    answers = question.correct_text_answers or []
    if question.type != "text" and answers:
        raise InvalidFormError(f"Вопрос {number}: допустимые текстовые ответы можно задавать только у текстового вопроса")
    question.correct_text_answers = normalize_text_answers(answers, number)


def validate_form(data: FormSave, is_test: bool) -> None:
    if data.max_attempts is not None and not 1 <= data.max_attempts <= 1000:
        raise InvalidFormError("Максимум попыток должен быть целым числом от 1 до 1000 или null")
    if data.time_limit_minutes is not None and not 1 <= data.time_limit_minutes <= 1440:
        raise InvalidFormError("Ограничение времени должно быть целым числом от 1 до 1440 или null")
    if not is_test and (data.grading_scale or data.time_limit_minutes is not None
                        or data.shuffle_questions or data.show_correct_answers or data.show_results_by_block):
        raise InvalidFormError("Это поле есть только у тестов")
    number = 0
    for block in data.blocks:
        for question in block.questions:
            number += 1
            if is_test:
                validate_test_question(question, number)
            elif (question.points is not None or question.allow_partial_scoring
                  or question.correct_text_answers or any(option.is_correct for option in question.options)):
                raise InvalidFormError("Это поле есть только у тестов")
    if is_test:
        validate_grading_scale(data.grading_scale or [])
