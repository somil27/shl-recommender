"""
API request/response models for SHL Assessment Recommender.
Pydantic models for validation and serialization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Single message in conversation"""
    role: str = Field(
        ..., 
        description="'user' or 'assistant'",
        examples=["user", "assistant"]
    )
    content: str = Field(
        ..., 
        description="Message content",
        examples=["I need a Java assessment", "What seniority level are you hiring for?"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "I need a Java assessment"
            }
        }


class ChatRequest(BaseModel):
    """Chat endpoint request model"""
    messages: List[Message] = Field(
        ..., 
        description="Conversation history - full history passed on each request",
        min_items=1,
        max_items=8
    )

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "I need a Java assessment"
                    }
                ]
            }
        }


class AssessmentReference(BaseModel):
    """Assessment recommendation in response"""
    name: str = Field(
        ..., 
        description="Assessment name from catalog",
        examples=["Java 8", "Python Developer Assessment"]
    )
    url: str = Field(
        ..., 
        description="Assessment URL from catalog",
        examples=["https://www.shl.com/..."]
    )
    test_type: str = Field(
        ..., 
        description="Assessment type (skills, role, personality, etc)",
        examples=["skills", "role", "personality"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Java 8",
                "url": "https://www.shl.com/assessments/java-8",
                "test_type": "skills"
            }
        }


class ChatResponse(BaseModel):
    """Chat endpoint response model"""
    reply: str = Field(
        ..., 
        description="Conversational response to user",
        examples=[
            "Hello! I'm the SHL Assessment Recommender. What role are you looking for?",
            "I found 2 relevant assessments for your needs."
        ]
    )
    recommendations: List[AssessmentReference] = Field(
        default_factory=list,
        description="Recommended assessments (empty when clarifying, 1-10 when recommending)",
        max_items=10
    )
    end_of_conversation: bool = Field(
        default=False,
        description="Whether conversation should end (True when recommendations provided)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "reply": "I found 2 relevant assessments for your needs.",
                "recommendations": [
                    {
                        "name": "Java 8",
                        "url": "https://www.shl.com/assessments/java-8",
                        "test_type": "skills"
                    },
                    {
                        "name": "Backend Developer Assessment",
                        "url": "https://www.shl.com/assessments/backend-dev",
                        "test_type": "role"
                    }
                ],
                "end_of_conversation": True
            }
        }

class EvaluateRequest(BaseModel):
    """Request model for evaluate endpoint"""
    query: str = Field(
        ...,
        description="Query for evaluation",
        examples=["Java developer senior"]
    )
    recommendations: List[str] = Field(
        ...,
        description="List of assessment names to evaluate",
        examples=[["Java 8", "Backend Developer Assessment"]]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Java developer senior",
                "recommendations": ["Java 8", "Backend Developer Assessment"]
            }
        }        