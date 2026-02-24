"""fix button_click_logs.user_id foreign key to users.id

Revision ID: 0010
Revises: 0009
Create Date: 2026-02-18

Normalizes legacy databases where button_click_logs.user_id could be tied to
users.telegram_id (BIGINT). The migration remaps values to users.id, safely
casts user_id to INTEGER, nulls dangling references, and recreates the FK to
users.id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table('button_click_logs') or not _has_table('users'):
        return

    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        # Ошибка воспроизводилась в PostgreSQL старых инсталляций.
        return

    inspector = sa.inspect(conn)

    columns = {col['name']: col for col in inspector.get_columns('button_click_logs')}
    if 'user_id' not in columns:
        return

    user_id_type = str(columns['user_id']['type']).lower()

    user_fk = next(
        (
            fk
            for fk in inspector.get_foreign_keys('button_click_logs')
            if fk.get('constrained_columns') == ['user_id']
        ),
        None,
    )
    fk_name = user_fk.get('name') if user_fk else None
    fk_target = None
    if user_fk:
        referred_columns = user_fk.get('referred_columns') or []
        fk_target = referred_columns[0] if referred_columns else None

    needs_fix = not user_fk or fk_target != 'id' or user_id_type != 'integer'
    if not needs_fix:
        return

    # Legacy-case: значения user_id хранили telegram_id, переносим в users.id.
    if fk_target == 'telegram_id':
        op.execute(
            """
            UPDATE button_click_logs AS logs
            SET user_id = users.id::bigint
            FROM users
            WHERE logs.user_id = users.telegram_id
            """
        )

    # Удаляем существующий FK, чтобы безопасно чистить данные и менять тип.
    if fk_name:
        op.drop_constraint(fk_name, 'button_click_logs', type_='foreignkey')

    # Убираем значения, которые не сопоставляются с users.id.
    op.execute(
        """
        UPDATE button_click_logs AS logs
        SET user_id = NULL
        WHERE logs.user_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM users
              WHERE users.id::bigint = logs.user_id
          )
        """
    )

    # Безопасно приводим BIGINT -> INTEGER, невалидные значения зануляем.
    if user_id_type != 'integer':
        op.execute(
            """
            ALTER TABLE button_click_logs
            ALTER COLUMN user_id TYPE INTEGER
            USING CASE
                WHEN user_id IS NULL THEN NULL
                WHEN user_id BETWEEN -2147483648 AND 2147483647 THEN user_id::integer
                ELSE NULL
            END
            """
        )

    # Финальная чистка перед созданием корректного FK.
    op.execute(
        """
        UPDATE button_click_logs AS logs
        SET user_id = NULL
        WHERE logs.user_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM users
              WHERE users.id = logs.user_id
          )
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = 'button_click_logs'
                  AND constraint_name = 'button_click_logs_user_id_fkey'
            ) THEN
                ALTER TABLE button_click_logs
                ADD CONSTRAINT button_click_logs_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Откат для data-fix миграции не поддерживаем.
    return
