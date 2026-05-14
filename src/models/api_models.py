"""
API request/response models.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class Message(BaseModel):
    """Single message in conversation"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    """Chat endpoint request"""
    messages: List[Message] = Field(..., description="Conversation history")

class AssessmentReference(BaseModel):
    """Assessment recommendation"""
    name: str = Field(..., description="Assessment name")
    url: str = Field(..., description="Assessment URL")
    test_type: str = Field(..., description="Assessment type")

class ChatResponse(BaseModel):
    """Chat endpoint response"""
    reply: str = Field(..., description="Conversational response")
    recommendations: List[AssessmentReference] = Field(
        default_factory=list,
        description="Recommended assessments (max 10)"
    )
    end_of_conversation: bool = Field(
        default=False,
        description="Whether conversation should end"
    )