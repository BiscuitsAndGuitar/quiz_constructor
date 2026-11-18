"""Правила досрочного завершения и сообщения на странице завершения.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('early_finish_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_early_finish_rules_question_id'), 'early_finish_rules', ['question_id'], unique=False)
    op.add_column('attempts', sa.Column('early_finish_rule_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_attempts_early_finish_rule_id', 'attempts', 'early_finish_rules', ['early_finish_rule_id'], ['id'], ondelete='SET NULL')
    op.add_column('condition_groups', sa.Column('early_finish_rule_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_condition_groups_early_finish_rule_id', 'condition_groups', 'early_finish_rules', ['early_finish_rule_id'], ['id'], ondelete='CASCADE')
    # Alembic не обнаруживает изменение CHECK автоматически.
    op.drop_constraint('ck_condition_groups_owner', 'condition_groups', type_='check')
    op.create_check_constraint(
        'ck_condition_groups_owner',
        'condition_groups',
        '(parent_group_id IS NULL AND '
        '(CASE WHEN block_id IS NOT NULL THEN 1 ELSE 0 END + '
        'CASE WHEN question_id IS NOT NULL THEN 1 ELSE 0 END + '
        'CASE WHEN early_finish_rule_id IS NOT NULL THEN 1 ELSE 0 END = 1)) OR '
        '(parent_group_id IS NOT NULL AND block_id IS NULL AND question_id IS NULL '
        'AND early_finish_rule_id IS NULL)',
    )
    op.add_column('forms', sa.Column('completion_message', sa.Text(), nullable=True))
    op.add_column('grading_scale', sa.Column('message', sa.Text(), nullable=True))


def downgrade():
    # Каскад удаляет только условия новых правил, включая вложенные группы.
    # Группы показа блоков/вопросов сохраняются и проходят старый CHECK.
    op.execute('DELETE FROM early_finish_rules')
    op.drop_column('grading_scale', 'message')
    op.drop_column('forms', 'completion_message')
    op.drop_constraint('ck_condition_groups_owner', 'condition_groups', type_='check')
    op.drop_constraint('fk_condition_groups_early_finish_rule_id', 'condition_groups', type_='foreignkey')
    op.drop_column('condition_groups', 'early_finish_rule_id')
    op.create_check_constraint(
        'ck_condition_groups_owner',
        'condition_groups',
        '(parent_group_id IS NULL AND ((block_id IS NULL) <> (question_id IS NULL))) '
        'OR (parent_group_id IS NOT NULL AND block_id IS NULL AND question_id IS NULL)',
    )
    op.drop_constraint('fk_attempts_early_finish_rule_id', 'attempts', type_='foreignkey')
    op.drop_column('attempts', 'early_finish_rule_id')
    op.drop_index(op.f('ix_early_finish_rules_question_id'), table_name='early_finish_rules')
    op.drop_table('early_finish_rules')
