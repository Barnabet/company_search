"""
Pydantic schemas for API requests and responses.

These schemas define the structure of data exchanged between
the frontend and backend API.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

# ============================================================================
# Message Schemas
# ============================================================================

class MessageBase(BaseModel):
    """Base schema for messages"""
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    pass


class MessageResponse(BaseModel):
    """Schema for message in API responses"""
    id: UUID
    role: str
    content: str
    created_at: datetime
    sequence_number: int
    analysis_result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationCreate(BaseModel):
    """Schema for creating a new conversation"""
    initial_message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Initial user query to start the conversation"
    )


class ConversationBase(BaseModel):
    """Base schema for conversations"""
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class ConversationResponse(ConversationBase):
    """Schema for conversation in API responses"""
    messages: List[MessageResponse] = []
    extraction_result: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    # Extended fields for API integration
    company_count: Optional[int] = Field(None, description="Number of matching companies from external API")

    model_config = ConfigDict(from_attributes=True)

    @property
    def company_count_from_extraction(self) -> Optional[int]:
        """Extract company_count from extraction_result if present."""
        if self.extraction_result:
            return self.extraction_result.get("company_count")
        return None


class ConversationListItem(ConversationBase):
    """Schema for conversation in list responses (without messages)"""
    message_count: int = 0
    last_message_preview: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Agent Response Schemas
# ============================================================================

class CompletenessAnalysis(BaseModel):
    """Schema for completeness analysis result from agent"""
    is_complete: bool = Field(..., description="Whether the query is complete enough for extraction")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    suggested_question: Optional[str] = Field(None, description="Next question to ask user")
    reasoning: str = Field(..., description="Explanation of the analysis")


class AgentMessageResponse(BaseModel):
    """Schema for agent's response to user message"""
    conversation_id: UUID
    status: str
    message: str = Field(..., description="Agent's message to user")
    is_complete: bool = Field(..., description="Whether search criteria are ready")
    extraction_result: Optional[Dict[str, Any]] = Field(None, description="Extraction result if complete")
    requires_user_input: bool = Field(..., description="Whether agent expects user response")


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
