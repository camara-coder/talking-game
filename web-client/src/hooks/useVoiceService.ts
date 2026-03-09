import { useState, useEffect, useCallback, useRef } from 'react';
import { VoiceServiceAPI } from '../services/api';
import { VoiceWebSocketClient } from '../services/websocket';
import { AudioPlayer } from '../lib/audio';
import { MicrophoneCapture } from '../lib/microphone';
import { CatSoundManager } from '../lib/cat-sounds';
import type {
  GameState,
  CatMood,
  AudioReadyPayload,
  CatSoundPayload,
  CatProactivePayload,
  CatMoodChangePayload,
  CatBehaviorPayload,
} from '../types';

const SESSION_STORAGE_KEY = 'voice_session_id';

export interface UseVoiceServiceResult {
  gameState: GameState;
  catMood: CatMood;
  transcript: string;
  replyText: string;
  error: string | null;
  isConnected: boolean;
  startListening: () => Promise<void>;
  stopListening: () => Promise<void>;
  clearSession: () => Promise<void>;
}

export function useVoiceService(): UseVoiceServiceResult {
  const [gameState, setGameState] = useState<GameState>('idle');
  const [catMood, setCatMood] = useState<CatMood>('happy');
  const [transcript, setTranscript] = useState('');
  const [replyText, setReplyText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');

  const apiRef = useRef<VoiceServiceAPI>(new VoiceServiceAPI());
  const wsRef = useRef<VoiceWebSocketClient>(new VoiceWebSocketClient());
  const audioPlayerRef = useRef<AudioPlayer>(new AudioPlayer());
  const catSoundsRef = useRef<CatSoundManager>(new CatSoundManager());
  const microphoneRef = useRef<MicrophoneCapture>(
    new MicrophoneCapture({ sampleRate: 16000, chunkDuration: 100 })
  );

  // Serialised audio queue — ensures multi-segment replies (streaming TTS)
  // play back-to-back rather than overlapping.
  const audioQueueRef = useRef<string[]>([]);
  const audioPlayingRef = useRef(false);

  // Setup WebSocket event handlers
  useEffect(() => {
    const ws = wsRef.current;
    const audioPlayer = audioPlayerRef.current;
    const catSounds = catSoundsRef.current;

    // ── Core voice events ─────────────────────────
    ws.on('state', (payload) => {
      setGameState(payload.state);
    });

    ws.on('transcript.partial', (payload) => {
      setTranscript(payload.text);
    });

    ws.on('transcript.final', (payload) => {
      setTranscript(payload.text);
    });

    ws.on('reply.text', (payload) => {
      setReplyText(payload.text);
    });

    // Drain the audio queue sequentially.  Each segment is played to
    // completion before the next starts.  gameState returns to 'idle'
    // only when the queue is fully empty.
    async function drainAudioQueue() {
      if (audioPlayingRef.current) return;
      audioPlayingRef.current = true;
      setGameState('speaking');
      while (audioQueueRef.current.length > 0) {
        const url = audioQueueRef.current.shift()!;
        try {
          const audioData = await apiRef.current.downloadAudio(url);
          await audioPlayer.playAudio(audioData);
        } catch (err) {
          console.error('Failed to play audio segment:', err);
        }
      }
      audioPlayingRef.current = false;
      setGameState('idle');
    }

    ws.on('reply.audio_ready', (payload: AudioReadyPayload) => {
      audioQueueRef.current.push(payload.url);
      drainAudioQueue();
    });

    ws.on('error', (payload) => {
      console.error('WebSocket error:', payload.message);
      setError(payload.message);
      setGameState('idle');
    });

    // ── Cat-specific events ───────────────────────

    // Passive sounds (meow, purr, yawn) — synthesized in-browser
    ws.on('cat.sound', (payload: CatSoundPayload) => {
      console.log(`🐱 Cat sound: ${payload.sound_name} (mood: ${payload.mood})`);
      catSounds.play(payload.sound_name as any);
    });

    // Cat initiates a conversation proactively
    ws.on('cat.proactive', async (payload: CatProactivePayload) => {
      try {
        console.log(`🐱 Proactive: "${payload.text}" (mood: ${payload.mood})`);
        setReplyText(payload.text);
        setTranscript('');
        setGameState('speaking');
        setCatMood(payload.mood);

        const audioData = await apiRef.current.downloadAudio(payload.audio_url);
        await audioPlayer.playAudio(audioData);
      } catch (err) {
        console.error('Failed to play proactive audio:', err);
        setGameState('idle');
      }
    });

    // Mood change notification
    ws.on('cat.mood_change', (payload: CatMoodChangePayload) => {
      console.log(`🐱 Mood changed to: ${payload.mood}`);
      setCatMood(payload.mood);
    });

    // Cat behavioral state (silly, sleeping, etc.)
    ws.on('cat.state', (payload) => {
      const s = payload.state;
      if (s === 'sleeping' || s === 'silly' || s === 'idle' || s === 'speaking') {
        setGameState(s as GameState);
      }
    });

    // Physical cat behavior — animate + show caption, no audio
    ws.on('cat.behavior', (payload: CatBehaviorPayload) => {
      console.log(`🐱 Behavior: ${payload.behavior} — "${payload.text}"`);
      setReplyText(payload.text);
      setTranscript('');
      setCatMood(payload.mood);
      const anim = payload.animation as GameState;
      setGameState(anim);
      setTimeout(() => {
        setGameState('idle');
        setReplyText('');
      }, payload.duration_ms);
    });

    // Playback-complete is handled by drainAudioQueue above.

    // Unlock audio on the very first user interaction so proactive speech
    // and passive sounds work even before the mic button is pressed.
    const unlockOnFirstInteraction = () => {
      audioPlayer.unlock();
      catSounds.unlock();
    };
    document.addEventListener('click', unlockOnFirstInteraction, { once: true });
    document.addEventListener('touchstart', unlockOnFirstInteraction, { once: true });

    return () => {
      ws.disconnect();
      audioPlayer.destroy();
      catSounds.destroy();
      microphoneRef.current.destroy();
      document.removeEventListener('click', unlockOnFirstInteraction);
      document.removeEventListener('touchstart', unlockOnFirstInteraction);
    };
  }, []);

  // Initialize connection and resume session
  useEffect(() => {
    const initConnection = async () => {
      try {
        await apiRef.current.checkHealth();
        setIsConnected(true);

        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
        const request = storedSessionId ? { session_id: storedSessionId } : {};
        const response = await apiRef.current.startSession(request);
        const newSessionId = response.session_id;
        setSessionId(newSessionId);
        localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);

        console.log(storedSessionId ? `Session resumed: ${newSessionId}` : `New session: ${newSessionId}`);
        await wsRef.current.connect(newSessionId);
      } catch (err) {
        console.error('Failed to connect to voice service:', err);
        setError('Voice service is not available');
        setIsConnected(false);
      }
    };

    initConnection();

    const requestMicPermission = async () => {
      try {
        await microphoneRef.current.initialize();
      } catch (err) {
        setError((err as Error).message);
      }
    };
    requestMicPermission();
  }, []);

  const startListening = useCallback(async () => {
    try {
      setError(null);
      setTranscript('');
      setReplyText('');

      // Unlock audio on user gesture (required for mobile/Safari)
      await audioPlayerRef.current.unlock();
      catSoundsRef.current.unlock();

      if (!sessionId) throw new Error('Session not initialized');

      const ws = wsRef.current;
      if (!ws.isConnected) {
        await ws.connect(sessionId);
      }

      const microphone = microphoneRef.current;
      await ws.sendAudioStart({
        sample_rate: microphone.actualSampleRate,
        channels: 1,
        format: 'pcm16',
      });

      microphone.onChunk(async (chunk: ArrayBuffer) => {
        try { await ws.sendAudioChunk(chunk); } catch (_) {}
      });

      microphone.onError((err: Error) => {
        setError(err.message);
        setGameState('idle');
      });

      await microphone.startRecording();
      setGameState('listening');
    } catch (err) {
      setError((err as Error).message || 'Failed to start session');
      setGameState('idle');
    }
  }, [sessionId]);

  const stopListening = useCallback(async () => {
    if (!sessionId) return;
    try {
      setGameState('processing');
      await microphoneRef.current.stopRecording();
      await wsRef.current.sendAudioEnd();
    } catch (err) {
      setError('Failed to process request');
      setGameState('idle');
    }
  }, [sessionId]);

  const clearSession = useCallback(async () => {
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      const response = await apiRef.current.startSession();
      const newSessionId = response.session_id;
      setSessionId(newSessionId);
      localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);

      wsRef.current.disconnect();
      await wsRef.current.connect(newSessionId);

      setTranscript('');
      setReplyText('');
      setError(null);
      setGameState('idle');
      setCatMood('happy');
    } catch (err) {
      setError('Failed to start new conversation');
    }
  }, []);

  return {
    gameState,
    catMood,
    transcript,
    replyText,
    error,
    isConnected,
    startListening,
    stopListening,
    clearSession,
  };
}
