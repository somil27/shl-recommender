"""
LLM Service for Conversational Assessment Recommendations
Using Groq API with Mixtral model
"""

from groq import Groq
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class AssessmentRecommenderLLM:
    """LLM-powered assessment recommendation engine"""

    def __init__(self):
        try:
            self.client = Groq()
            self.model = "llama-3.3-70b-versatile"
            self.temperature = 0.7
            self.max_tokens = 500

            logger.info("Groq client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise

    def build_catalog_context(self, catalog: List[Dict]) -> str:
        """Build context string from catalog"""

        context = "Available Assessments:\n\n"

        if not catalog:
            return context + "No assessments available."

        for i, assessment in enumerate(catalog, 1):

            name = assessment.get('name', 'Unknown')
            test_type = assessment.get('test_type', 'Unknown')
            skills = ', '.join(assessment.get('skills', []))
            url = assessment.get('url', '')

            context += f"{i}. {name}\n"
            context += f"   Type: {test_type}\n"
            context += f"   Skills: {skills}\n"
            context += f"   URL: {url}\n\n"

        return context

    def _call_groq(self, prompt: str, max_tokens: int = 500) -> str:
        """Reusable Groq API call"""

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.temperature,
            max_tokens=max_tokens,
        )

        return completion.choices[0].message.content.strip()

    def get_llm_recommendation(
        self,
        user_query: str,
        catalog: List[Dict],
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Get LLM-powered recommendation with catalog grounding
        """

        try:

            if not user_query:

                logger.warning("Empty user query received")

                return {
                    "recommendations": [],
                    "reasoning": "Please provide a query",
                    "confidence": 0,
                    "clarifying_question": "What role are you looking for?",
                    "response_text": "I need more information to help you."
                }

            # Build context
            catalog_context = self.build_catalog_context(catalog)

            # Build conversation history
            conversation_context = ""

            if conversation_history:

                conversation_context = "Conversation History:\n"

                for i, msg in enumerate(conversation_history):

                    role = (
                        msg.role.upper()
                        if hasattr(msg, 'role')
                        else 'UNKNOWN'
                    )

                    content = (
                        msg.content
                        if hasattr(msg, 'content')
                        else ''
                    )

                    conversation_context += (
                        f"{i+1}. {role}: {content}\n"
                    )

            prompt = f"""
You are an expert SHL Assessment Recommender.

CRITICAL RULES:
1. ONLY recommend assessments from provided catalog
2. NEVER hallucinate names
3. Use exact assessment names
4. Give confidence score
5. Use conversational style

{conversation_context}

ASSESSMENT CATALOG:
{catalog_context}

CURRENT USER QUERY:
{user_query}

TASK:
1. Recommend most relevant assessments
2. Explain reasoning
3. Give confidence score
4. Ask clarification if needed

RESPOND IN VALID JSON ONLY:

{{
    "recommendations": ["Assessment Name"],
    "reasoning": "Why recommended",
    "confidence": 90,
    "clarifying_question": null,
    "response_text": "Friendly conversational response"
}}
"""

            logger.info(
                f"Calling Groq API for query: "
                f"{user_query[:50]}..."
            )

            response_text = self._call_groq(
                prompt,
                self.max_tokens
            )

            logger.info(
                f"Groq response received: "
                f"{len(response_text)} chars"
            )

            try:

                response_json = self._extract_json(
                    response_text
                )

                response_json.setdefault(
                    'recommendations',
                    []
                )

                response_json.setdefault(
                    'reasoning',
                    ''
                )

                response_json.setdefault(
                    'confidence',
                    50
                )

                response_json.setdefault(
                    'clarifying_question',
                    None
                )

                response_json.setdefault(
                    'response_text',
                    response_text
                )

                logger.info(
                    f"Successfully parsed LLM response"
                )

                return response_json

            except json.JSONDecodeError as e:

                logger.warning(
                    f"JSON parse failed: {e}"
                )

                return self._get_fallback_response(
                    response_text
                )

        except Exception as e:

            logger.error(
                f"Error in LLM recommendation: {e}",
                exc_info=True
            )

            raise

    def _get_fallback_response(
        self,
        response_text: str
    ) -> Dict:
        """Fallback response"""

        return {
            "recommendations": [],
            "reasoning": response_text[:200],
            "confidence": 30,
            "clarifying_question":
                "Can you provide more details?",
            "response_text": response_text
        }

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from response"""

        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if (
            start_idx == -1 or
            end_idx == -1
        ):

            raise json.JSONDecodeError(
                "No JSON found",
                text,
                0
            )

        json_str = text[start_idx:end_idx + 1]

        return json.loads(json_str)

    def generate_clarifying_question(
        self,
        user_query: str,
        catalog: List[Dict]
    ) -> str:
        """Generate clarifying question"""

        try:

            assessment_types = set(
                a.get('test_type', '')
                for a in catalog
            )

            types_str = ', '.join(
                filter(None, assessment_types)
            )

            prompt = f"""
Candidate query: "{user_query}"

Available assessment types:
{types_str}

Generate ONE short clarifying question.

ONLY return question text.
"""

            response = self._call_groq(
                prompt,
                50
            )

            return (
                response.strip()
                if response
                else "What seniority level are you hiring for?"
            )

        except Exception as e:

            logger.error(
                f"Error generating question: {e}"
            )

            return (
                "What seniority level are you hiring for?"
            )

    def calculate_relevance_score(
        self,
        query: str,
        assessment_name: str
    ) -> float:
        """Calculate relevance score"""

        try:

            prompt = f"""
Rate relevance from 0-100.

Query:
{query}

Assessment:
{assessment_name}

ONLY return a number.
"""

            response = self._call_groq(
                prompt,
                10
            )

            digits = ''.join(
                filter(str.isdigit, response)
            )

            if digits:

                score = int(digits)

                return min(
                    100,
                    max(0, score)
                )

            return 50.0

        except Exception as e:

            logger.error(
                f"Error calculating relevance: {e}"
            )

            return 50.0

    def compare_assessments(
        self,
        assessment1: Dict,
        assessment2: Dict,
        context: str = ""
    ) -> Dict:
        """Compare two assessments"""

        try:

            prompt = f"""
Compare these SHL assessments.

Assessment 1:
{assessment1}

Assessment 2:
{assessment2}

Context:
{context}

RESPOND IN VALID JSON:

{{
    "similarities": [],
    "differences": [],
    "recommendation": "",
    "use_case_1": "",
    "use_case_2": ""
}}
"""

            response = self._call_groq(
                prompt,
                300
            )

            return self._extract_json(response)

        except Exception as e:

            logger.error(
                f"Comparison error: {e}"
            )

            return self._get_empty_comparison()

    def _get_empty_comparison(self) -> Dict:
        """Empty comparison"""

        return {
            "similarities": [],
            "differences": [],
            "recommendation":
                "Need more information to compare",
            "use_case_1": "TBD",
            "use_case_2": "TBD"
        }