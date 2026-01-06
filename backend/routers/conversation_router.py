"""
Conversation API endpoints for the conversational agent.

Endpoints:
- POST /api/v1/conversations - Start new conversation
- POST /api/v1/conversations/{id}/messages - Send message
- GET /api/v1/conversations/{id} - Get conversation
- DELETE /api/v1/conversations/{id} - Delete conversation
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
)
from services.conversation_service import ConversationService, MessageService
from services.agent_service import AgentService

# Create router
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    payload: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    """
    Start a new conversation with an initial user query.

    Simplified workflow:
    1. Create conversation in database
    2. Add user's initial message
    3. Process with agent (ONE LLM call: decide extract or clarify)
    4. Return result

    Args:
        payload: Initial message from user
        db: Database session

    Returns:
        ConversationResponse: Conversation with messages and optional extraction result
    """
    try:
        # 1. Create conversation
        conversation = await ConversationService.create(db)

        # 2. Add user message
        user_message = await MessageService.create(
            db,
            conversation_id=conversation.id,
            role="user",
            content=payload.initial_message,
        )

        # 3. Process with agent (single LLM call)
        agent_response = await AgentService.process_message([user_message])

        # 4. Handle response
        if agent_response.action == "extract":
            # Complete conversation with extraction result
            await ConversationService.complete(
                db, conversation.id, agent_response.extraction_result
            )
            assistant_content = agent_response.message
        else:
            # Need clarification
            assistant_content = agent_response.message

        # 5. Store assistant response
        await MessageService.create(
            db,
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
        )

        # 6. Return conversation with messages
        await db.commit()
        conversation = await ConversationService.get_with_messages(db, conversation.id)
        return conversation

    except Exception as e:
        await db.rollback()
        print(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.post("/{conversation_id}/messages", response_model=ConversationResponse)
async def send_message(
    conversation_id: UUID, payload: MessageCreate, db: AsyncSession = Depends(get_db)
):
    """
    Send a message in an existing conversation.

    Simplified workflow:
    1. Validate conversation exists and is active
    2. Add user message
    3. Process with agent (ONE LLM call with full history)
    4. Return result

    Args:
        conversation_id: UUID of the conversation
        payload: User message content
        db: Database session

    Returns:
        ConversationResponse: Updated conversation with new messages
    """
    try:
        # 1. Validate conversation
        conversation = await ConversationService.get_with_messages(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.status.value != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Conversation is not active (status: {conversation.status.value})",
            )

        # 2. Add user message
        await MessageService.create(
            db, conversation_id=conversation_id, role="user", content=payload.content
        )

        # 3. Get full message history
        messages = await MessageService.get_by_conversation(db, conversation_id)

        # 4. Process with agent (single LLM call)
        agent_response = await AgentService.process_message(messages)

        # 5. Handle response
        if agent_response.action == "extract":
            # Complete conversation with extraction result
            await ConversationService.complete(
                db, conversation_id, agent_response.extraction_result
            )
            assistant_content = agent_response.message
        else:
            # Need more clarification
            assistant_content = agent_response.message

        # 6. Store assistant response
        await MessageService.create(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )

        # 7. Update last activity
        await ConversationService.touch(db, conversation_id)

        # 8. Return updated conversation
        await db.commit()
        conversation = await ConversationService.get_with_messages(db, conversation_id)
        return conversation

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a conversation with all its messages.

    Args:
        conversation_id: UUID of the conversation
        db: Database session

    Returns:
        ConversationResponse: Conversation with messages
    """
    conversation = await ConversationService.get_with_messages(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: UUID of the conversation
        db: Database session

    Returns:
        204 No Content on success
    """
    conversation = await ConversationService.get(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await ConversationService.delete(db, conversation_id)
    await db.commit()
    return None


@router.post("/{conversation_id}/reset", response_model=ConversationResponse)
async def reset_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Reset a conversation (clear messages, set back to active).

    Useful for starting over without creating a new conversation ID.

    Args:
        conversation_id: UUID of the conversation
        db: Database session

    Returns:
        ConversationResponse: Reset conversation
    """
    conversation = await ConversationService.get(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete all messages
    await MessageService.delete_by_conversation(db, conversation_id)

    # Reset status to active
    await ConversationService.update_status(db, conversation_id, "active")

    await db.commit()

    # Return empty conversation
    conversation = await ConversationService.get_with_messages(db, conversation_id)
    return conversation
