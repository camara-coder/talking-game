# Cat Pet Simulator — Implementation Plan

## Overview

Transform the current push-to-talk voice assistant into a **living cat pet** that proactively interacts with the user. The cat has moods, makes passive sounds, initiates conversations, and replies with unpredictable silly or thoughtful behavior. The user never quite knows what to expect — that's the fun.

---

## Design Decisions (from requirements)

| Decision | Choice |
|---|---|
| Proactive behavior | Both — passive noises at short intervals AND random speech initiations |
| Cat sounds | Mix — TTS reads speech, real audio files for idle noises (meow, purr) |
| Visual character | Replace PixiJS character with animated cat sprite |
| Mood system | Yes — `happy`, `bored`, `curious`, `sleepy` with behavioral effects |

---

## Behavioral Model

### Response Modes

Each time the cat replies to a user message, it randomly picks a response mode (weighted by current mood):

| Mode | Description | Example |
|---|---|---|
| `SILLY` | Echoes user words with cat noise or makes absurd joke | User: "I'm hungry" → Cat: "Meeow hungry? Meow hungry meow?? *spins*" |
| `PLAYFUL` | Funny but coherent, cat-like humor | "Oh I'm always hungry too. I knocked my bowl over three times today." |
| `THOUGHTFUL` | Normal helpful response with cat personality | "Sounds like you should get a snack! I recommend tuna." |
| `PURE_CAT` | No real words — just sounds emitted as text | "Mrrrow. Prrrrr. Mew mew." |

### Mood States and Effects

| Mood | Silly% | Proactive interval | Passive sounds | Behavior notes |
|---|---|---|---|---|
| `happy` | 45% | 45–90s | Purring | High energy, frequent speech, enthusiastic replies |
| `bored` | 25% | 20–50s | Yawning + slow meow | Initiates often to get attention, dry/deadpan responses |
| `curious` | 30% | 60–120s | Quick meows | Asks follow-up questions, investigative |
| `sleepy` | 15% | 120–240s | Very slow purr | Slow/mumbled replies, occasionally "falls asleep" mid-response |

### Mood Transitions

```
happy ──(10min no interaction)──► bored
bored ──(user interacts)──► happy or curious (random)
curious ──(3+ turns answered)──► happy
sleepy ──(triggered at random, ~20% chance after 30min)──► any mood on wake
any ──(random ~5% per mood check interval)──► sleepy
```

Mood checks happen every 60 seconds.

---

## Proactive Behavior Engine

### Two Layers of Proactivity

**Layer 1 — Passive sounds (no TTS, no LLM):**
- Fires every **20–40 seconds** of user inactivity
- Frontend receives a `cat.sound` WebSocket event
- Plays a random ambient sound from the sound library (`idle_meow`, `purr`, `yawn`)
- Cat character animates accordingly

**Layer 2 — Proactive speech (LLM-generated, TTS-spoken):**
- Fires every **45–240 seconds** depending on mood (see table above)
- Backend calls LLM with a special "initiate conversation" prompt
- Backend generates TTS audio
- Frontend receives `cat.proactive` event with audio URL and text
- Cat character enters talking animation, caption appears, audio plays automatically

### Sample Proactive Messages (by mood)

```
happy:    "Hey!! Are you there?? I found something! ...I forgot what it was. Meow."
bored:    "Helloooo? I've been sitting here for like forever. Pet me."
curious:  "Hey, what are you doing? Can I watch? I'm very good at watching things."
sleepy:   "mrrrow... oh... were you saying something? ...zzz"
```

---

## Architecture Changes

### Backend: New Components

```
voice_service/app/
├── personality/                      ← NEW MODULE
│   ├── __init__.py
│   ├── cat_mood.py                   ← Mood state machine
│   ├── cat_prompts.py                ← LLM system prompts per mood/mode
│   └── proactive_engine.py          ← Background timer loop
├── api/
│   ├── ws.py                         ← MODIFIED: new event types
│   ├── routes.py                     ← MODIFIED: sound file serving
│   ├── session_manager.py            ← MODIFIED: mood in session state
│   └── models.py                     ← MODIFIED: CatMood enum, mood field
├── pipeline/
│   └── processors/
│       └── llm_ollama.py             ← MODIFIED: use cat prompts
└── config.py                         ← MODIFIED: cat config constants
```

### Frontend: Changes

```
web-client/src/
├── lib/
│   ├── cat-character.ts              ← NEW: Cat PixiJS sprite + animations
│   ├── cat-sounds.ts                 ← NEW: Sound effect manager
│   └── character.ts                  ← REPLACED by cat-character.ts
├── hooks/
│   └── useVoiceService.ts            ← MODIFIED: proactive events, mood events
├── components/
│   ├── CharacterCanvas.tsx           ← MODIFIED: use cat character
│   ├── MoodIndicator.tsx             ← NEW: subtle mood display
│   └── CaptionDisplay.tsx            ← MODIFIED: auto-show on proactive
├── App.tsx                           ← MODIFIED: new cat-themed UI
└── types/index.ts                    ← MODIFIED: new event types

web-client/public/
└── sounds/                           ← NEW: Cat sound assets
    ├── meow_short.wav
    ├── meow_long.wav
    ├── meow_silly.wav
    ├── purr_loop.wav
    ├── yawn.wav
    └── hiss_playful.wav
```

---

## Implementation Steps

### Phase 1 — Backend: Cat Personality Core

#### Step 1.1 — Mood State Machine (`cat_mood.py`)

```python
class CatMood(Enum):
    HAPPY = "happy"
    BORED = "bored"
    CURIOUS = "curious"
    SLEEPY = "sleepy"

class MoodManager:
    - current_mood: CatMood
    - last_interaction: datetime
    - mood_change_listeners: list[callable]

    + get_mood() → CatMood
    + on_user_interaction() → None  # may trigger transition
    + tick() → None                 # called every 60s, checks transitions
    + get_response_mode() → Literal["SILLY","PLAYFUL","THOUGHTFUL","PURE_CAT"]
```

#### Step 1.2 — Cat Prompts (`cat_prompts.py`)

One system prompt per combination of (mood × response_mode). Prompts enforce:
- Cat personality and name ("Whiskers")
- Max 2 sentences / 40 words
- Mood-appropriate energy level
- Mode-appropriate style (silly echo vs thoughtful)

Example prompt — `happy + SILLY`:
```
You are Whiskers, a silly happy cat who can talk. You LOVE attention.
The user just said something. Repeat their words back in a ridiculous cat way,
add meow or mrrrow sounds, be goofy and energetic.
Keep it under 2 sentences. You are delighted by everything.
```

Example prompt — `bored + THOUGHTFUL`:
```
You are Whiskers, a bored but smart cat. You can hold a conversation but
you're not that excited about it. Reply normally but sound slightly unimpressed.
Under 2 sentences. End with a dry cat observation.
```

#### Step 1.3 — Proactive Engine (`proactive_engine.py`)

```python
class ProactiveEngine:
    - session_id: str
    - mood_manager: MoodManager
    - ws_broadcast: callable
    - is_running: bool

    + start() → None          # starts background asyncio task
    + stop() → None
    + _passive_sound_loop()   # sends cat.sound events
    + _proactive_speech_loop()# calls LLM, TTS, sends cat.proactive event
    + _get_proactive_prompt() # prompt for cat-initiated speech
    + pause_on_user_active()  # stop timer when user is speaking
    + resume_on_idle()        # restart timer after response delivered
```

The engine runs two independent asyncio loops per session, both paused while user is interacting.

#### Step 1.4 — Modify Session Manager

Add to `Session` model:
```python
mood: CatMood = CatMood.HAPPY
proactive_engine: Optional[ProactiveEngine] = None
last_interaction_at: datetime
```

Engine starts when session is created. Engine stops on session timeout/cleanup.

#### Step 1.5 — New WebSocket Events

| Event | Direction | Payload |
|---|---|---|
| `cat.sound` | server→client | `{ sound_name: str, mood: str }` |
| `cat.proactive` | server→client | `{ text: str, audio_url: str, duration_ms: int, mood: str }` |
| `cat.mood_change` | server→client | `{ mood: str, previous_mood: str }` |
| `cat.state` | server→client | `{ state: "idle"\|"thinking"\|"talking"\|"sleeping"\|"silly" }` |

#### Step 1.6 — Modify LLM Processor

Replace static `SYSTEM_PROMPT` with dynamic lookup:
```python
async def generate_response(transcript, session, mood_manager):
    mode = mood_manager.get_response_mode()
    prompt = cat_prompts.get_prompt(mood_manager.current_mood, mode)
    # ... call Ollama with dynamic prompt
```

#### Step 1.7 — Sound File Serving

Add route: `GET /api/sounds/{sound_name}.wav`
Serves from `voice_service/data/sounds/` directory.
Add static cat sound WAV files to this directory.

---

### Phase 2 — Frontend: Cat Character

#### Step 2.1 — Cat Sound Manager (`cat-sounds.ts`)

```typescript
class CatSoundManager {
    private sounds: Map<string, HTMLAudioElement>

    preload(soundNames: string[]): void
    play(soundName: string): void
    playRandom(category: 'idle' | 'happy' | 'silly'): void
    stopAll(): void
}
```

Sounds preloaded from `/api/sounds/` on app init.

#### Step 2.2 — Cat Character Sprite (`cat-character.ts`)

Replace current `character.ts` with a cat sprite system using PixiJS:

**Character states:**
- `idle` — Slow tail swish, occasional blink, breathing animation
- `listening` — Ears perked up, leaning forward, tail still
- `thinking` — Tilted head, one ear down, tail curling slowly
- `talking` — Mouth opening/closing in sync, tail upright
- `silly` — Spinning, bouncing, eyes spinning, tongue out
- `sleeping` — Eyes closed, slow breathing, "zzz" particles
- `excited` (happy mood) — Jumping, wide eyes, rapid tail

**Sprite approach:**
- Use a spritesheet with cat animations (can start with a free/CC0 pixel art cat)
- Or use PixiJS Graphics API to draw a simple but expressive vector cat
- Recommended: vector cat using PixiJS Graphics for easy customization and no asset licensing issues

#### Step 2.3 — Mood Indicator Component (`MoodIndicator.tsx`)

Small subtle UI element showing current mood:
```
😸 Happy     😴 Sleepy     😒 Bored     🔍 Curious
```
Updates on `cat.mood_change` events.

#### Step 2.4 — Update `useVoiceService.ts` Hook

Add handlers:
```typescript
ws.on('cat.proactive', (data) => {
    // Auto-play TTS audio (no button press needed)
    audioPlayer.play(data.audio_url)
    setCaption(data.text)
    setCharacterState('talking')
    setMood(data.mood)
})

ws.on('cat.sound', (data) => {
    catSounds.play(data.sound_name)
    // Trigger short idle animation
})

ws.on('cat.mood_change', (data) => {
    setMood(data.mood)
    // Maybe show a small notification
})
```

#### Step 2.5 — Update `App.tsx` and UI

- Replace generic title with "Whiskers" cat name + mood indicator
- Remove or soften the "Push to Talk" label — rename to "Talk to Whiskers"
- Add subtle cat-themed background/color scheme (warm, cozy)
- Caption display shows cat's proactive speech automatically

---

### Phase 3 — Cat Assets

#### Sound Files (6 files, free/CC0 sources)

| File | Description | Usage |
|---|---|---|
| `meow_short.wav` | Quick meow | Idle passive sound |
| `meow_long.wav` | Long meow/yowl | Bored proactive noise |
| `meow_silly.wav` | High-pitched or goofy meow | Silly mode passive sound |
| `purr_loop.wav` | ~3 second purring loop | Happy idle, looped |
| `yawn.wav` | Cat yawn sound | Sleepy mood |
| `hiss_playful.wav` | Soft playful hiss | Curious mood |

Sources: freesound.org (CC0 license), or generated via script.

#### Cat Sprite

Option A (recommended for speed): **PixiJS Vector Cat**
- Drawn programmatically with `PIXI.Graphics`
- Body, head, ears, tail, eyes — each as separate `DisplayObject`
- Animates via `gsap` or simple frame-based tweens
- No external art assets needed
- Highly customizable mood expressions

Option B (richer visuals): **Spritesheet**
- Find CC0 pixel art cat (e.g., itch.io free assets)
- Use `PIXI.AnimatedSprite` with frames per state
- More work upfront but better visual result

Plan: **Start with Option A** (vector cat), make Option B a future enhancement.

---

## Configuration Updates (`config.py`)

```python
# Cat personality
CAT_NAME: str = "Whiskers"
CAT_PASSIVE_SOUND_INTERVAL_MIN: int = 20   # seconds
CAT_PASSIVE_SOUND_INTERVAL_MAX: int = 40   # seconds
CAT_PROACTIVE_SPEECH_INTERVAL_MIN: int = 45  # seconds (happy mood)
CAT_PROACTIVE_SPEECH_INTERVAL_MAX: int = 240 # seconds (sleepy mood)
CAT_MOOD_CHECK_INTERVAL: int = 60           # seconds
CAT_BORED_THRESHOLD_MINUTES: int = 10       # minutes before going bored
CAT_SILLY_BASE_PROBABILITY: float = 0.4     # base silly response chance
```

---

## Memory / Conversation Context

Keep existing conversation history (last 6 turns) but enrich context sent to LLM:

```python
context = {
    "turns": last_6_turns,
    "current_mood": mood_manager.current_mood,
    "response_mode": selected_mode,
    "time_since_last_interaction": elapsed_seconds,
}
```

The cat remembers recent conversation so it can reference it ("You mentioned being hungry earlier — did you eat?").

---

## Testing Plan

| Test | Type | What to verify |
|---|---|---|
| Mood transitions | Unit | `happy→bored` after inactivity threshold |
| Proactive interval | Unit | Engine fires within expected time window |
| Prompt selection | Unit | Correct prompt for each mood/mode combo |
| WebSocket events | Integration | `cat.proactive` delivers text + audio |
| Sound serving | Integration | `/api/sounds/*.wav` returns 200 |
| Frontend autoplay | E2E | Cat speaks without user pressing button |
| Mood indicator | Component | Updates on `cat.mood_change` event |

---

## Implementation Order

```
Week 1:
  [x] Phase 1.1 — Mood state machine
  [x] Phase 1.2 — Cat prompts
  [x] Phase 1.3 — Proactive engine (passive sounds first)
  [x] Phase 1.4 — Session manager update
  [x] Phase 1.5 — New WebSocket events

Week 2:
  [x] Phase 1.6 — LLM processor update
  [x] Phase 1.7 — Sound file route + assets
  [x] Phase 2.1 — Cat sound manager (frontend)
  [x] Phase 2.4 — useVoiceService hook updates

Week 3:
  [x] Phase 2.2 — Cat character (vector PixiJS cat)
  [x] Phase 2.3 — Mood indicator
  [x] Phase 2.5 — App.tsx UI update
  [x] Full integration testing
```

---

## Out of Scope (Future)

- Multiple pet types (dog, parrot, hamster)
- Pet hunger/energy stats (Tamagotchi-style)
- Unlockable cat accessories (hats, toys)
- Pet saves state between browser sessions
- Multiplayer (two kids interact with the same cat)
- Cat sprite art upgrade (spritesheet with professional illustrations)
