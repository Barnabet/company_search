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
    ErrorResponse,
)
from services.conversation_service import ConversationService, MessageService
from services.agent_service import AgentService
from services.extraction_service import extract_criteria

# Create router
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    payload: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    """
    Start a new conversation with an initial user query.

    Workflow:
    1. Create conversation in database
    2. Add user's initial message
    3. Analyze completeness
    4. If complete: extract criteria and return result
    5. If incomplete: ask clarifying question

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

        # 3. Analyze completeness
        messages = [user_message]
        analysis = await AgentService.analyze_completeness(messages)

        # 4. Generate response
        if analysis.is_complete:
            # Extract criteria immediately
            try:
                extraction_result = extract_criteria(payload.initial_message)
                await ConversationService.complete(
                    db, conversation.id, extraction_result
                )
                assistant_content = (
                    "Parfait ! J'ai tous les critères nécessaires. "
                    "Voici les résultats de l'extraction."
                )
            except Exception as e:
                # Extraction failed, ask user for corrections
                print(f"Extraction failed: {e}")
                assistant_content = (
                    "J'ai rencontré un problème lors de l'extraction. "
                    "Pouvez-vous reformuler votre requête ?"
                )
                analysis.is_complete = False
        else:
            # Ask clarifying question
            assistant_content = await AgentService.generate_question(messages, analysis)

        # 5. Store assistant response
        assistant_message = await MessageService.create(
            db,
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
            analysis_result=analysis.model_dump() if not analysis.is_complete else None,
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

    Workflow:
    1. Validate conversation exists and is active
    2. Add user message
    3. Analyze completeness with full history
    4. If complete: merge conversation + extract criteria
    5. If incomplete: ask next question

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

        # 4. Analyze completeness
        analysis = await AgentService.analyze_completeness(messages)

        # 5. Generate response
        if analysis.is_complete:
            # Merge conversation into single query
            merged_query = await AgentService.merge_conversation(messages)

            # Extract criteria
            try:
                extraction_result = extract_criteria(merged_query)
                await ConversationService.complete(
                    db, conversation_id, extraction_result
                )
                assistant_content = (
                    "Parfait ! J'ai tous les critères nécessaires. "
                    "Lancement de la recherche..."
                )
            except Exception as e:
                # Extraction failed
                print(f"Extraction failed: {e}")
                assistant_content = (
                    "J'ai rencontré un problème lors de l'extraction. "
                    "Pouvez-vous vérifier les critères ?"
                )
                analysis.is_complete = False
        else:
            # Ask next question
            assistant_content = await AgentService.generate_question(messages, analysis)

        # 6. Store assistant response
        await MessageService.create(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            analysis_result=analysis.model_dump() if not analysis.is_complete else None,
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
