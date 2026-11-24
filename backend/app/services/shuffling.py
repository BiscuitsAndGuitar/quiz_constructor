from copy import deepcopy
import random


def shuffled_form(form, rng=None):
    rng = rng if rng is not None else random.SystemRandom()
    result = deepcopy(form)
    for block in result["blocks"]:
        if form["is_test"] and form.get("shuffle_questions") and form["take_by_blocks"]:
            rng.shuffle(block["questions"])
        if form.get("shuffle_answer_options"):
            for question in block["questions"]:
                if question["type"] in {"single", "multiple"}:
                    rng.shuffle(question["options"])
    order = [question["id"] for block in result["blocks"] for question in block["questions"]]
    if form["is_test"] and form.get("shuffle_questions") and not form["take_by_blocks"]:
        rng.shuffle(order)
    result["question_order"] = order
    return result
