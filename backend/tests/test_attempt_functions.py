from copy import deepcopy
from decimal import Decimal
from random import Random

import pytest

from app.services.scoring import question_score, percent_score, select_grade, completion_message
from app.services.visibility import condition_matches, visible_questions
from app.services.shuffling import shuffled_form


def choice_question(kind="multiple", partial=False):
    return {"id": 1, "type": kind, "points": 5, "allow_partial_scoring": partial,
            "options": [{"id": 1, "is_correct": True}, {"id": 2, "is_correct": True},
                        {"id": 3, "is_correct": True}, {"id": 4, "is_correct": False}]}


@pytest.mark.parametrize("selected,partial,score", [([1, 2, 3], False, 5), ([1, 2], False, 0),
    ([1, 2, 3, 4], False, 0), ([1, 2], True, 3), ([1, 4], True, 0), ([4], True, 0), ([], True, 0)])
def test_multiple(selected, partial, score):
    assert question_score(choice_question(partial=partial), {"option_ids": selected}) == score


def test_single_text_info_and_empty():
    assert question_score(choice_question("single"), {"option_ids": [1]}) == 5
    assert question_score(choice_question("single"), {"option_ids": [4]}) == 0
    assert question_score(choice_question(), {}) == 0
    text = {"type": "text", "points": 4, "correct_text_answers": ["  МоСКва   город ", "1,5"]}
    assert question_score(text, {"text": "москва  ГОРОД"}) == 4
    assert question_score(text, {"text": " 1.5 "}) == 4
    assert question_score(text, {"text": " "}) == 0
    assert question_score({"type": "info", "points": 100}, {"text": "x"}) == 0


@pytest.mark.parametrize("score,grade", [(49, "2"), (50, "3"), (69, "3"), (70, "4"), (84, "4"), (85, "5")])
def test_grade_boundaries(score, grade):
    scale = [{"min_percent": percent, "grade": str(index + 2)} for index, percent in enumerate([0, 50, 70, 85])]
    assert select_grade(score, 100, scale)["grade"] == grade


def test_grade_without_rounding_and_zero_maximum():
    scale = [{"id": 1, "min_percent": 50, "grade": "3"}]
    assert percent_score(49999, 100000) == Decimal("50.00")
    assert select_grade(49999, 100000, scale) is None
    assert select_grade(0, 100, scale) is None
    assert select_grade(100, 100, []) is None
    assert percent_score(0, 0) == 0
    assert select_grade(0, 0, [{"id": 1, "min_percent": 0}, {"id": 2, "min_percent": 100}]) is None
    assert completion_message(form_message="Общее") == "Общее"


def cond(operator="answered", question_id=1, **value):
    return {"match_all": True, "items": [{"question_id": question_id, "operator": operator, **value}]}


@pytest.mark.parametrize("operator,value,present,missing", [
    ("chosen", {"option_id": 1}, True, False), ("not_chosen", {"option_id": 1}, False, True),
    ("equals", {"text_answer": "МОСКВА город"}, True, False), ("contains", {"text_answer": "СКВА   ГО"}, True, False),
    ("answered", {}, True, False), ("not_answered", {}, False, True)])
def test_all_operators(operator, value, present, missing):
    condition = cond(operator, **value)
    assert condition_matches(condition, {1: {"option_ids": [1], "text": " Москва   Город "}}) is present
    assert condition_matches(condition, {}) is missing


def form_blocks():
    return {"is_test": False, "take_by_blocks": False, "blocks": [
        {"id": 1, "questions": [{"id": 1, "type": "text"}, {"id": 2, "type": "text"}]},
        {"id": 2, "questions": [{"id": 3, "type": "text"}, {"id": 4, "type": "info"}]}]}


def test_visibility_top_down_hidden_answers_and_block():
    form = form_blocks()
    form["blocks"][0]["questions"][0]["condition"] = cond("answered", 99)
    form["blocks"][0]["questions"][1]["condition"] = cond("not_answered")
    form["blocks"][1]["condition"] = cond("answered")
    visible, rule = visible_questions(form, {1: {"text": "Не учитывать"}})
    assert [q["id"] for q in visible] == [2]
    assert rule is None
    condition = {"match_all": False, "items": [cond()["items"][0], cond("not_answered", 2)["items"][0]]}
    assert condition_matches(condition, {})
    condition["match_all"] = True
    assert not condition_matches(condition, {})


@pytest.mark.parametrize("by_blocks,ids", [(False, [1]), (True, [1, 2])])
def test_first_rule_and_block_cutoff(by_blocks, ids):
    form = form_blocks()
    form["take_by_blocks"] = by_blocks
    form["blocks"][0]["questions"][0]["finish_rules"] = [
        {"id": 10, "position": 2, "condition": cond()}, {"id": 11, "position": 1, "condition": cond()}]
    visible, rule = visible_questions(form, {1: {"text": "Да"}})
    assert [q["id"] for q in visible] == ids
    assert rule["id"] == 11


def test_hidden_rule_ignored_info_and_last_rule():
    form = form_blocks()
    first = form["blocks"][0]["questions"][0]
    first.update(condition=cond("answered", 99), finish_rules=[{"id": 1, "condition": cond("not_answered")}])
    last = form["blocks"][1]["questions"][-1]
    last["condition"] = cond("not_answered", 1)
    visible, rule = visible_questions(form, {1: {"text": "x"}, 4: {"text": "info"}})
    assert [q["id"] for q in visible] == [2, 3, 4] and rule is None
    last["type"] = "text"
    last["finish_rules"] = [{"id": 12, "condition": cond("answered", 4)}]
    assert visible_questions(form, {4: {"text": "x"}})[1]["id"] == 12


@pytest.mark.parametrize("is_test,by_blocks", [(False, False), (False, True), (True, False), (True, True)])
def test_shuffling(is_test, by_blocks):
    form = form_blocks()
    form.update(is_test=is_test, take_by_blocks=by_blocks, shuffle_questions=True, shuffle_answer_options=True)
    for block in form["blocks"]:
        for question in block["questions"]:
            question.update(type="single", options=[{"id": i} for i in range(8)])
    before = deepcopy(form)
    result = shuffled_form(form, Random(4))
    assert form == before
    assert set(result["question_order"]) == {1, 2, 3, 4}
    assert [b["id"] for b in result["blocks"]] == [1, 2]
    flat = [q["id"] for b in result["blocks"] for q in b["questions"]]
    if by_blocks or not is_test:
        assert result["question_order"] == flat
    if not is_test:
        assert flat == [1, 2, 3, 4]
    else:
        assert result["question_order"] != [1, 2, 3, 4]
    for block in result["blocks"]:
        for question in block["questions"]:
            assert {o["id"] for o in question["options"]} == set(range(8))
            assert [o["id"] for o in question["options"]] != list(range(8))
    form["blocks"][0]["questions"][0]["type"] = "info"
    assert {q["id"] for b in shuffled_form(form, Random(1))["blocks"] for q in b["questions"]} == {1, 2, 3, 4}


def test_message_chain():
    assert completion_message("Правило", "Оценка", "Форма") == "Правило"
    assert completion_message("", "Оценка", "Форма") == "Оценка"
    assert completion_message(None, "", "Форма") == "Форма"
    assert completion_message() == "Спасибо за участие!"
