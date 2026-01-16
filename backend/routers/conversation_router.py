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

from typing import Dict, Any


def _merge_extractions(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two extraction results, preferring new values when present.

    This is used during refinement to combine the initial extraction
    with new criteria provided by the user.
    """
    merged = {}

    # List of criteria sections
    sections = ["localisation", "activite", "taille_entreprise", "criteres_financiers", "criteres_juridiques"]

    for section in sections:
        old_section = old.get(section, {})
        new_section = new.get(section, {})

        # If new section is present and has data, use it
        if new_section.get("present", False):
            merged[section] = new_section
        # Otherwise keep old section if it was present
        elif old_section.get("present", False):
            merged[section] = old_section
        else:
            # Neither has data, keep the structure
            merged[section] = new_section if new_section else old_section

    return merged


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
    3. LLM extracts criteria (or rejects if too vague)
    4. If extracted: query API for count, refine if > 500
    5. Return result

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
            # Query external API for company count
            api_response = await AgentService.process_with_api(
                agent_response.extraction_result,
                refinement_round=1
            )

            if api_response.action == "refine":
                # Too many results - ask for refinement, keep conversation active
                assistant_content = api_response.message
                # Store partial extraction for next round
                await ConversationService.update_extraction(
                    db, conversation.id, {
                        "partial_extraction": api_response.extraction_result,
                        "company_count": api_response.company_count,
                        "refinement_round": 1,
                        "naf_codes": api_response.naf_codes,
                    }
                )
            else:
                # Complete conversation with full results
                await ConversationService.complete(
                    db, conversation.id, {
                        "extraction": api_response.extraction_result,
                        "company_count": api_response.company_count,
                        "naf_codes": api_response.naf_codes,
                        "api_result": api_response.api_result,
                    }
                )
                assistant_content = api_response.message
        else:
            # Query too vague - rejected
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

    Workflow:
    1. Validate conversation exists and is active
    2. Add user message
    3. LLM extracts criteria from full history (or rejects if too vague)
    4. If extracted: query API for count, refine if > 500
    5. Return result

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
            # Check if we're in a refinement flow
            current_extraction = conversation.extraction_result or {}
            refinement_round = current_extraction.get("refinement_round", 0) + 1

            # Merge with previous extraction if exists
            if current_extraction.get("partial_extraction"):
                # Merge new extraction with previous partial extraction
                merged_extraction = _merge_extractions(
                    current_extraction.get("partial_extraction", {}),
                    agent_response.extraction_result or {}
                )
            else:
                merged_extraction = agent_response.extraction_result

            # Query external API for company count
            api_response = await AgentService.process_with_api(
                merged_extraction,
                refinement_round=refinement_round
            )

            if api_response.action == "refine":
                # Still too many results - ask for more refinement
                assistant_content = api_response.message
                # Update partial extraction
                await ConversationService.update_extraction(
                    db, conversation_id, {
                        "partial_extraction": api_response.extraction_result,
                        "company_count": api_response.company_count,
                        "refinement_round": refinement_round,
                        "naf_codes": api_response.naf_codes,
                    }
                )
            else:
                # Complete conversation with full results
                await ConversationService.complete(
                    db, conversation_id, {
                        "extraction": api_response.extraction_result,
                        "company_count": api_response.company_count,
                        "naf_codes": api_response.naf_codes,
                        "api_result": api_response.api_result,
                    }
                )
                assistant_content = api_response.message
        else:
            # Query too vague - rejected
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
