from app import models
from app.database import Base


def test_table_names():
    expected = {
        "users", "forms", "blocks", "questions", "question_types",
        "question_choices", "correct_text_answers", "images", "grading_scale",
        "condition_groups", "conditions", "condition_operators", "attempts",
        "attempt_answers", "attempt_answer_choices", "library_blocks", "tags",
        "library_block_tags", "early_finish_rules",
    }
    assert set(Base.metadata.tables) == expected
    assert len(Base.metadata.tables) == 19
