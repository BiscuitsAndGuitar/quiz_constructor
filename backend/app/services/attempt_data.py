from sqlalchemy import select

from app.models import GradingScale
from app.services.forms import build_form_response


def numeric_condition(condition):
    if condition is None:
        return None
    items = []
    for item in condition["items"]:
        converted = {"question_id": int(item["question"][1:]), "operator": item["operator"]}
        if "option" in item:
            converted["option_id"] = int(item["option"][1:])
        if "text_answer" in item:
            converted["text_answer"] = item["text_answer"]
        items.append(converted)
    return {"match_all": condition["match_all"], "items": items}


def load_attempt_form(db, form):
    # Это внутреннее представление с правильными ответами. Участнику отдаём только whitelist ниже.
    data = build_form_response(db, form)
    for block in data["blocks"]:
        block["id"] = int(block.pop("key")[1:])
        block["condition"] = numeric_condition(block.get("condition"))
        for question in block["questions"]:
            question["id"] = int(question.pop("key")[1:])
            question["condition"] = numeric_condition(question.get("condition"))
            for option in question["options"]:
                option["id"] = int(option.pop("key")[1:])
            for position, rule in enumerate(question.get("finish_rules", []), 1):
                rule["id"] = int(rule.pop("key")[1:])
                rule["position"] = position
                rule["condition"] = numeric_condition(rule["condition"])
    data["grading_scale"] = [{"id": row.id, "min_percent": row.min_percent, "grade": row.grade, "message": row.message}
                             for row in db.scalars(select(GradingScale).where(GradingScale.form_id == form.id))]
    return data


def participant_form(data):
    result = {key: data[key] for key in ["id", "is_test", "title", "take_by_blocks", "allow_free_navigation", "question_order"]}
    result["blocks"] = []
    for block in data["blocks"]:
        output = {"id": block["id"], "title": block["title"], "questions": []}
        if not data["is_test"]:
            output["condition"] = block["condition"]
        for question in block["questions"]:
            item = {key: question[key] for key in ["id", "text", "type"]}
            item["options"] = [{"id": option["id"], "text": option["text"]} for option in question["options"]]
            if "image" in question:
                item["image"] = question["image"]
            if not data["is_test"]:
                item.update(is_answer_required=question["is_answer_required"], condition=question["condition"],
                            finish_rules=[{"id": rule["id"], "condition": rule["condition"]} for rule in question.get("finish_rules", [])])
            output["questions"].append(item)
        result["blocks"].append(output)
    return result
