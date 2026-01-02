"""
Response Shaper Processor
Enforces kid-mode constraints on responses
"""
import logging

from app.config import settings
from app.utils.safety_filter import (
    contains_unsafe_content,
    get_safe_fallback,
    count_sentences,
    count_words,
    truncate_to_sentences,
    truncate_to_words
)

logger = logging.getLogger(__name__)


class ResponseShaperProcessor:
    """Shapes responses to be kid-friendly and concise"""

    def __init__(
        self,
        max_sentences: int = None,
        max_words: int = None
    ):
        """
        Initialize response shaper

        Args:
            max_sentences: Maximum number of sentences
            max_words: Maximum number of words
        """
        self.max_sentences = max_sentences or settings.MAX_RESPONSE_SENTENCES
        self.max_words = max_words or settings.MAX_RESPONSE_WORDS

        logger.info(
            f"Response shaper initialized: "
            f"max_sentences={self.max_sentences}, max_words={self.max_words}"
        )

    def shape(self, text: str) -> str:
        """
        Shape response to be kid-friendly

        Args:
            text: Original response text

        Returns:
            Shaped response text
        """
        logger.info(f"Shaping response: '{text}'")

        # Check for unsafe content first
        if contains_unsafe_content(text):
            logger.warning("Unsafe content detected, using fallback")
            return get_safe_fallback()

        # Count sentences and words
        num_sentences = count_sentences(text)
        num_words = count_words(text)

        logger.debug(
            f"Original: {num_sentences} sentences, {num_words} words"
        )

        # Truncate if needed
        shaped_text = text

        # First truncate to max sentences
        if num_sentences > self.max_sentences:
            shaped_text = truncate_to_sentences(shaped_text, self.max_sentences)
            logger.info(f"Truncated to {self.max_sentences} sentences")

        # Then truncate to max words (respecting sentence boundaries)
        num_words_after = count_words(shaped_text)
        if num_words_after > self.max_words:
            shaped_text = truncate_to_words(shaped_text, self.max_words)
            logger.info(f"Truncated to ~{self.max_words} words")

        # Final check for unsafe content (in case truncation revealed something)
        if contains_unsafe_content(shaped_text):
            logger.warning("Unsafe content in shaped response, using fallback")
            return get_safe_fallback()

        logger.info(f"Shaped response: '{shaped_text}'")

        return shaped_text.strip()
