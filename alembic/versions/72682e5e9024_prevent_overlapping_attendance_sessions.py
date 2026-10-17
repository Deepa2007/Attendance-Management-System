"""prevent overlapping attendance sessions

Revision ID: 72682e5e9024
Revises: b9c14dcd58d6
Create Date: 2026-10-15 17:27:44.842053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72682e5e9024'
down_revision: Union[str, Sequence[str], None] = 'b9c14dcd58d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Ensure PostgreSQL has the GiST operator support we need.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # Prevent overlapping attendance sessions for the same employee.
    # An active session (NULL checkout) extends to infinity.
    # The [) range allows adjacent sessions without overlap.
    op.execute("""
        ALTER TABLE attendance_sessions
        ADD CONSTRAINT ex_attendance_sessions_no_overlap
        EXCLUDE USING gist (
            employee_id WITH =,
            (
                tstzrange(
                    checked_in_at,
                    COALESCE(
                        checked_out_at,
                        'infinity'::timestamptz
                    ),
                    '[)'
                )
            ) WITH &&
        )
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE attendance_sessions
        DROP CONSTRAINT IF EXISTS ex_attendance_sessions_no_overlap
    """)

