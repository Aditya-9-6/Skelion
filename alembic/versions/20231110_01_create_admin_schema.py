'''alembic revision --autogenerate -m "create admin schema"'''

from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '20231110_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('github_user_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('login_snapshot', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    # admin_sessions table (append‑only)
    op.create_table(
        'admin_sessions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('github_user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('session_token_hash', sa.String(), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('ip', sa.String(), nullable=True),
        sa.Column('user_agent_hash', sa.String(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('step_up_until', sa.DateTime(), nullable=True),
    )
    # Append‑only trigger for admin_sessions
    op.execute(
        """
        CREATE TRIGGER admin_sessions_no_update BEFORE UPDATE ON admin_sessions
        BEGIN SELECT RAISE(ABORT, 'admin_sessions is append‑only'); END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER admin_sessions_no_delete BEFORE DELETE ON admin_sessions
        BEGIN SELECT RAISE(ABORT, 'admin_sessions is append‑only'); END;
        """
    )

    # admin_factors table (append‑only)
    op.create_table(
        'admin_factors',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('github_user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('type', sa.String(), nullable=False, index=True),
        sa.Column('credential_id', sa.String(), nullable=True, index=True),
        sa.Column('secret_ref', sa.String(), nullable=True),
        sa.Column('last4', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
    )
    op.execute(
        """
        CREATE TRIGGER admin_factors_no_update BEFORE UPDATE ON admin_factors
        BEGIN SELECT RAISE(ABORT, 'admin_factors is append‑only'); END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER admin_factors_no_delete BEFORE DELETE ON admin_factors
        BEGIN SELECT RAISE(ABORT, 'admin_factors is append‑only'); END;
        """
    )

    # audit_log table (append‑only)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('ts', sa.DateTime(), nullable=False, default=datetime.utcnow, index=True),
        sa.Column('actor_github_id', sa.Integer(), nullable=False, index=True),
        sa.Column('action', sa.String(), nullable=False, index=True),
        sa.Column('target_type', sa.String(), nullable=False, index=True),
        sa.Column('target_id', sa.String(), nullable=True),
        sa.Column('before', sa.JSON(), nullable=True),
        sa.Column('after', sa.JSON(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('ip', sa.String(), nullable=True),
        sa.Column('user_agent_hash', sa.String(), nullable=True),
        sa.Column('request_id', sa.String(), nullable=True),
        sa.Column('stepped_up_at', sa.DateTime(), nullable=True),
        sa.Column('prev_hash', sa.String(), nullable=True),
        sa.Column('row_hash', sa.String(), nullable=True),
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log
        BEGIN SELECT RAISE(ABORT, 'audit_log is append‑only'); END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log
        BEGIN SELECT RAISE(ABORT, 'audit_log is append‑only'); END;
        """
    )


def downgrade():
    # Drop triggers first (SQLite drops them automatically with table drop, but explicit for safety)
    op.execute('DROP TRIGGER IF EXISTS admin_sessions_no_update')
    op.execute('DROP TRIGGER IF EXISTS admin_sessions_no_delete')
    op.execute('DROP TRIGGER IF EXISTS admin_factors_no_update')
    op.execute('DROP TRIGGER IF EXISTS admin_factors_no_delete')
    op.execute('DROP TRIGGER IF EXISTS audit_log_no_update')
    op.execute('DROP TRIGGER IF EXISTS audit_log_no_delete')
    op.drop_table('audit_log')
    op.drop_table('admin_factors')
    op.drop_table('admin_sessions')
    op.drop_table('admin_users')
