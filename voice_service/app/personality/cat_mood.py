"""
Cat Mood State Machine
Manages Whiskers the cat's emotional state and response mode selection.
"""
import random
import logging
from enum import Enum
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class CatMood(str, Enum):
    HAPPY = "happy"
    BORED = "bored"
    CURIOUS = "curious"
    SLEEPY = "sleepy"


class ResponseMode(str, Enum):
    SILLY = "silly"
    PLAYFUL = "playful"
    THOUGHTFUL = "thoughtful"
    PURE_CAT = "pure_cat"


# Weighted response modes per mood (weights out of 100)
MOOD_RESPONSE_WEIGHTS: dict = {
    CatMood.HAPPY:    {ResponseMode.SILLY: 45, ResponseMode.PLAYFUL: 35, ResponseMode.THOUGHTFUL: 15, ResponseMode.PURE_CAT: 5},
    CatMood.BORED:    {ResponseMode.SILLY: 20, ResponseMode.PLAYFUL: 25, ResponseMode.THOUGHTFUL: 40, ResponseMode.PURE_CAT: 15},
    CatMood.CURIOUS:  {ResponseMode.SILLY: 25, ResponseMode.PLAYFUL: 35, ResponseMode.THOUGHTFUL: 35, ResponseMode.PURE_CAT: 5},
    CatMood.SLEEPY:   {ResponseMode.SILLY: 10, ResponseMode.PLAYFUL: 15, ResponseMode.THOUGHTFUL: 50, ResponseMode.PURE_CAT: 25},
}

# Proactive speech intervals per mood (min_sec, max_sec)
PROACTIVE_INTERVALS: dict = {
    CatMood.HAPPY:   (20.0, 40.0),
    CatMood.BORED:   (12.0, 25.0),
    CatMood.CURIOUS: (25.0, 50.0),
    CatMood.SLEEPY:  (60.0, 120.0),
}

# Physical behavior intervals per mood (min_sec, max_sec) — lightweight, no LLM needed
BEHAVIOR_INTERVALS: dict = {
    CatMood.HAPPY:   (12.0, 20.0),
    CatMood.BORED:   (15.0, 28.0),
    CatMood.CURIOUS: (8.0, 18.0),
    CatMood.SLEEPY:  (40.0, 80.0),
}

# Physical behaviors per mood — (behavior_key, display_text, animation_hint, duration_ms)
# animation_hint maps to GameState on the frontend
BEHAVIORS_BY_MOOD: dict = {
    CatMood.HAPPY: [
        ("zoom",        "*suddenly activates ZOOMIES for no reason*",              "silly",      3500),
        ("knock_off",   "*stares into your eyes and slowly pushes thing off table*","silly",      2500),
        ("show_belly",  "*dramatically flops over and exposes belly*",              "silly",      4000),
        ("bring_gift",  "*drops a crinkle ball at your feet proudly*",              "speaking",   3000),
        ("demand_pets", "*headbutts your hand repeatedly until pet*",               "speaking",   3500),
        ("chase_tail",  "*spots own tail... ATTACK MODE engaged*",                  "silly",      3000),
    ],
    CatMood.BORED: [
        ("stare_wall",  "*has been staring at that corner for 10 minutes*",         "processing", 5000),
        ("knock_off",   "*knocks thing off table... stares you dead in the eyes*",  "silly",      3000),
        ("demand_pets", "*sits directly on your keyboard demanding attention*",      "speaking",   4000),
        ("groom",       "*begins extensive grooming session, ignoring everything*",  "idle",       5000),
        ("yawn_stretch","*yawns enormously, showing every single tooth*",           "idle",       3500),
    ],
    CatMood.CURIOUS: [
        ("stare_wall",  "*investigates that suspicious spot on the wall INTENSELY*","processing", 4000),
        ("chirp",       "*chatters excitedly at a bird through the window*",        "speaking",   3000),
        ("demand_pets", "*tilts head sideways and stares at you with big eyes*",    "speaking",   3500),
        ("groom",       "*pauses mid-groom to think about something important*",    "idle",       4000),
        ("chase_tail",  "*becomes suddenly aware of tail — must destroy it*",       "silly",      3000),
        ("sniff_around","*sniffs every corner of the room with great suspicion*",   "processing", 4500),
    ],
    CatMood.SLEEPY: [
        ("groom",       "*licks paw in slow motion and wipes face dreamily*",       "idle",       5000),
        ("nap",         "*curls into a perfect circle and closes eyes*",            "sleeping",   10000),
        ("yawn_stretch","*stretches in an impossibly long way then collapses*",     "idle",       4000),
        ("stare_wall",  "*stares at nothing with half-closed eyes*",                "processing", 5000),
    ],
}

# Passive sound intervals per mood (min_sec, max_sec)
PASSIVE_SOUND_INTERVALS: dict = {
    CatMood.HAPPY:   (20.0, 40.0),
    CatMood.BORED:   (30.0, 60.0),
    CatMood.CURIOUS: (25.0, 45.0),
    CatMood.SLEEPY:  (40.0, 80.0),
}

# Passive sounds per mood (names map to frontend Web Audio synthesis)
PASSIVE_SOUNDS: dict = {
    CatMood.HAPPY:   ["purr", "meow_short", "meow_happy", "meow_short", "purr"],
    CatMood.BORED:   ["meow_long", "yawn", "meow_bored", "yawn"],
    CatMood.CURIOUS: ["meow_short", "meow_curious", "meow_short", "meow_curious"],
    CatMood.SLEEPY:  ["purr", "yawn", "purr", "meow_sleepy"],
}


class MoodManager:
    """Manages the cat's mood and behavioral state."""

    def __init__(self):
        self.current_mood: CatMood = CatMood.HAPPY
        self.last_interaction: datetime = datetime.utcnow()
        self.consecutive_interactions: int = 0

    def on_user_interaction(self) -> Optional[CatMood]:
        """
        Call when the user speaks. May trigger mood transition.
        Returns new mood if it changed, None otherwise.
        """
        self.last_interaction = datetime.utcnow()
        self.consecutive_interactions += 1
        prev = self.current_mood

        if self.current_mood == CatMood.BORED:
            self.current_mood = random.choice([CatMood.HAPPY, CatMood.CURIOUS])
            logger.info(f"Mood: bored → {self.current_mood} (user woke me up!)")

        elif self.current_mood == CatMood.SLEEPY and random.random() < 0.65:
            self.current_mood = CatMood.CURIOUS
            self.consecutive_interactions = 0
            logger.info("Cat woke up! sleepy → curious")

        elif self.current_mood == CatMood.CURIOUS and self.consecutive_interactions >= 3:
            self.current_mood = CatMood.HAPPY
            self.consecutive_interactions = 0
            logger.info("Mood: curious → happy (3 interactions reached)")

        return self.current_mood if self.current_mood != prev else None

    def tick(self) -> Optional[CatMood]:
        """
        Periodic mood check — call this every ~60 seconds.
        Returns new mood if it changed, None otherwise.
        """
        now = datetime.utcnow()
        elapsed_min = (now - self.last_interaction).total_seconds() / 60.0
        prev = self.current_mood

        # happy → bored after 10 min inactivity
        if self.current_mood == CatMood.HAPPY and elapsed_min > 10:
            self.current_mood = CatMood.BORED

        # Random sleepiness after 30 min (5% chance per tick)
        elif self.current_mood != CatMood.SLEEPY and elapsed_min > 30 and random.random() < 0.05:
            self.current_mood = CatMood.SLEEPY

        # Sleepy cat randomly wakes up after a nap
        elif self.current_mood == CatMood.SLEEPY and elapsed_min > 5 and random.random() < 0.12:
            self.current_mood = random.choice([CatMood.HAPPY, CatMood.CURIOUS, CatMood.BORED])
            self.consecutive_interactions = 0

        if prev != self.current_mood:
            logger.info(f"Mood tick: {prev} → {self.current_mood}")
            return self.current_mood
        return None

    def get_response_mode(self) -> ResponseMode:
        """Weighted random response mode based on current mood."""
        weights = MOOD_RESPONSE_WEIGHTS[self.current_mood]
        modes = list(weights.keys())
        wts = [weights[m] for m in modes]
        return random.choices(modes, weights=wts, k=1)[0]

    def get_proactive_interval(self) -> float:
        """Seconds until next proactive speech attempt."""
        lo, hi = PROACTIVE_INTERVALS[self.current_mood]
        return random.uniform(lo, hi)

    def get_behavior_interval(self) -> float:
        """Seconds until next physical behavior."""
        lo, hi = BEHAVIOR_INTERVALS[self.current_mood]
        return random.uniform(lo, hi)

    def get_random_behavior(self) -> tuple:
        """Return a random (behavior_key, text, animation, duration_ms) for current mood."""
        behaviors = BEHAVIORS_BY_MOOD[self.current_mood]
        return random.choice(behaviors)

    def get_passive_sound_interval(self) -> float:
        """Seconds until next passive noise."""
        lo, hi = PASSIVE_SOUND_INTERVALS[self.current_mood]
        return random.uniform(lo, hi)

    def get_passive_sound(self) -> str:
        """Random passive sound name for current mood."""
        return random.choice(PASSIVE_SOUNDS[self.current_mood])
