from app.services.scoring import normalize_text


def has_answer(answer):
    return bool(answer and (answer.get("option_ids") or normalize_text(answer.get("text"))))


def condition_matches(condition, answers):
    if condition is None:
        return True
    results = []
    for item in condition["items"]:
        answer = answers.get(item["question_id"], {})
        chosen = item.get("option_id") in (answer.get("option_ids") or [])
        text = normalize_text(answer.get("text"))
        expected = normalize_text(item.get("text_answer"))
        results.append({
            "chosen": chosen, "not_chosen": not chosen,
            "equals": bool(text) and text == expected,
            "contains": bool(text) and expected in text,
            "answered": has_answer(answer), "not_answered": not has_answer(answer),
        }[item["operator"]])
    return all(results) if condition["match_all"] else any(results)


def visible_questions(form, answers):
    """Возвращаем видимые вопросы и первое правило; скрытые ответы не попадают в контекст."""
    visible, known = [], {}
    triggered = None
    for block in form["blocks"]:
        if not form["is_test"] and not condition_matches(block.get("condition"), known):
            continue
        for question in block["questions"]:
            if not form["is_test"] and not condition_matches(question.get("condition"), known):
                continue
            visible.append(question)
            if question["type"] == "info":
                continue
            known[question["id"]] = answers.get(question["id"], {})
            if not form["is_test"] and triggered is None:
                for rule in sorted(question.get("finish_rules", []), key=lambda rule: rule.get("position", 0)):
                    if condition_matches(rule["condition"], known):
                        triggered = rule
                        break
            if triggered and not form["take_by_blocks"]:
                return visible, triggered
        if triggered:
            break
    return visible, triggered
