"""
LLM Processor using Ollama
Generates responses to non-math queries
"""
import requests
import logging
from typing import List, Dict, Optional
import time

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaLLMProcessor:
    """LLM processor using Ollama local inference"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = None
    ):
        """
        Initialize Ollama LLM processor

        Args:
            base_url: Ollama API base URL
            model: Model name
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT

        logger.info(
            f"LLM initialized: model={self.model}, "
            f"url={self.base_url}"
        )

        # Verify Ollama is accessible
        self._check_connection()

    def _check_connection(self):
        """Check if Ollama is accessible"""
        try:
            response = requests.get(self.base_url, timeout=5)
            logger.info("Ollama connection verified")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")

    def generate(
        self,
        prompt: str,
        context: List[Dict[str, str]] = None,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Generate response using Ollama

        Args:
            prompt: User prompt/question
            context: Conversation context (list of {user, assistant} dicts)
            system_prompt: System prompt (default from settings)

        Returns:
            Generated response or None if generation failed
        """
        if system_prompt is None:
            system_prompt = settings.SYSTEM_PROMPT

        logger.info(f"Generating LLM response for: '{prompt}'")

        start_time = time.time()

        try:
            # Build messages for chat endpoint
            messages = []

            # Add system message
            messages.append({
                "role": "system",
                "content": system_prompt
            })

            # Add context messages
            if context:
                for turn in context:
                    messages.append({"role": "user", "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["assistant"]})

            # Add current prompt with instruction
            user_message = f"{prompt}\n\nReply briefly. One or two sentences."
            messages.append({"role": "user", "content": user_message})

            # Call Ollama API
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": settings.LLM_TEMPERATURE,
                    "top_p": settings.LLM_TOP_P,
                    "num_predict": settings.LLM_MAX_TOKENS
                }
            }

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            # Extract response
            if "message" in result and "content" in result["message"]:
                generated_text = result["message"]["content"].strip()

                elapsed_time = time.time() - start_time

                logger.info(
                    f"LLM response generated: '{generated_text}' "
                    f"({elapsed_time:.2f}s)"
                )

                return generated_text
            else:
                logger.error(f"Unexpected Ollama response format: {result}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            return "I'm thinking too slowly. Can you ask again?"

        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama")
            return "I'm having trouble thinking right now. Try again?"

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}", exc_info=True)
            return None
