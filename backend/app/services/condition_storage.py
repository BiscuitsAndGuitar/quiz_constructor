from sqlalchemy import or_, select

from app.models import Condition, ConditionGroup, ConditionOperator, EarlyFinishRule


def save_conditions(db, blocks, block_ids, question_ids, choice_ids, operator_ids):
    pending = []
    for block in blocks:
        pending.append((block.condition, {"block_id": block_ids[block.key]}))
        for question in block.questions:
            pending.append((question.condition, {"question_id": question_ids[question.key]}))
            # Позиции назначаются сервером строго по списку, клиент их не задаёт.
            for position, rule in enumerate(question.finish_rules, 1):
                stored = EarlyFinishRule(question_id=question_ids[question.key],
                                         message=rule.message, position=position)
                db.add(stored)
                db.flush()
                pending.append((rule.condition, {"early_finish_rule_id": stored.id}))
    # Все вопросы, варианты и правила уже получили id до создания ссылок.
    for condition, owner in pending:
        if condition is None:
            continue
        group = ConditionGroup(match_all=condition.match_all, **owner)
        db.add(group)
        db.flush()
        for item in condition.items:
            db.add(Condition(group_id=group.id, question_id=question_ids[item.question],
                             operator_id=operator_ids[item.operator],
                             choice_id=choice_ids[item.option] if item.option is not None else None,
                             text_answer=item.text_answer))


def add_conditions_to_response(db, result):
    blocks = {int(block["key"][1:]): block for block in result["blocks"]}
    questions = {int(question["key"][1:]): question
                 for block in result["blocks"] for question in block["questions"]}
    for block in blocks.values():
        block["condition"] = None
    for question in questions.values():
        question.update(condition=None, finish_rules=[])
    rules = {}
    for rule in db.scalars(select(EarlyFinishRule).where(EarlyFinishRule.question_id.in_(questions))
                           .order_by(EarlyFinishRule.position, EarlyFinishRule.id)):
        item = {"key": f"r{rule.id}", "message": rule.message, "condition": None}
        rules[rule.id] = item
        questions[rule.question_id]["finish_rules"].append(item)
    groups = db.scalars(select(ConditionGroup).where(or_(
        ConditionGroup.block_id.in_(blocks), ConditionGroup.question_id.in_(questions),
        ConditionGroup.early_finish_rule_id.in_(rules))).order_by(ConditionGroup.id)).all()
    items = {}
    for condition, operator in db.execute(
        select(Condition, ConditionOperator.operator).join(ConditionOperator)
        .where(Condition.group_id.in_([group.id for group in groups])).order_by(Condition.id)
    ):
        item = {"question": f"q{condition.question_id}", "operator": operator}
        if condition.choice_id is not None:
            item["option"] = f"o{condition.choice_id}"
        if condition.text_answer is not None:
            item["text_answer"] = condition.text_answer
        items.setdefault(condition.group_id, []).append(item)
    for group in groups:
        if group.block_id is not None:
            owner = blocks[group.block_id]
        elif group.question_id is not None:
            owner = questions[group.question_id]
        else:
            owner = rules[group.early_finish_rule_id]
        owner["condition"] = {"match_all": group.match_all, "items": items.get(group.id, [])}
