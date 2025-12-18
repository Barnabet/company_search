"""
Database models for conversational company search.

Models:
- Conversation: Represents a multi-turn conversation session
- Message: Individual messages within a conversation
"""

import enum
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base

# ============================================================================
# Enums
# ============================================================================

class ConversationStatus(str, enum.Enum):
    """Status of a conversation"""
    ACTIVE = "active"  # Conversation ongoing, collecting information
    EXTRACTING = "extracting"  # Running criteria extraction
    COMPLETED = "completed"  # Extraction successful, ready for search
    ABANDONED = "abandoned"  # User left (timeout)


class MessageRole(str, enum.Enum):
    """Role of message sender"""
    USER = "user"  # Message from user
    ASSISTANT = "assistant"  # Message from AI agent
    SYSTEM = "system"  # System message (optional)

# ============================================================================
# Models
# ============================================================================

class Conversation(Base):
    """
    Represents a conversation session for company search criteria collection.

    A conversation consists of multiple messages exchanged between the user
    and the AI agent, culminating in extracted search criteria.
    """

    __tablename__ = "conversations"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Status
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus),
        default=ConversationStatus.ACTIVE,
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    # Session management
    last_activity: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Final extraction result (stored as JSON when completed)
    extraction_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    # Future: User tracking (for authentication)
    # user_id: Mapped[uuid.UUID | None] = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey('users.id'),
    #     nullable=True
    # )

    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.sequence_number"
    )

    # Indexes
    __table_args__ = (
        Index('idx_conversation_status', 'status'),
        Index('idx_conversation_last_activity', 'last_activity'),
        Index('idx_conversation_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, status={self.status}, messages={len(self.messages)})>"


class Message(Base):
    """
    Represents a single message in a conversation.

    Messages are ordered by sequence_number within a conversation.
    """

    __tablename__ = "messages"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign Key
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('conversations.id', ondelete='CASCADE'),
        nullable=False
    )

    # Message data
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # Optional: Store analysis result from agent (for debugging/analytics)
    analysis_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )

    # Indexes
    __table_args__ = (
        Index('idx_message_conversation_seq', 'conversation_id', 'sequence_number'),
        Index('idx_message_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, seq={self.sequence_number})>"
