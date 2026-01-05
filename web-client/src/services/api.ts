import type {
  SessionStartRequest,
  SessionStartResponse,
  SessionStopRequest,
  SessionStopResponse,
} from '../types';

export class VoiceServiceAPI {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    // In production, use the full URL from environment variable
    // In development, use empty string to leverage Vite's proxy (relative paths)
    if (baseUrl) {
      this.baseUrl = baseUrl;
    } else if (import.meta.env.VITE_API_BASE_URL) {
      this.baseUrl = import.meta.env.VITE_API_BASE_URL;
    } else {
      // Development mode: use relative paths for Vite proxy
      this.baseUrl = '';
    }
  }

  async startSession(request: SessionStartRequest = {}): Promise<SessionStartResponse> {
    const response = await fetch(`${this.baseUrl}/api/session/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        language: 'en',
        mode: 'ptt',
        ...request,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }

    return response.json();
  }

  async stopSession(request: SessionStopRequest): Promise<SessionStopResponse> {
    const response = await fetch(`${this.baseUrl}/api/session/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        return_audio: true,
        ...request,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to stop session: ${response.statusText}`);
    }

    return response.json();
  }

  async downloadAudio(audioUrl: string): Promise<ArrayBuffer> {
    const response = await fetch(audioUrl);

    if (!response.ok) {
      throw new Error(`Failed to download audio: ${response.statusText}`);
    }

    return response.arrayBuffer();
  }

  async checkHealth(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return response.json();
  }
}
