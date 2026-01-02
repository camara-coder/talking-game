"""
Safety filter utilities for kid-mode content filtering
"""
import logging
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)


def contains_unsafe_content(text: str, keywords: List[str] = None) -> bool:
    """
    Check if text contains unsafe keywords

    Args:
        text: Text to check
        keywords: List of unsafe keywords (default from settings)

    Returns:
        True if unsafe content detected
    """
    if keywords is None:
        keywords = settings.UNSAFE_KEYWORDS

    text_lower = text.lower()

    for keyword in keywords:
        if keyword.lower() in text_lower:
            logger.warning(f"Unsafe keyword detected: '{keyword}'")
            return True

    return False


def get_safe_fallback() -> str:
    """
    Get safe fallback response

    Returns:
        Safe fallback message
    """
    return settings.SAFE_FALLBACK_RESPONSE


def count_sentences(text: str) -> int:
    """
    Count sentences in text

    Args:
        text: Text to analyze

    Returns:
        Number of sentences
    """
    # Simple sentence counting (periods, exclamation marks, question marks)
    sentence_enders = ['.', '!', '?']

    count = 0
    for char in text:
        if char in sentence_enders:
            count += 1

    # If no sentence enders, count as 1 sentence if non-empty
    if count == 0 and text.strip():
        count = 1

    return count


def count_words(text: str) -> int:
    """
    Count words in text

    Args:
        text: Text to analyze

    Returns:
        Number of words
    """
    words = text.split()
    return len(words)


def truncate_to_sentences(text: str, max_sentences: int = 2) -> str:
    """
    Truncate text to maximum number of sentences

    Args:
        text: Text to truncate
        max_sentences: Maximum number of sentences

    Returns:
        Truncated text
    """
    sentence_enders = ['.', '!', '?']

    sentence_count = 0
    truncate_pos = len(text)

    for i, char in enumerate(text):
        if char in sentence_enders:
            sentence_count += 1
            if sentence_count >= max_sentences:
                truncate_pos = i + 1
                break

    return text[:truncate_pos].strip()


def truncate_to_words(text: str, max_words: int = 35) -> str:
    """
    Truncate text to maximum number of words
    Tries to end at sentence boundary if possible

    Args:
        text: Text to truncate
        max_words: Maximum number of words

    Returns:
        Truncated text
    """
    words = text.split()

    if len(words) <= max_words:
        return text

    # Truncate to max words
    truncated_words = words[:max_words]
    truncated_text = ' '.join(truncated_words)

    # Try to find last sentence ender
    sentence_enders = ['.', '!', '?']
    last_ender = -1

    for i in range(len(truncated_text) - 1, -1, -1):
        if truncated_text[i] in sentence_enders:
            last_ender = i
            break

    # If found sentence ender in last 80% of text, use that
    if last_ender > len(truncated_text) * 0.8:
        return truncated_text[:last_ender + 1].strip()

    # Otherwise, just return truncated text with ellipsis if original was longer
    if len(words) > max_words:
        return truncated_text.strip() + "..."

    return truncated_text.strip()
