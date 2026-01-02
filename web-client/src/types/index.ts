// Game states (matches backend SessionStatus)
export type GameState = 'idle' | 'listening' | 'processing' | 'speaking';

// WebSocket event types
export type EventType =
  | 'state'
  | 'transcript.partial'
  | 'transcript.final'
  | 'reply.text'
  | 'reply.audio_ready'
  | 'error';

// WebSocket event payload
export interface WebSocketEvent {
  type: EventType;
  session_id: string;
  turn_id?: string;
  ts: string;
  payload: Record<string, any>;
}

// State event payload
export interface StatePayload {
  state: GameState;
}

// Transcript event payload
export interface TranscriptPayload {
  text: string;
}

// Reply text event payload
export interface ReplyTextPayload {
  text: string;
}

// Audio ready event payload
export interface AudioReadyPayload {
  url: string;
  duration_ms: number;
  format: string;
  sample_rate_hz: number;
  channels: number;
}

// Error event payload
export interface ErrorPayload {
  code: string;
  message: string;
}

// Session start request
export interface SessionStartRequest {
  session_id?: string;
  language?: string;
  mode?: string;
}

// Session start response
export interface SessionStartResponse {
  session_id: string;
  status: string;
}

// Session stop request
export interface SessionStopRequest {
  session_id: string;
  return_audio?: boolean;
}

// Session stop response
export interface SessionStopResponse {
  session_id: string;
  status: string;
}
