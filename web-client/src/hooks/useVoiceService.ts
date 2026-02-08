import { useState, useEffect, useCallback, useRef } from 'react';
import { VoiceServiceAPI } from '../services/api';
import { VoiceWebSocketClient } from '../services/websocket';
import { AudioPlayer } from '../lib/audio';
import { MicrophoneCapture } from '../lib/microphone';
import type { GameState, AudioReadyPayload } from '../types';

const SESSION_STORAGE_KEY = 'voice_session_id';

export interface UseVoiceServiceResult {
  gameState: GameState;
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
  const [transcript, setTranscript] = useState('');
  const [replyText, setReplyText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');

  const apiRef = useRef<VoiceServiceAPI>(new VoiceServiceAPI());
  const wsRef = useRef<VoiceWebSocketClient>(new VoiceWebSocketClient());
  const audioPlayerRef = useRef<AudioPlayer>(new AudioPlayer());
  const microphoneRef = useRef<MicrophoneCapture>(
    new MicrophoneCapture({
      sampleRate: 16000, // 16kHz for STT
      chunkDuration: 100, // Send chunks every 100ms
    })
  );

  // Setup WebSocket event handlers
  useEffect(() => {
    const ws = wsRef.current;
    const audioPlayer = audioPlayerRef.current;

    // State change handler
    ws.on('state', (payload) => {
      console.log('State changed:', payload.state);
      setGameState(payload.state);
    });

    // Transcript handlers
    ws.on('transcript.partial', (payload) => {
      console.log('Partial transcript:', payload.text);
      setTranscript(payload.text);
    });

    ws.on('transcript.final', (payload) => {
      console.log('Final transcript:', payload.text);
      setTranscript(payload.text);
    });

    // Reply text handler
    ws.on('reply.text', (payload) => {
      console.log('Reply text:', payload.text);
      setReplyText(payload.text);
    });

    // Audio ready handler
    ws.on('reply.audio_ready', async (payload: AudioReadyPayload) => {
      try {
        console.log('🎵 Audio ready event received');
        console.log('  URL:', payload.url);
        console.log('  Duration:', payload.duration_ms, 'ms');
        console.log('  Format:', payload.format);
        console.log('  Sample rate:', payload.sample_rate_hz, 'Hz');

        setGameState('speaking');

        console.log('📥 Downloading audio from:', payload.url);
        const audioData = await apiRef.current.downloadAudio(payload.url);
        console.log('✅ Audio downloaded:', audioData.byteLength, 'bytes');

        console.log('▶️ Playing audio...');
        await audioPlayer.playAudio(audioData);
        console.log('✅ Audio playback initiated');
      } catch (err) {
        console.error('❌ Failed to play audio:', err);
        setError('Failed to play audio');
        setGameState('idle');
      }
    });

    // Error handler
    ws.on('error', (payload) => {
      console.error('WebSocket error:', payload.message);
      setError(payload.message);
      setGameState('idle');
    });

    // Audio playback complete handler
    audioPlayer.onPlaybackComplete(() => {
      console.log('Audio playback complete');
      setGameState('idle');
    });

    // Cleanup
    return () => {
      ws.disconnect();
      audioPlayer.destroy();
      microphoneRef.current.destroy();
    };
  }, []);

  // Initialize connection and resume or create persistent session
  useEffect(() => {
    const initConnection = async () => {
      try {
        // Check health
        const health = await apiRef.current.checkHealth();
        console.log('Voice service health:', health);
        setIsConnected(true);

        // Check localStorage for an existing session to resume
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
        const request = storedSessionId
          ? { session_id: storedSessionId }
          : {};

        // Resume existing session from DB or create a new one
        const response = await apiRef.current.startSession(request);
        const newSessionId = response.session_id;
        setSessionId(newSessionId);

        // Persist session_id so it survives page refreshes
        localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);

        console.log(
          storedSessionId
            ? `Session resumed: ${newSessionId}`
            : `New session created: ${newSessionId}`
        );

        // Connect WebSocket with persistent session
        await wsRef.current.connect(newSessionId);
        console.log('WebSocket connected');
      } catch (err) {
        console.error('Failed to connect to voice service:', err);
        setError('Voice service is not available');
        setIsConnected(false);
      }
    };

    initConnection();

    // Request microphone permission on mount
    const requestMicPermission = async () => {
      try {
        await microphoneRef.current.initialize();
        console.log('Microphone initialized');
      } catch (err) {
        console.error('Microphone initialization failed:', err);
        setError((err as Error).message);
      }
    };

    requestMicPermission();
  }, []);

  const startListening = useCallback(async () => {
    try {
      console.log('Starting listening...');
      setError(null);
      setTranscript('');
      setReplyText('');

      // Unlock audio context for mobile browsers (must be in user gesture handler)
      await audioPlayerRef.current.unlock();

      // Verify session is initialized
      if (!sessionId) {
        throw new Error('Session not initialized');
      }

      console.log('Using persistent session:', sessionId);

      // WebSocket should already be connected from useEffect
      // Just verify connection state
      const ws = wsRef.current;
      if (!ws.isConnected) {
        console.log('WebSocket disconnected, reconnecting...');
        await ws.connect(sessionId);
      }

      // Send audio configuration with the actual sample rate from the AudioContext.
      // On Android Chrome, the browser may use the device's native rate (e.g. 48kHz)
      // instead of the requested 16kHz. The backend will resample if needed.
      const microphone = microphoneRef.current;
      await ws.sendAudioStart({
        sample_rate: microphone.actualSampleRate,
        channels: 1,
        format: 'pcm16',
      });

      // Setup microphone to stream audio chunks
      microphone.onChunk(async (chunk: ArrayBuffer) => {
        try {
          await ws.sendAudioChunk(chunk);
        } catch (err) {
          console.error('Failed to send audio chunk:', err);
        }
      });

      microphone.onError((err: Error) => {
        console.error('Microphone error:', err);
        setError(err.message);
        setGameState('idle');
      });

      // Start recording
      await microphone.startRecording();

      console.log('Recording started');
      setGameState('listening');
    } catch (err) {
      console.error('Failed to start listening:', err);
      setError((err as Error).message || 'Failed to start session');
      setGameState('idle');
    }
  }, [sessionId]); // Add sessionId as dependency

  const stopListening = useCallback(async () => {
    if (!sessionId) {
      console.warn('No active session');
      return;
    }

    try {
      console.log('Stopping listening...');
      setGameState('processing');

      const microphone = microphoneRef.current;
      const ws = wsRef.current;

      // Stop recording
      await microphone.stopRecording();
      console.log('Recording stopped');

      // Send audio end signal
      await ws.sendAudioEnd();
      console.log('Audio end signal sent');

      // The backend will now process the audio and send back results via WebSocket
    } catch (err) {
      console.error('Failed to stop listening:', err);
      setError('Failed to process request');
      setGameState('idle');
    }
  }, [sessionId]);

  const clearSession = useCallback(async () => {
    try {
      console.log('Clearing session and starting fresh...');

      // Remove stored session so the next one is brand new
      localStorage.removeItem(SESSION_STORAGE_KEY);

      // Create a fresh session (no session_id → backend generates new)
      const response = await apiRef.current.startSession();
      const newSessionId = response.session_id;
      setSessionId(newSessionId);
      localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);

      // Reconnect WebSocket to new session
      wsRef.current.disconnect();
      await wsRef.current.connect(newSessionId);

      // Reset UI state
      setTranscript('');
      setReplyText('');
      setError(null);
      setGameState('idle');

      console.log('New session started:', newSessionId);
    } catch (err) {
      console.error('Failed to clear session:', err);
      setError('Failed to start new conversation');
    }
  }, []);

  return {
    gameState,
    transcript,
    replyText,
    error,
    isConnected,
    startListening,
    stopListening,
    clearSession,
  };
}
