"""
Stateless chat endpoint for the conversational agent.

No database required - frontend manages conversation state.
"""

import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Process a chat conversation and stream the assistant's response.

    Uses Server-Sent Events (SSE) format.
    First sends metadata (extraction, count, etc.), then streams the message.

    Event types:
    - metadata: JSON with extraction_result, company_count, naf_codes, activity_matches
    - content: Text chunk of the assistant's message
    - done: Stream complete
    - error: Error occurred
    """
    async def generate_stream() -> AsyncGenerator[str, None]:
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

            # If rejected (too vague), send rejection message and done
            if agent_response.action != "extract" or not agent_response.extraction_result:
                yield f"event: metadata\ndata: {json.dumps({'rejected': True})}\n\n"
                yield f"event: content\ndata: {json.dumps(agent_response.message)}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

            # Format conversation history for response generation
            conversation_history = "\n".join([
                f"{'Utilisateur' if msg.role == 'user' else 'Agent'}: {msg.content}"
                for msg in request.messages
            ])

            # Import services for API processing
            from services.activity_matcher import get_activity_matcher
            from services.api_transformer import transform_extraction_to_api_request
            from services.company_api_client import get_company_api_client, CompanyAPIError

            extraction_result = agent_response.extraction_result
            location_corrections = agent_response.location_corrections

            naf_codes = []
            company_count = 0
            count_semantic = 0
            original_activity_text = None
            activity_matches = []

            # Process activity matching (Step 1 & 2)
            activite = extraction_result.get("activite", {})
            activity_display = activite.get("activite_entreprise")
            mots_cles = activite.get("mots_cles")

            previous_mots_cles = None
            if request.previous_extraction:
                previous_activite = request.previous_extraction.get("activite", {})
                previous_mots_cles = previous_activite.get("mots_cles")

            activity_changed = mots_cles != previous_mots_cles

            if mots_cles:
                original_activity_text = activity_display or mots_cles
                print(f"[Stream] Activity search: mots_cles='{mots_cles}', changed={activity_changed}")

                if not activity_changed and previous_activity_matches_internal:
                    print(f"[Stream] Using cached activity matches")
                    activity_matches = previous_activity_matches_internal
                    for match in activity_matches:
                        if match.selected:
                            for code in match.naf_codes:
                                if code not in naf_codes:
                                    naf_codes.append(code)
                else:
                    print(f"[Stream] Running activity matcher...")
                    activity_matcher = await get_activity_matcher()
                    matches = activity_matcher.find_similar_activities(mots_cles, top_k=5, threshold=0.3)
                    print(f"[Stream] Found {len(matches)} activity matches")

                    print(f"[Stream] Running NAF selection LLM...")
                    selected_indices, explanation, no_good_match = AgentService._select_naf_codes(
                        mots_cles, matches
                    )
                    print(f"[Stream] NAF selection complete: indices={selected_indices}")

                    for i, (activity, score, codes) in enumerate(matches):
                        is_selected = i in selected_indices and not no_good_match
                        activity_matches.append(ActivityMatch(
                            activity=activity,
                            naf_codes=codes,
                            score=score,
                            selected=is_selected
                        ))
                        if is_selected:
                            for code in codes:
                                if code not in naf_codes:
                                    naf_codes.append(code)

            # Transform to API format and call external API
            api_request = transform_extraction_to_api_request(
                extraction_result,
                naf_codes,
                original_activity_text=original_activity_text
            )

            try:
                api_client = get_company_api_client()
                api_response = api_client.count_companies(api_request)
                company_count = api_response.count
                count_semantic = api_response.count_semantic
            except CompanyAPIError as e:
                print(f"[Stream] API error: {e}")
                company_count = None
                count_semantic = None

            # Convert activity matches to response format
            activity_matches_response = [
                {
                    "activity": m.activity,
                    "naf_codes": m.naf_codes,
                    "score": m.score,
                    "selected": m.selected
                }
                for m in activity_matches
            ]

            # Send metadata first
            metadata = {
                "extraction_result": extraction_result,
                "company_count": company_count,
                "count_semantic": count_semantic,
                "naf_codes": naf_codes if naf_codes else None,
                "activity_matches": activity_matches_response if activity_matches_response else None,
            }
            yield f"event: metadata\ndata: {json.dumps(metadata, ensure_ascii=False)}\n\n"

            # Stream the response message
            if user_query and activity_matches and company_count is not None:
                try:
                    async for chunk in AgentService._generate_contextual_response_stream(
                        user_query=user_query,
                        company_count=company_count,
                        extraction_result=extraction_result,
                        activity_matches=activity_matches,
                        location_corrections=location_corrections,
                        conversation_history=conversation_history
                    ):
                        yield f"event: content\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                except Exception as stream_error:
                    print(f"[Stream] Error during streaming: {stream_error}")
                    import traceback
                    traceback.print_exc()
                    yield f"event: content\ndata: {json.dumps(f'Erreur: {stream_error}', ensure_ascii=False)}\n\n"
            else:
                # Fallback message
                print(f"[Stream] Using fallback message (user_query={bool(user_query)}, activity_matches={bool(activity_matches)}, count={company_count})")
                if company_count is None:
                    message = "Critères extraits, mais impossible de contacter la base de données."
                elif company_count == 0:
                    message = "Aucune entreprise ne correspond à ces critères."
                elif company_count <= 500:
                    message = f"J'ai trouvé {company_count} entreprises."
                else:
                    message = f"J'ai trouvé {company_count} entreprises. Affinez vos critères."
                yield f"event: content\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"

            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            print(f"Error in streaming chat: {e}")
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


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
