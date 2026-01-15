"""
Conversation service for CRUD operations on conversations and messages.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Conversation, Message, ConversationStatus, MessageRole


class ConversationService:
    """Service for managing conversations"""

    @staticmethod
    async def create(db: AsyncSession) -> Conversation:
        """
        Create a new conversation.

        Args:
            db: Database session

        Returns:
            Conversation: Newly created conversation
        """
        conversation = Conversation(
            status=ConversationStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get(db: AsyncSession, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get a conversation by ID.

        Args:
            db: Database session
            conversation_id: Conversation UUID

        Returns:
            Conversation or None if not found
        """
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_with_messages(
        db: AsyncSession, conversation_id: UUID
    ) -> Optional[Conversation]:
        """
        Get a conversation with all its messages eagerly loaded.

        Args:
            db: Database session
            conversation_id: Conversation UUID

        Returns:
            Conversation with messages or None if not found
        """
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        db: AsyncSession, conversation_id: UUID, status: ConversationStatus
    ) -> None:
        """
        Update conversation status.

        Args:
            db: Database session
            conversation_id: Conversation UUID
            status: New status
        """
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await db.flush()

    @staticmethod
    async def complete(
        db: AsyncSession, conversation_id: UUID, extraction_result: dict
    ) -> None:
        """
        Mark conversation as completed with extraction result.

        Args:
            db: Database session
            conversation_id: Conversation UUID
            extraction_result: Extracted search criteria
        """
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                status=ConversationStatus.COMPLETED,
                extraction_result=extraction_result,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await db.flush()

    @staticmethod
    async def touch(db: AsyncSession, conversation_id: UUID) -> None:
        """
        Update last_activity timestamp.

        Args:
            db: Database session
            conversation_id: Conversation UUID
        """
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_activity=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        await db.flush()

    @staticmethod
    async def update_extraction(
        db: AsyncSession, conversation_id: UUID, extraction_result: dict
    ) -> None:
        """
        Update extraction result without completing the conversation.

        Used during refinement to store partial extraction state.

        Args:
            db: Database session
            conversation_id: Conversation UUID
            extraction_result: Partial extraction data with refinement info
        """
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                extraction_result=extraction_result,
                updated_at=datetime.utcnow(),
            )
        )
        await db.flush()

    @staticmethod
    async def delete(db: AsyncSession, conversation_id: UUID) -> None:
        """
        Delete a conversation and all its messages.

        Args:
            db: Database session
            conversation_id: Conversation UUID
        """
        await db.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        await db.flush()

    @staticmethod
    async def list_active(
        db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """
        List active conversations.

        Args:
            db: Database session
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of active conversations
        """
        result = await db.execute(
            select(Conversation)
            .where(Conversation.status == ConversationStatus.ACTIVE)
            .order_by(Conversation.last_activity.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_by_status(db: AsyncSession) -> dict:
        """
        Count conversations by status.

        Args:
            db: Database session

        Returns:
            Dictionary with status counts
        """
        result = await db.execute(
            select(Conversation.status, func.count(Conversation.id))
            .group_by(Conversation.status)
        )
        return {status: count for status, count in result.all()}


class MessageService:
    """Service for managing messages"""

    @staticmethod
    async def create(
        db: AsyncSession,
        conversation_id: UUID,
        role: str,
        content: str,
        analysis_result: Optional[dict] = None,
    ) -> Message:
        """
        Create a new message in a conversation.

        Args:
            db: Database session
            conversation_id: Conversation UUID
            role: Message role (user, assistant, system)
            content: Message content
            analysis_result: Optional analysis metadata

        Returns:
            Message: Newly created message
        """
        # Get next sequence number
        result = await db.execute(
            select(func.coalesce(func.max(Message.sequence_number), -1) + 1).where(
                Message.conversation_id == conversation_id
            )
        )
        sequence_number = result.scalar()

        message = Message(
            conversation_id=conversation_id,
            role=MessageRole(role),
            content=content,
            created_at=datetime.utcnow(),
            sequence_number=sequence_number,
            analysis_result=analysis_result,
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_by_conversation(
        db: AsyncSession, conversation_id: UUID
    ) -> List[Message]:
        """
        Get all messages for a conversation, ordered by sequence.

        Args:
            db: Database session
            conversation_id: Conversation UUID

        Returns:
            List of messages ordered by sequence_number
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_last_n_messages(
        db: AsyncSession, conversation_id: UUID, n: int = 10
    ) -> List[Message]:
        """
        Get last N messages from a conversation.

        Args:
            db: Database session
            conversation_id: Conversation UUID
            n: Number of messages to retrieve

        Returns:
            List of last N messages ordered by sequence_number
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(n)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))  # Return in chronological order

    @staticmethod
    async def delete_by_conversation(db: AsyncSession, conversation_id: UUID) -> None:
        """
        Delete all messages in a conversation.

        Args:
            db: Database session
            conversation_id: Conversation UUID
        """
        await db.execute(
            delete(Message).where(Message.conversation_id == conversation_id)
        )
        await db.flush()

    @staticmethod
    async def count_by_conversation(db: AsyncSession, conversation_id: UUID) -> int:
        """
        Count messages in a conversation.

        Args:
            db: Database session
            conversation_id: Conversation UUID

        Returns:
            Number of messages
        """
        result = await db.execute(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id
            )
        )
        return result.scalar()
