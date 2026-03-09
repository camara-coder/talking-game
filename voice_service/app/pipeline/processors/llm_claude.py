"""
LLM Processor using the Anthropic Claude API (primary provider).

Uses claude-haiku-4-5 by default — Anthropic's fastest model, optimised for
low-latency conversational tasks.  Streaming is always used so TTS can start
on the first sentence while the model is still generating the rest.

If the API key is missing, exhausted, or any API error occurs, the caller
(pipeline_runner) catches the exception and falls back to the local Ollama
processor.
"""
import re
import logging
from typing import Generator, List, Dict, Optional

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# Sentence-ending punctuation — same regex used by the Ollama streamer.
_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


class ClaudeLLMProcessor:
    """LLM processor using the Anthropic Messages API with streaming."""

    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set — cannot use Claude LLM. "
                "Set the environment variable or fall back to Ollama."
            )
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info(f"Claude LLM initialised: model={settings.ANTHROPIC_MODEL}")

    def generate_sentences_stream(
        self,
        prompt: str,
        context: List[Dict[str, str]] = None,
        system_prompt: str = None,
    ) -> Generator[str, None, None]:
        """
        Stream the Claude response and yield one complete sentence at a time.

        Raises:
            anthropic.APIError (and subclasses) on any API failure, so the
            caller can catch it and fall back to Ollama.
        """
        if system_prompt is None:
            system_prompt = settings.SYSTEM_PROMPT

        # Build messages array from conversation context
        messages: List[Dict] = []
        if context:
            for turn in context:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": prompt})

        buffer = ""
        remainder = ""

        try:
            with self._client.messages.stream(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
            ) as stream:
                for text_chunk in stream.text_stream:
                    buffer += text_chunk

                    # Yield every time a sentence boundary is detected
                    while True:
                        m = _SENTENCE_END.search(buffer)
                        if not m:
                            break
                        sentence = buffer[: m.start() + 1].strip()
                        buffer = buffer[m.end():]
                        if sentence:
                            logger.debug(f"Claude sentence: '{sentence}'")
                            yield sentence

            # Yield anything left after the stream closes
            remainder = buffer.strip()
            if remainder:
                yield remainder

        except anthropic.APIError as exc:
            # Re-raise so pipeline_runner can fall back to Ollama
            logger.warning(
                f"Claude API error ({type(exc).__name__}: {exc}), "
                "pipeline will fall back to Ollama"
            )
            # Yield whatever was buffered before the error so we're not silent
            if buffer.strip():
                yield buffer.strip()
            raise
