"""
Assessment Recommender - FastAPI Application with LLM Integration
"""

import os
import json
import logging
from typing import List

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from models.api_models import (
    ChatRequest,
    ChatResponse,
    AssessmentReference,
    EvaluateRequest,
)
from llm_service import AssessmentRecommenderLLM

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

    # Calculate app root directory
    app_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    catalog_path = os.path.join(
        app_root,
        "data",
        "assessments.json"
    )

    logger.info(f"App root directory: {app_root}")
    logger.info(f"Catalog path: {catalog_path}")
    logger.info(f"Catalog exists: {os.path.exists(catalog_path)}")

    if not os.path.exists(catalog_path):

        logger.error(f"Catalog not found at {catalog_path}")

        try:
            logger.info(f"Contents of {app_root}:")

            for item in os.listdir(app_root):
                logger.info(f"  - {item}")

        except Exception as e:
            logger.error(f"Cannot list directory: {e}")

        return []

    try:

        with open(
            catalog_path,
            'r',
            encoding='utf-8'
        ) as f:

            catalog = json.load(f)

        logger.info(
            f"Loaded {len(catalog)} assessments "
            f"from {catalog_path}"
        )

        return catalog

    except json.JSONDecodeError as e:

        logger.error(f"Invalid JSON in catalog: {e}")

        return []

    except Exception as e:

        logger.error(f"Error loading catalog: {e}")

        return []


# Load catalog on startup
CATALOG = load_catalog()

#Initialize LLM service
try:
    llm_service = AssessmentRecommenderLLM()
    logger.info("LLM Service initialized successfully")
except Exception as e:
    logger.warning(f"LLM Service initialization failed: {e}")
    logger.warning("Will use fallback keyword-based search")
    llm_service = None

# Create FastAPI app
app = FastAPI(
    title="Assessment Recommender",
    description="Multi-turn conversational agent with LLM for SHL assessment recommendations",
    version="2.0.0",
)


# -----------------------------
# ROOT ROUTE
# -----------------------------
@app.get("/")
async def root():

    return {
        "message": "Recommender API is running 🚀",
        "version": "2.0.0",
        "llm_enabled": llm_service is not None,
        "docs": "/docs",
        "health": "/health",
        "chat_endpoint": "/chat",
    }


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "service": "shl-recommender",
        "version": "2.0.0",
        "catalog_size": len(CATALOG),
        "llm_enabled": llm_service is not None,
    }


#Assessment Comparison Endpoint
@app.get("/chat/compare-by-name")
async def compare_assessments_by_name(
    assessment1: str,
    assessment2: str,
    context: str = ""
):
    """
    Compare two assessments by name (query parameters)
    
    Usage: GET /chat/compare-by-name?assessment1=Java%208&assessment2=Backend%20Developer%20Assessment
    """
    
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="LLM service not available"
        )
    
    try:
        logger.info(f"Comparing by name: {assessment1} vs {assessment2}")
        
        # Find assessments - flexible matching
        a1 = None
        a2 = None
        
        assessment1_lower = assessment1.lower()
        assessment2_lower = assessment2.lower()
        
        for assessment in CATALOG:
            catalog_name_lower = assessment['name'].lower()
            
            if assessment1_lower in catalog_name_lower or catalog_name_lower in assessment1_lower:
                a1 = assessment
            
            if assessment2_lower in catalog_name_lower or catalog_name_lower in assessment2_lower:
                a2 = assessment
        
        if not a1 or not a2:
            available = [a['name'] for a in CATALOG]
            raise HTTPException(
                status_code=404,
                detail=f"One or both assessments not found. Available: {', '.join(available)}"
            )
        
        logger.info(f"Found assessments: {a1['name']} and {a2['name']}")
        
        # Compare using LLM
        comparison = llm_service.compare_assessments(a1, a2, context)
        
        return {
            "assessment1": a1['name'],
            "assessment2": a2['name'],
            "comparison": comparison
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error comparing assessments: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

#UPDATED: CHAT ENDPOINT WITH LLM
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint with LLM-powered recommendations
    - Uses Groq API for intelligent understanding
    - Supports multi-turn conversations
    - Clarifies vague queries
    - Refines on constraint changes
    - Compares assessments with evidence
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
            f"Chat request with {len(request.messages)} messages, "
            f"LLM enabled: {llm_service is not None}"
        )

        last_message = request.messages[-1].content

        logger.info(f"Last message: {last_message}")

        #TURN 1: Clarification with LLM
        if len(request.messages) == 1:

            logger.info("Turn 1 - Generating clarifying questions with LLM")
            
            try:
                if llm_service:
                    # Use LLM to generate contextual clarifying question
                    clarifying_q = llm_service.generate_clarifying_question(
                        last_message, 
                        CATALOG
                    )
                    logger.info(f"LLM clarifying question: {clarifying_q}")
                else:
                    raise Exception("LLM service not available")
                    
            except Exception as e:
                logger.warning(
                    f"LLM clarifying question failed, using default: {e}"
                )
                clarifying_q = (
                    "What seniority level are you hiring for "
                    "(entry, mid, senior)?"
                )

            return ChatResponse(
                reply=(
                    "Hello! I'm the Assessment Recommender.\n\n"
                    f"I understand you're looking for: {last_message}\n\n"
                    f"{clarifying_q}\n\n"
                    "This will help me provide better recommendations."
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        #TURN 2+: LLM-Powered Recommendations
        logger.info("Turn 2+ - Getting LLM recommendations")
        
        recommendations = []
        llm_reasoning = ""
        
        try:
            if llm_service:
                # Call LLM with full conversation history
                logger.info("Calling Groq LLM with conversation history")
                
                llm_result = llm_service.get_llm_recommendation(
                    user_query=last_message,
                    catalog=CATALOG,
                    conversation_history=request.messages[:-1]
                )
                
                logger.info(f"LLM Result: {llm_result}")
                
                # Extract recommended assessment names from LLM
                recommended_names = llm_result.get("recommendations", [])
                llm_reasoning = llm_result.get("reasoning", "")
                llm_confidence = llm_result.get("confidence", 0)
                
                logger.info(
                    f"LLM recommended {len(recommended_names)} assessments "
                    f"with {llm_confidence}% confidence"
                )
                
                # Find matching assessments from catalog
                for rec_name in recommended_names:
                    for assessment in CATALOG:
                        # Match by substring to handle variations
                        if (rec_name.lower() in assessment['name'].lower() or 
                            assessment['name'].lower() in rec_name.lower()):
                            recommendations.append(
                                AssessmentReference(
                                    name=assessment['name'],
                                    url=assessment['url'],
                                    test_type=assessment['test_type'],
                                )
                            )
                            logger.info(
                                f"Matched LLM recommendation: {assessment['name']}"
                            )
                            break
            else:
                raise Exception("LLM service not available")
        
        except Exception as e:
            logger.warning(
                f"LLM recommendation failed, using fallback keyword search: {e}"
            )
            llm_reasoning = ""
            recommendations = []

        #FALLBACK: Keyword-Based Search (if LLM fails or returns no results)
        if not recommendations:
            logger.info("Using fallback keyword-based search")
            
            search_terms = last_message.lower().split()

            results = []

            # Keyword matching
            for assessment in CATALOG:

                assessment_name = assessment['name'].lower()

                assessment_type = assessment.get(
                    'test_type',
                    ''
                ).lower()

                assessment_skills = ' '.join(
                    assessment.get('skills', [])
                ).lower()

                # Check if any search term matches
                for term in search_terms:

                    if (
                        term in assessment_name or
                        term in assessment_type or
                        term in assessment_skills
                    ):

                        results.append(assessment)

                        break

            #Limit top results to 1-10 (requirements say)
            results = results[:10]

            logger.info(
                f"Keyword search found {len(results)} assessments"
            )

            recommendations = [
                AssessmentReference(
                    name=assessment['name'],
                    url=assessment['url'],
                    test_type=assessment['test_type'],
                )
                for assessment in results
            ]

        # Ensure we have 1-10 recommendations (per spec)
        recommendations = recommendations[:10]

        logger.info(
            f"Final recommendations: {len(recommendations)} assessments"
        )

        # No results
        if not recommendations:

            logger.warning(
                "No matching assessments found after LLM and keyword search"
            )

            return ChatResponse(
                reply=(
                    "I couldn't find any matching assessments "
                    "for your query. Please try describing:\n"
                    "- Role/Position\n"
                    "- Required Skills\n"
                    "- Seniority level (entry, mid, senior)"
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        # Success response
        reply_text = (
            f"I found {len(recommendations)} relevant assessment"
        )
        
        if len(recommendations) > 1:
            reply_text += "s"
        
        reply_text += " for your needs."
        
        if llm_reasoning:
            reply_text += f"\n\nReasoning: {llm_reasoning}"
        
        return ChatResponse(
            reply=reply_text,
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


# NEW: Multi-Assessment Comparison
@app.post("/chat/clarify")
async def clarify_intent(query: str):
    """
    Get clarifying questions for a vague query using LLM
    """
    
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="LLM service not available"
        )
    
    try:
        logger.info(f"Clarifying query: {query}")
        
        clarifying_q = llm_service.generate_clarifying_question(
            query,
            CATALOG
        )
        
        return {
            "query": query,
            "clarifying_question": clarifying_q
        }
    
    except Exception as e:
        logger.error(f"Error generating clarifying question: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# NEW: Evaluate Recommendations
@app.post("/evaluate")
async def evaluate_recommendations(request: EvaluateRequest):
    """
    Evaluate how relevant recommendations are for a query
    
    Request body:
    {
      "query": "Java developer senior",
      "recommendations": ["Java 8", "Backend Developer Assessment"]
    }
    
    Response:
    {
      "query": "Java developer senior",
      "evaluations": [
        {"assessment": "Java 8", "relevance_score": 95},
        {"assessment": "Backend Developer Assessment", "relevance_score": 88}
      ],
      "average_relevance": 91.5
    }
    """
    
    if not llm_service:
        raise HTTPException(
            status_code=503,
            detail="LLM service not available"
        )
    
    try:
        logger.info(f"Evaluating {len(request.recommendations)} recommendations")
        logger.info(f"Query: {request.query}")
        
        if not request.query:
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )
        
        if not request.recommendations:
            raise HTTPException(
                status_code=400,
                detail="Recommendations list cannot be empty"
            )
        
        scores = []
        
        for rec_name in request.recommendations:
            logger.info(f"Evaluating: {rec_name}")
            
            score = llm_service.calculate_relevance_score(
                request.query,
                rec_name
            )
            scores.append({
                "assessment": rec_name,
                "relevance_score": score
            })
            logger.info(f"{rec_name}: {score}%")
        
        average_relevance = sum(s["relevance_score"] for s in scores) / len(scores) if scores else 0
        
        logger.info(f"Average relevance: {average_relevance}")
        
        return {
            "query": request.query,
            "evaluations": scores,
            "average_relevance": round(average_relevance, 1)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error evaluating recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# NEW: Health Check with Detailed Status
@app.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check with LLM status"""
    
    return {
        "status": "healthy",
        "service": "shl-recommender",
        "version": "2.0.0",
        "catalog": {
            "loaded": len(CATALOG) > 0,
            "count": len(CATALOG)
        },
        "llm": {
            "enabled": llm_service is not None,
            "provider": "Groq",
            "model": "llama3-70b-8192" if llm_service else "N/A"
        },
        "features": {
            "clarify": True,
            "recommend": True,
            "refine": True,
            "compare": True,
            "fallback": True
        }
    }


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    import uvicorn

    port = int(os.getenv("PORT", 8080))

    logger.info(
        f"Starting SHL Recommender on port {port}"
    )

    logger.info(
        f"Loaded {len(CATALOG)} assessments"
    )

    logger.info(
        f"LLM Service: {'Enabled' if llm_service else 'Disabled'}"
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
