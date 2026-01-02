import type {
  WebSocketEvent,
  StatePayload,
  TranscriptPayload,
  ReplyTextPayload,
  AudioReadyPayload,
  ErrorPayload,
} from '../types';

export type EventCallback<T = any> = (payload: T) => void;

interface AudioStartMessage {
  type: 'audio.start';
  session_id: string;
  config: {
    sample_rate: number;
    channels: number;
    format: string;
  };
}

interface AudioChunkMessage {
  type: 'audio.chunk';
  session_id: string;
  data: ArrayBuffer;
}

interface AudioEndMessage {
  type: 'audio.end';
  session_id: string;
}

export class VoiceWebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private eventHandlers: Map<string, EventCallback[]> = new Map();
  private connectionPromise: Promise<void> | null = null;

  constructor(private baseUrl: string = import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8008') {}

  async connect(sessionId: string): Promise<void> {
    // If already connecting, return existing promise
    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    // If already connected to the same session, return immediately
    if (this.isConnected && this.sessionId === sessionId) {
      console.log('Already connected to session:', sessionId);
      return Promise.resolve();
    }

    this.sessionId = sessionId;
    const wsUrl = `${this.baseUrl}/ws?session_id=${sessionId}`;

    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        console.log('Connecting to WebSocket:', wsUrl);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected successfully');
          this.reconnectAttempts = 0;
          this.connectionPromise = null;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: WebSocketEvent = JSON.parse(event.data);
            this.handleEvent(data);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.connectionPromise = null;
          reject(new Error('WebSocket connection failed'));
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.connectionPromise = null;
          this.attemptReconnect();
        };
      } catch (error) {
        this.connectionPromise = null;
        reject(error);
      }
    });

    return this.connectionPromise;
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = '';
    this.eventHandlers.clear();
    this.connectionPromise = null;
  }

  /**
   * Send audio start message to backend
   */
  async sendAudioStart(config: { sample_rate: number; channels: number; format: string }): Promise<void> {
    await this.ensureConnected();

    const message: AudioStartMessage = {
      type: 'audio.start',
      session_id: this.sessionId,
      config,
    };

    this.send(JSON.stringify(message));
    console.log('Sent audio.start message');
  }

  /**
   * Send audio chunk to backend
   */
  async sendAudioChunk(audioData: Blob): Promise<void> {
    await this.ensureConnected();

    // Convert Blob to ArrayBuffer
    const arrayBuffer = await audioData.arrayBuffer();

    // For binary data, we send it directly
    // The backend should handle binary frames
    this.send(arrayBuffer);

    console.log(`Sent audio chunk: ${arrayBuffer.byteLength} bytes`);
  }

  /**
   * Send audio end message to backend
   */
  async sendAudioEnd(): Promise<void> {
    await this.ensureConnected();

    const message: AudioEndMessage = {
      type: 'audio.end',
      session_id: this.sessionId,
    };

    this.send(JSON.stringify(message));
    console.log('Sent audio.end message');
  }

  private async ensureConnected(): Promise<void> {
    if (!this.isConnected) {
      throw new Error('WebSocket is not connected');
    }

    // Wait for connection to be ready
    let attempts = 0;
    while (this.ws && this.ws.readyState === WebSocket.CONNECTING && attempts < 50) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      attempts++;
    }

    if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not ready');
    }
  }

  private send(data: string | ArrayBuffer): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('Cannot send: WebSocket not open');
    }

    this.ws.send(data);
  }

  private handleEvent(event: WebSocketEvent): void {
    const handlers = this.eventHandlers.get(event.type);
    if (handlers) {
      handlers.forEach((handler) => handler(event.payload));
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.sessionId) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.connect(this.sessionId).catch((error) => {
          console.error('Reconnection failed:', error);
        });
      }, this.reconnectDelay);
    }
  }

  // Event listeners
  on(eventType: 'state', callback: EventCallback<StatePayload>): void;
  on(eventType: 'transcript.partial', callback: EventCallback<TranscriptPayload>): void;
  on(eventType: 'transcript.final', callback: EventCallback<TranscriptPayload>): void;
  on(eventType: 'reply.text', callback: EventCallback<ReplyTextPayload>): void;
  on(eventType: 'reply.audio_ready', callback: EventCallback<AudioReadyPayload>): void;
  on(eventType: 'error', callback: EventCallback<ErrorPayload>): void;
  on(eventType: string, callback: EventCallback): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(callback);
  }

  off(eventType: string, callback?: EventCallback): void {
    if (!callback) {
      this.eventHandlers.delete(eventType);
      return;
    }

    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(callback);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  get currentSessionId(): string {
    return this.sessionId;
  }
}
