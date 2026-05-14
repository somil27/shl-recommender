"""
SHL Assessment Recommender - FastAPI Application
"""

import os
import json
import logging
from typing import List
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from src.models.api_models import ChatRequest, ChatResponse, AssessmentReference

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load catalog
def load_catalog() -> List[dict]:
    """Load assessment catalog from JSON"""
    catalog_path = os.getenv("CATALOG_PATH", "data/assessments.json")
    try:
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        logger.info(f"Loaded {len(catalog)} assessments from {catalog_path}")
        return catalog
    except FileNotFoundError:
        logger.error(f"Catalog not found at {catalog_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in catalog: {e}")
        return []

# Load catalog on startup
CATALOG = load_catalog()
CATALOG_NAMES = {a['name'] for a in CATALOG}

# Create FastAPI app
app = FastAPI(
    title="SHL Assessment Recommender",
    description="Multi-turn conversational agent for SHL assessment recommendations",
    version="1.0.0",
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "shl-recommender",
        "version": "1.0.0",
        "catalog_size": len(CATALOG),
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - accepts conversation history, returns recommendations.
    """
    # Validate input BEFORE try-except
    if not request.messages:
        logger.error("No messages in request")
        raise HTTPException(status_code=400, detail="No messages provided")
    
    try:
        logger.info(f"Chat request with {len(request.messages)} messages")
        
        last_message = request.messages[-1].content
        logger.info(f"Last message: {last_message}")
        
        # First turn - ask for clarification
        if len(request.messages) == 1:
            logger.info("First turn - asking for clarification")
            return ChatResponse(
                reply="Hello! I'm the SHL Assessment Recommender. To help you find the best assessments, could you tell me:\n1. What role are you hiring for?\n2. What seniority level (entry, mid, senior)?",
                recommendations=[],
                end_of_conversation=False,
            )
        
        # If user mentions "java", recommend Java 8
        if "java" in last_message.lower():
            logger.info("User mentioned Java - searching for Java assessments")
            java_assessment = next(
                (a for a in CATALOG if "java" in a['name'].lower()),
                None
            )
            if java_assessment:
                logger.info(f"Found Java assessment: {java_assessment['name']}")
                return ChatResponse(
                    reply="Great! Java 8 (New) is an excellent technical assessment for evaluating Java programming skills.",
                    recommendations=[
                        AssessmentReference(
                            name=java_assessment['name'],
                            url=java_assessment['url'],
                            test_type=java_assessment['test_type'],
                        )
                    ],
                    end_of_conversation=True,
                )
        
        # Default: return top 5 assessments
        logger.info(f"Returning default response with {min(5, len(CATALOG))} assessments")
        return ChatResponse(
            reply="Based on your requirements, here are our recommended assessments:",
            recommendations=[
                AssessmentReference(
                    name=a['name'],
                    url=a['url'],
                    test_type=a['test_type'],
                )
                for a in CATALOG[:5]
            ],
            end_of_conversation=True,
        )
    
    except HTTPException:
        # Let HTTP exceptions pass through unchanged (don't convert to 500)
        raise
    except Exception as e:
        # Only catch unexpected errors and convert to 500
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting SHL Recommender on port {port}")
    logger.info(f"Loaded {len(CATALOG)} assessments")
    logger.info(f"API docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
    )