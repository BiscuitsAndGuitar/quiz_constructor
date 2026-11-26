from copy import deepcopy
from pydantic import ValidationError

from sqlalchemy import select, delete, or_, func
from sqlalchemy.dialects.postgresql import insert
from app.models import LibraryBlock, LibraryBlockTag, Tag, Block, User, Question, QuestionType
from app.schemas.forms import FormSave
from app.services.form_validation import InvalidFormError
from app.services.block_storage import read_blocks, validate_blocks, write_blocks


def normalize_tags(tags):
    result = set()
    for tag in tags:
        tag = " ".join(tag.split()).lower()
        if len(tag) > 30:
            raise InvalidFormError("Тег должен быть не длиннее 30 символов")
        if tag:
            result.add(tag)
    if len(result) > 10:
        raise InvalidFormError("Можно указать не больше 10 тегов")
    return sorted(result)


def prepare_library_block(block):
    result = deepcopy(block)
    warnings = []
    if result.pop("condition", None) is not None:
        warnings.append("Условие показа блока не сохранено")
    earlier = {}
    removed = 0
    had_rules = False
    for question in result["questions"]:
        condition = question.get("condition")
        if condition is not None:
            valid = True
            for item in condition["items"]:
                source = earlier.get(item["question"])
                if (source is None or source["type"] == "info" or
                    (item.get("option") is not None and item["option"] not in {o["key"] for o in source.get("options", [])})):
                    valid = False
                    break
            if not valid:
                question.pop("condition", None)
                removed += 1
        had_rules = bool(question.pop("finish_rules", [])) or had_rules
        earlier[question["key"]] = question
    if removed:
        warnings.append(f"У вопросов ({removed} шт.) удалены условия с недопустимыми ссылками: вне блока, на не более ранние вопросы, текст без вопроса или чужие варианты")
    if had_rules:
        warnings.append("Правила досрочного завершения не сохранены")
    return result, warnings


def visible_library(user_id):
    return or_(LibraryBlock.owner_id == user_id, LibraryBlock.is_public.is_(True))


def tags_by_block(db, ids):
    result = {id: [] for id in ids}
    for id, name in db.execute(select(LibraryBlockTag.library_block_id, Tag.name)
                              .join(Tag).where(LibraryBlockTag.library_block_id.in_(ids)).order_by(Tag.name)):
        result[id].append(name)
    return result


def list_items(db, user_id, *, query=None, tag=None, scope="all", is_test=None, limit=20, offset=0, id=None):
    question_count = (select(func.count(Question.id)).join(QuestionType)
                      .where(Question.block_id == Block.id, QuestionType.type != "info").correlate(Block).scalar_subquery())
    statement = (select(LibraryBlock, Block.title, User.name, question_count)
                 .join(Block, Block.library_block_id == LibraryBlock.id).join(User, User.id == LibraryBlock.owner_id)
                 .where(visible_library(user_id)))
    if id is not None:
        statement = statement.where(LibraryBlock.id == id)
    if scope == "mine":
        statement = statement.where(LibraryBlock.owner_id == user_id)
    elif scope == "public":
        statement = statement.where(LibraryBlock.owner_id != user_id, LibraryBlock.is_public.is_(True))
    if is_test is not None:
        statement = statement.where(LibraryBlock.is_test == is_test)
    tagged = select(LibraryBlockTag.library_block_id).join(Tag)
    if tag is not None:
        statement = statement.where(LibraryBlock.id.in_(tagged.where(Tag.name == " ".join(tag.split()).lower())))
    if query:
        # autoescape: проценты и подчёркивания пользователя — обычные символы поиска.
        value = query.lower()
        statement = statement.where(or_(func.lower(Block.title).contains(value, autoescape=True),
            func.lower(LibraryBlock.description).contains(value, autoescape=True),
            LibraryBlock.id.in_(tagged.where(func.lower(Tag.name).contains(value, autoescape=True)))))
    rows = db.execute(statement.order_by(LibraryBlock.created_at.desc(), LibraryBlock.id.desc()).limit(limit).offset(offset)).all()
    tags = tags_by_block(db, [row[0].id for row in rows])
    return [{"id": item.id, "title": title, "description": item.description, "is_test": item.is_test,
             "is_public": item.is_public, "is_mine": item.owner_id == user_id, "owner_name": owner,
             "tags": tags[item.id], "questions_count": count, "created_at": item.created_at}
            for item, title, owner, count in rows]


def sample_block(db, item):
    return db.scalars(select(Block).where(Block.library_block_id == item.id)).one()


def library_keys(block):
    result = deepcopy(block)
    result["key"] = "b1"
    keys = {}
    option_number = 0
    for number, question in enumerate(result["questions"], 1):
        keys[question["key"]] = f"q{number}"
        question["key"] = f"q{number}"
        for option in question["options"]:
            option_number += 1
            keys[option["key"]] = f"o{option_number}"
            option["key"] = f"o{option_number}"
    for question in result["questions"]:
        for item in (question.get("condition") or {}).get("items", []):
            item["question"] = keys[item["question"]]
            if item.get("option") is not None:
                item["option"] = keys[item["option"]]
    return result


def get_details(db, item):
    block = library_keys(read_blocks(db, [sample_block(db, item)], item.is_test)[0])
    return {"id": item.id, "title": block["title"], "description": item.description,
            "is_test": item.is_test, "is_public": item.is_public,
            "tags": tags_by_block(db, [item.id])[item.id], "block": block}


def save_tags(db, id, names):
    db.execute(delete(LibraryBlockTag).where(LibraryBlockTag.library_block_id == id))
    for name in names:
        # UNIQUE и ON CONFLICT защищают от одновременного создания одинакового тега.
        db.execute(insert(Tag).values(name=name).on_conflict_do_nothing(index_elements=[Tag.name]))
        tag_id = db.scalar(select(Tag.id).where(Tag.name == name))
        db.add(LibraryBlockTag(library_block_id=id, tag_id=tag_id))


def create_library_block(db, user_id, data):
    try:
        raw = data.block.model_dump(exclude_unset=True)
        raw["title"] = data.title
        if not raw.get("questions"):
            raise InvalidFormError("В блоке должен быть хотя бы один вопрос или текст без вопроса")
        if data.is_test and (raw.get("condition") or any(q.get("condition") or q.get("finish_rules") for q in raw["questions"])):
            raise InvalidFormError("Условия показа и правила завершения есть только у опросов")
        block, warnings = prepare_library_block(raw)
        # Повторно используем проверки черновика, включая ключи и типы полей.
        try:
            form = FormSave(title=data.title, blocks=[block])
        except ValidationError as error:
            raise InvalidFormError(error.errors()[0]["msg"]) from None
        operator_ids = validate_blocks(db, form, data.is_test)
        item = LibraryBlock(owner_id=user_id, is_test=data.is_test, description=data.description, is_public=data.is_public)
        db.add(item)
        db.flush()
        write_blocks(db, form.blocks, item.is_test, operator_ids, library_block_id=item.id)
        save_tags(db, item.id, data.tags)
        result = {"id": item.id, "title": data.title, "is_test": item.is_test, "is_public": item.is_public,
                  "tags": data.tags, "warnings": warnings}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def update_library_block(db, item, data):
    try:
        sample_block(db, item).title = data.title
        item.description = data.description
        item.is_public = data.is_public
        save_tags(db, item.id, data.tags)
        db.flush()
        result = list_items(db, item.owner_id, id=item.id)[0]
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def delete_library_block(db, item):
    try:
        db.delete(item)
        db.commit()
    except Exception:
        db.rollback()
        raise


def list_tags(db, user_id, query=None):
    count = func.count(LibraryBlockTag.library_block_id)
    statement = (select(Tag.name, count).join(LibraryBlockTag).join(LibraryBlock)
                 .where(visible_library(user_id)))
    if query:
        statement = statement.where(func.lower(Tag.name).startswith(query.lower(), autoescape=True))
    return [{"name": name, "count": total} for name, total in db.execute(
        statement.group_by(Tag.id, Tag.name).order_by(count.desc(), Tag.name).limit(20))]
