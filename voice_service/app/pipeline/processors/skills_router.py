"""
Skills Router Processor
Routes transcripts to either deterministic skills (math) or LLM
"""
import logging
from typing import Optional, Tuple

from app.utils.text_math import (
    is_math_query,
    parse_math_expression,
    compute_math,
    format_math_response
)

logger = logging.getLogger(__name__)


class SkillsRouterProcessor:
    """Routes queries to appropriate handler (math or LLM)"""

    def __init__(self):
        """Initialize skills router"""
        logger.info("Skills router initialized")

    def route(self, transcript: str) -> Tuple[str, Optional[str]]:
        """
        Route transcript to appropriate handler

        Args:
            transcript: Transcribed text

        Returns:
            Tuple of (route, response)
            - route: "math" or "llm"
            - response: Computed response if math, None if LLM should handle
        """
        logger.info(f"Routing transcript: '{transcript}'")

        # Check if math query
        if is_math_query(transcript):
            logger.info("Math query detected")

            # Try to parse and compute
            parsed = parse_math_expression(transcript)

            if parsed:
                operator, a, b = parsed
                logger.info(f"Math expression: {a} {operator} {b}")

                # Compute result
                result, error = compute_math(operator, a, b)

                if error:
                    # Error in computation (e.g., divide by zero)
                    logger.warning(f"Math error: {error}")
                    return ("math", error)

                # Format response
                response = format_math_response(operator, a, b, result)
                logger.info(f"Math response: '{response}'")
                return ("math", response)

            else:
                # Looks like math but couldn't parse
                logger.warning("Math query detected but could not parse expression")
                # Fall through to LLM

        # Route to LLM
        logger.info("Routing to LLM")
        return ("llm", None)
