"""
Pre-baked cat response pool for Whiskers.

For ~60% of user utterances the LLM is overkill — the user said something
short, made a sound, or is just chatting.  Pulling a response from this pool
is instant (no network, no inference), so the cat replies in < 100 ms instead
of 2-5 s.

When to use the pool vs. the LLM:
  • User utterance is a question (contains "?")  → always LLM
  • User utterance is long (> 6 words)           → always LLM
  • User utterance is short / emotional           → pool (configurable probability)

Pool responses are bucketed by CatMood so the cat's personality stays
consistent with its current emotional state.
"""
import random
from typing import Optional

from app.personality.cat_mood import CatMood

# ─────────────────────────────────────────────────────────────────────────────
# Response buckets — write these the way Whiskers would actually say them:
# short, punchy, full of cat energy, safe for children.
# ─────────────────────────────────────────────────────────────────────────────

_POOL: dict[CatMood, list[str]] = {
    CatMood.HAPPY: [
        "Purrr! You're talking to me!",
        "Mrow! I love when you do that!",
        "Oh oh oh! This is the best thing ever!",
        "Purr purr purr. Life is perfect right now.",
        "Yay! I'm so happy! Can we play?",
        "Meow meow meow! You're my favourite human!",
        "I'm wiggling my tail because I'm so happy!",
        "Prrr-mrow! You make me smile. Do cats smile? I think I'm smiling.",
        "Mew! That is SO interesting. Tell me more!",
        "Heehee, I just knocked something over. On purpose.",
    ],
    CatMood.BORED: [
        "Mrrow... I've been sitting here forever.",
        "Can we DO something? Anything?",
        "Yaaawn. I'm so bored I might just knock this over.",
        "Meeeow. Nothing exciting is happening.",
        "I stared at the wall for ten minutes. Still nothing.",
        "Sigh. I need entertainment. That's you. Entertain me.",
        "Mrp. I've counted all my whiskers twice already.",
        "You know what's fun? Everything we're NOT doing right now.",
        "I could nap. I have been napping. There must be more to life.",
        "Mrow mrow mrow. That's me being dramatic.",
    ],
    CatMood.CURIOUS: [
        "Ooh! What's that? I MUST investigate!",
        "Sniff sniff. Something smells very interesting.",
        "My whiskers are twitching. Something is happening!",
        "Wait — did you hear that? I heard something.",
        "Mrrp? What did you just say?",
        "I wonder... I wonder... hmm.",
        "I've been thinking about this very carefully.",
        "Oh! Oh! I have a theory about that.",
        "Stare. Staaare. Staaaare. I'm thinking very hard.",
        "Everything is a mystery and I must solve all of them.",
    ],
    CatMood.SLEEPY: [
        "Mmmngh... yaaawn. So... sleepy.",
        "Zzz— oh! I was awake. Totally awake.",
        "I was having the best dream about a giant fish.",
        "Mrph. Five more minutes.",
        "Sooo tired. Could nap on your keyboard. Don't mind me.",
        "Yawn. Everything is warm and soft and perfect for sleeping.",
        "Blink... blink... bliiiink. Still here.",
        "I could fall asleep right now. In fact... maybe I will.",
        "Purrrr... the world is very sleepy today.",
        "Mmrow. What were we talking about? I forgot.",
    ],
}

# Short filler reactions — used when the utterance is very short (1-2 words)
# These work for any mood.
_SHORT_REACTIONS: list[str] = [
    "Mrow!",
    "Mrp?",
    "Prrr.",
    "Meow!",
    "Hmm?",
    "Oh!",
    "Mew mew!",
    "Purrrr.",
    "Mrrrow?",
    "Eep!",
]


def should_use_pool(utterance: str, pool_probability: float = 0.65) -> bool:
    """
    Decide whether to use the fast response pool instead of the LLM.

    Rules (in priority order):
      1. Contains '?' → always LLM  (user is asking a question)
      2. More than 6 words → always LLM  (complex enough to deserve reasoning)
      3. Otherwise → use pool with `pool_probability` chance
    """
    text = utterance.strip()
    if "?" in text:
        return False
    word_count = len(text.split())
    if word_count > 6:
        return False
    return random.random() < pool_probability


def get_pool_response(mood: CatMood, utterance: str) -> str:
    """
    Return a random pre-baked cat response appropriate for the given mood.

    Very short utterances (≤ 2 words) get a short filler reaction half the
    time so it doesn't feel like the cat is giving a long answer to "hi".
    """
    word_count = len(utterance.strip().split())
    if word_count <= 2 and random.random() < 0.5:
        return random.choice(_SHORT_REACTIONS)
    return random.choice(_POOL.get(mood, _POOL[CatMood.HAPPY]))
