"""
SHL Assessment Recommender - FastAPI Application
"""

import os
import json
import logging
from typing import List

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from src.models.api_models import (
    ChatRequest,
    ChatResponse,
    AssessmentReference,
)

from src.retrieval.bm25_search import search_engine

from src.guardrails.basic_guards import (
    is_injection_attempt,
    is_out_of_scope,
)

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

    catalog_path = os.getenv(
        "CATALOG_PATH",
        "data/assessments.json"
    )

    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)

        logger.info(
            f"Loaded {len(catalog)} assessments from {catalog_path}"
        )

        return catalog

    except FileNotFoundError:
        logger.error(f"Catalog not found at {catalog_path}")
        return []

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in catalog: {e}")
        return []


# Load catalog on startup
CATALOG = load_catalog()

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
    Chat endpoint - accepts conversation history,
    returns recommendations.
    """

    # Validate input
    if not request.messages:

        logger.error("No messages in request")

        raise HTTPException(
            status_code=400,
            detail="No messages provided"
        )

    try:

        logger.info(
            f"Chat request with {len(request.messages)} messages"
        )

        last_message = request.messages[-1].content

        logger.info(f"Last message: {last_message}")

        # -----------------------------
        # GUARDRAILS
        # -----------------------------

        if is_injection_attempt(last_message):

            logger.warning(
                "Injection attempt detected"
            )

            return ChatResponse(
                reply=(
                    "I detected a suspicious request. "
                    "I can only help with SHL assessments."
                ),
                recommendations=[],
                end_of_conversation=True,
            )

        if is_out_of_scope(last_message):

            logger.warning(
                "Out-of-scope request detected"
            )

            return ChatResponse(
                reply=(
                    "That's outside my scope. "
                    "I focus on SHL assessment recommendations."
                ),
                recommendations=[],
                end_of_conversation=True,
            )

        # -----------------------------
        # FIRST TURN
        # -----------------------------

        if len(request.messages) == 1:

            logger.info(
                "First turn - asking for clarification"
            )

            return ChatResponse(
                reply=(
                    "Hello! I'm the SHL Assessment Recommender.\n\n"
                    "To help you find the best assessments, "
                    "please tell me:\n"
                    "1. What role are you hiring for?\n"
                    "2. What seniority level "
                    "(entry, mid, senior)?"
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        # -----------------------------
        # SEARCH
        # -----------------------------

        logger.info(
            f"Searching assessments for query: {last_message}"
        )

        results = search_engine.search(
            last_message,
            top_k=5
        )

        logger.info(
            f"Found {len(results)} matching assessments"
        )

        recommendations = [
            AssessmentReference(
                name=assessment['name'],
                url=assessment['url'],
                test_type=assessment['test_type'],
            )
            for assessment in results
        ]

        # -----------------------------
        # NO RESULTS
        # -----------------------------

        if not recommendations:

            logger.warning(
                "No matching assessments found"
            )

            return ChatResponse(
                reply=(
                    "I couldn't find any matching assessments "
                    "for your query. Please try describing:\n"
                    "- Role\n"
                    "- Skills\n"
                    "- Seniority level"
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        # -----------------------------
        # SUCCESS RESPONSE
        # -----------------------------

        return ChatResponse(
            reply=(
                f"I found {len(recommendations)} "
                "relevant assessments for your needs."
            ),
            recommendations=recommendations,
            end_of_conversation=True,
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.error(
            f"Error in chat endpoint: {e}",
            exc_info=True
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


if __name__ == "__main__":

    import uvicorn

    port = int(os.getenv("PORT", 8000))

    logger.info(
        f"Starting SHL Recommender on port {port}"
    )

    logger.info(
        f"Loaded {len(CATALOG)} assessments"
    )

    logger.info(
        f"API docs: http://localhost:{port}/docs"
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
    )