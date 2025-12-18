"""Initial schema for conversations and messages

Revision ID: 001_initial
Revises:
Create Date: 2025-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE conversationstatus AS ENUM ('active', 'extracting', 'completed', 'abandoned')")
    op.execute("CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system')")

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('active', 'extracting', 'completed', 'abandoned', name='conversationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('extraction_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for conversations
    op.create_index('idx_conversation_status', 'conversations', ['status'])
    op.create_index('idx_conversation_last_activity', 'conversations', ['last_activity'])
    op.create_index('idx_conversation_created_at', 'conversations', ['created_at'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('analysis_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for messages
    op.create_index('idx_message_conversation_seq', 'messages', ['conversation_id', 'sequence_number'])
    op.create_index('idx_message_created_at', 'messages', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_message_created_at', table_name='messages')
    op.drop_index('idx_message_conversation_seq', table_name='messages')
    op.drop_index('idx_conversation_created_at', table_name='conversations')
    op.drop_index('idx_conversation_last_activity', table_name='conversations')
    op.drop_index('idx_conversation_status', table_name='conversations')

    # Drop tables
    op.drop_table('messages')
    op.drop_table('conversations')

    # Drop enum types
    op.execute('DROP TYPE messagerole')
    op.execute('DROP TYPE conversationstatus')
