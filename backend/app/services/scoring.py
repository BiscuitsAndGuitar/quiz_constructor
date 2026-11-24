from decimal import Decimal, ROUND_HALF_UP


def normalize_text(value, numeric=False):
    result = " ".join((value or "").lower().split())
    return result.replace(",", ".") if numeric else result


def question_score(question, answer):
    kind = question["type"]
    points = question.get("points") or 0
    if kind == "info" or not answer:
        return 0
    if kind == "text":
        text = normalize_text(answer.get("text"), numeric=True)
        return points if text and any(text == normalize_text(value, numeric=True)
                                     for value in question.get("correct_text_answers", [])) else 0
    selected = set(answer.get("option_ids") or [])
    correct = {option["id"] for option in question.get("options", []) if option.get("is_correct")}
    if not selected or not correct:
        return 0
    if kind == "single":
        return points if len(selected) == 1 and selected <= correct else 0
    if not question.get("allow_partial_scoring"):
        return points if selected == correct else 0
    return max(0, (len(selected & correct) - len(selected - correct)) * points // len(correct))


def percent_score(score, max_score):
    if max_score == 0:
        return Decimal("0.00")
    return (Decimal(score) * 100 / Decimal(max_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def select_grade(score, max_score, scale):
    if max_score == 0:
        return None
    suitable = [row for row in scale if score * 100 >= row["min_percent"] * max_score]
    return max(suitable, key=lambda row: row["min_percent"]) if suitable else None


def completion_message(rule_message=None, grade_message=None, form_message=None):
    return next((message for message in [rule_message, grade_message, form_message] if message), "Спасибо за участие!")
