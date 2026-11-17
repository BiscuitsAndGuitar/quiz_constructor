"""Начальная схема: 18 таблиц и справочники.

Сгенерировано из SQLAlchemy metadata средствами Alembic без подключения к БД.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('condition_operators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operator', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operator')
    )
    op.create_table('question_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type')
    )
    op.create_table('tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_author', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table('forms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('is_test', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('public_code', sa.String(length=20), nullable=False),
        sa.Column('requires_login', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=True),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('take_by_blocks', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('allow_free_navigation', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('shuffle_questions', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('shuffle_answer_options', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('show_correct_answers', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('show_results_by_block', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_code')
    )
    op.create_index(op.f('ix_forms_author_id'), 'forms', ['author_id'], unique=False)
    op.create_table('images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=100), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_name')
    )
    op.create_table('library_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('is_test', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_library_blocks_owner_id'), 'library_blocks', ['owner_id'], unique=False)
    op.create_table('blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=True),
        sa.Column('library_block_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.CheckConstraint('(form_id IS NULL) <> (library_block_id IS NULL)', name='ck_blocks_owner'),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['library_block_id'], ['library_blocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('library_block_id')
    )
    op.create_index(op.f('ix_blocks_form_id'), 'blocks', ['form_id'], unique=False)
    op.create_table('grading_scale',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('min_percent', sa.Integer(), nullable=False),
        sa.Column('grade', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('library_block_tags',
        sa.Column('library_block_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['library_block_id'], ['library_blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('library_block_id', 'tag_id')
    )
    op.create_index(op.f('ix_library_block_tags_tag_id'), 'library_block_tags', ['tag_id'], unique=False)
    op.create_table('attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('attempt_key', sa.String(length=64), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('max_score', sa.Integer(), nullable=True),
        sa.Column('percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('grading_scale_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grading_scale_id'], ['grading_scale.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attempts_form_id'), 'attempts', ['form_id'], unique=False)
    op.create_index(op.f('ix_attempts_user_id'), 'attempts', ['user_id'], unique=False)
    op.create_table('questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=True),
        sa.Column('is_answer_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('allow_partial_scoring', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['block_id'], ['blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['type_id'], ['question_types.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('attempt_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('attempt_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('text_answer', sa.Text(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['attempt_id'], ['attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attempt_answers_attempt_id'), 'attempt_answers', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_attempt_answers_question_id'), 'attempt_answers', ['question_id'], unique=False)
    op.create_table('condition_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parent_group_id', sa.Integer(), nullable=True),
        sa.Column('match_all', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=True),
        sa.Column('question_id', sa.Integer(), nullable=True),
        sa.CheckConstraint('(parent_group_id IS NULL AND ((block_id IS NULL) <> (question_id IS NULL))) OR (parent_group_id IS NOT NULL AND block_id IS NULL AND question_id IS NULL)', name='ck_condition_groups_owner'),
        sa.ForeignKeyConstraint(['block_id'], ['blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_group_id'], ['condition_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('correct_text_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('question_choices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.String(length=500), nullable=False),
        sa.Column('is_correct', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('attempt_answer_choices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('attempt_answer_id', sa.Integer(), nullable=False),
        sa.Column('choice_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_answer_id'], ['attempt_answers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['choice_id'], ['question_choices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('conditions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('operator_id', sa.Integer(), nullable=False),
        sa.Column('choice_id', sa.Integer(), nullable=True),
        sa.Column('text_answer', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['choice_id'], ['question_choices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['condition_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['operator_id'], ['condition_operators.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    question_types = sa.table(
        "question_types", sa.column("type", sa.String(20)),
        sa.column("name", sa.String(50)),
    )
    op.bulk_insert(question_types, [
        {"type": "single", "name": "Один ответ"},
        {"type": "multiple", "name": "Несколько ответов"},
        {"type": "text", "name": "Текстовый ответ"},
        {"type": "info", "name": "Текст без вопроса"},
    ])
    condition_operators = sa.table(
        "condition_operators", sa.column("operator", sa.String(20)),
        sa.column("name", sa.String(50)),
    )
    op.bulk_insert(condition_operators, [
        {"operator": "chosen", "name": "выбран вариант"},
        {"operator": "not_chosen", "name": "не выбран вариант"},
        {"operator": "equals", "name": "равно"},
        {"operator": "contains", "name": "содержит"},
        {"operator": "answered", "name": "есть ответ"},
        {"operator": "not_answered", "name": "нет ответа"},
    ])


def downgrade():
    op.drop_table('conditions')
    op.drop_table('attempt_answer_choices')
    op.drop_table('question_choices')
    op.drop_table('correct_text_answers')
    op.drop_table('condition_groups')
    op.drop_index(op.f('ix_attempt_answers_question_id'), table_name='attempt_answers')
    op.drop_index(op.f('ix_attempt_answers_attempt_id'), table_name='attempt_answers')
    op.drop_table('attempt_answers')
    op.drop_table('questions')
    op.drop_index(op.f('ix_attempts_user_id'), table_name='attempts')
    op.drop_index(op.f('ix_attempts_form_id'), table_name='attempts')
    op.drop_table('attempts')
    op.drop_index(op.f('ix_library_block_tags_tag_id'), table_name='library_block_tags')
    op.drop_table('library_block_tags')
    op.drop_table('grading_scale')
    op.drop_index(op.f('ix_blocks_form_id'), table_name='blocks')
    op.drop_table('blocks')
    op.drop_index(op.f('ix_library_blocks_owner_id'), table_name='library_blocks')
    op.drop_table('library_blocks')
    op.drop_table('images')
    op.drop_index(op.f('ix_forms_author_id'), table_name='forms')
    op.drop_table('forms')
    op.drop_table('users')
    op.drop_table('tags')
    op.drop_table('question_types')
    op.drop_table('condition_operators')
