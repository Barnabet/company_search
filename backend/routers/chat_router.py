"""
Stateless chat endpoint for the conversational agent.

No database required - frontend manages conversation state.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.agent_service import AgentService, ActivityMatch


# ============================================================================
# Schemas
# ============================================================================

class ChatMessage(BaseModel):
    """A single message in the conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    """Request to process a chat conversation"""
    messages: List[ChatMessage] = Field(..., min_length=1, description="Conversation history")
    previous_extraction: Optional[Dict[str, Any]] = Field(None, description="Previous extraction for caching")
    previous_activity_matches: Optional[List["ActivityMatchResponse"]] = Field(None, description="Previous activity matches for caching")


class ActivityMatchResponse(BaseModel):
    """An activity match result with score"""
    activity: str = Field(..., description="Activity label")
    naf_codes: List[str] = Field(default_factory=list, description="Associated NAF codes")
    score: float = Field(..., description="Similarity score (0-1)")
    selected: bool = Field(False, description="Whether this match was selected by the agent")


class ChatResponse(BaseModel):
    """Response from the chat endpoint"""
    message: str = Field(..., description="Assistant's response message")
    extraction_result: Optional[Dict[str, Any]] = Field(None, description="Extracted search criteria")
    company_count: Optional[int] = Field(None, description="Number of matching companies (NAF-based)")
    count_semantic: Optional[int] = Field(None, description="Number of matching companies (semantic)")
    naf_codes: Optional[List[str]] = Field(None, description="Matched NAF codes")
    api_result: Optional[Dict[str, Any]] = Field(None, description="Full API response data")
    activity_matches: Optional[List[ActivityMatchResponse]] = Field(None, description="Activity matches with scores")


class UpdateSelectionRequest(BaseModel):
    """Request to update NAF selection and re-run search"""
    extraction_result: Dict[str, Any] = Field(..., description="Current extraction result")
    activity_matches: List[ActivityMatchResponse] = Field(..., description="Activity matches with updated selections")


class UpdateSelectionResponse(BaseModel):
    """Response from update selection endpoint"""
    company_count: int = Field(..., description="Number of matching companies")
    count_semantic: Optional[int] = Field(None, description="Number of matching companies (semantic)")
    naf_codes: List[str] = Field(..., description="Selected NAF codes")
    activity_matches: List[ActivityMatchResponse] = Field(..., description="Updated activity matches")


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat conversation and return the assistant's response.

    Stateless endpoint - frontend maintains conversation history.
    Send the full message history on each request.

    Flow:
    1. LLM extracts criteria from conversation (or rejects if too vague)
    2. If extracted: query API for company count
    3. Return response with extraction and count
    """
    try:
        # Convert to internal Message format for AgentService
        messages = []
        for msg in request.messages:
            message = type('Message', (), {
                'role': type('Role', (), {'value': msg.role})(),
                'content': msg.content,
            })()
            messages.append(message)

        # Get user query (last user message)
        user_query = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_query = msg.content
                break

        # Convert previous activity matches from request to internal format
        previous_activity_matches_internal = None
        if request.previous_activity_matches:
            previous_activity_matches_internal = [
                ActivityMatch(
                    activity=m.activity,
                    naf_codes=m.naf_codes,
                    score=m.score,
                    selected=m.selected
                )
                for m in request.previous_activity_matches
            ]

        # Process with agent (extraction + location matching)
        agent_response = await AgentService.process_message(
            messages,
            previous_extraction=request.previous_extraction
        )

        # If extraction succeeded, query the API
        if agent_response.action == "extract" and agent_response.extraction_result:
            # Format conversation history for response generation
            conversation_history = "\n".join([
                f"{'Utilisateur' if msg.role == 'user' else 'Agent'}: {msg.content}"
                for msg in request.messages
            ])

            api_response = await AgentService.process_with_api(
                extraction_result=agent_response.extraction_result,
                user_query=user_query,
                location_corrections=agent_response.location_corrections,
                previous_extraction=request.previous_extraction,
                previous_activity_matches=previous_activity_matches_internal,
                conversation_history=conversation_history
            )

            # Convert activity matches to response format
            activity_matches = None
            if api_response.activity_matches:
                activity_matches = [
                    ActivityMatchResponse(
                        activity=m.activity,
                        naf_codes=m.naf_codes,
                        score=m.score,
                        selected=m.selected
                    )
                    for m in api_response.activity_matches
                ]

            return ChatResponse(
                message=api_response.message,
                extraction_result=api_response.extraction_result,
                company_count=api_response.company_count,
                count_semantic=api_response.count_semantic,
                naf_codes=api_response.naf_codes,
                api_result=api_response.api_result,
                activity_matches=activity_matches,
            )
        else:
            # Query too vague - rejected
            return ChatResponse(
                message=agent_response.message,
                extraction_result=None,
                company_count=None,
                count_semantic=None,
                naf_codes=None,
                api_result=None,
                activity_matches=None,
            )

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.post("/update-selection", response_model=UpdateSelectionResponse)
async def update_selection(request: UpdateSelectionRequest) -> UpdateSelectionResponse:
    """
    Update NAF code selection and re-run the company search.

    Called when user clicks to select/deselect activity matches.
    """
    from services.api_transformer import transform_extraction_to_api_request
    from services.company_api_client import get_company_api_client, CompanyAPIError

    try:
        # Collect NAF codes from selected activities
        naf_codes = []
        for match in request.activity_matches:
            if match.selected:
                for code in match.naf_codes:
                    if code not in naf_codes:
                        naf_codes.append(code)

        # Get original activity text for semantic search
        activite = request.extraction_result.get("activite", {})
        original_activity_text = activite.get("activite_entreprise")

        # Transform to API format
        api_request = transform_extraction_to_api_request(
            request.extraction_result,
            naf_codes,
            original_activity_text=original_activity_text
        )

        # Call external API
        api_client = get_company_api_client()
        api_response = api_client.count_companies(api_request)

        return UpdateSelectionResponse(
            company_count=api_response.count,
            count_semantic=api_response.count_semantic,
            naf_codes=naf_codes,
            activity_matches=request.activity_matches,
        )

    except CompanyAPIError as e:
        print(f"Error in update-selection endpoint: {e}")
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")
    except Exception as e:
        print(f"Error in update-selection endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Update selection failed: {str(e)}")
