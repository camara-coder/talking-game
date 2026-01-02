/**
 * Browser Microphone Capture using MediaRecorder API
 * Captures audio from the user's microphone and provides chunks for streaming
 */

export type AudioChunkCallback = (chunk: Blob) => void;
export type ErrorCallback = (error: Error) => void;

export interface MicrophoneOptions {
  /** Audio sample rate (default: 16000 for STT) */
  sampleRate?: number;
  /** Audio chunk duration in milliseconds (default: 100ms) */
  chunkDuration?: number;
  /** MIME type for audio recording */
  mimeType?: string;
}

export class MicrophoneCapture {
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private isRecording = false;

  private onChunkCallback: AudioChunkCallback | null = null;
  private onErrorCallback: ErrorCallback | null = null;

  private options: Required<MicrophoneOptions>;

  constructor(options: MicrophoneOptions = {}) {
    this.options = {
      sampleRate: options.sampleRate ?? 16000,
      chunkDuration: options.chunkDuration ?? 100,
      mimeType: options.mimeType ?? this.getSupportedMimeType(),
    };
  }

  /**
   * Request microphone permission and initialize audio stream
   */
  async initialize(): Promise<void> {
    try {
      // Request microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1, // Mono
          sampleRate: this.options.sampleRate,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      console.log('Microphone access granted');
      console.log('Audio constraints:', {
        sampleRate: this.options.sampleRate,
        mimeType: this.options.mimeType,
      });
    } catch (error) {
      const err = error as Error;
      console.error('Failed to access microphone:', err);

      if (err.name === 'NotAllowedError') {
        throw new Error('Microphone permission denied. Please allow microphone access.');
      } else if (err.name === 'NotFoundError') {
        throw new Error('No microphone found. Please connect a microphone.');
      } else {
        throw new Error(`Failed to access microphone: ${err.message}`);
      }
    }
  }

  /**
   * Start recording audio
   */
  async startRecording(): Promise<void> {
    if (this.isRecording) {
      console.warn('Already recording');
      return;
    }

    if (!this.audioStream) {
      await this.initialize();
    }

    if (!this.audioStream) {
      throw new Error('Audio stream not initialized');
    }

    try {
      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: this.options.mimeType,
      });

      // Handle audio data chunks
      this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          console.log(`Audio chunk received: ${event.data.size} bytes`);
          if (this.onChunkCallback) {
            this.onChunkCallback(event.data);
          }
        }
      };

      // Handle errors
      this.mediaRecorder.onerror = (event: Event) => {
        const error = new Error(`MediaRecorder error: ${(event as any).error}`);
        console.error(error);
        if (this.onErrorCallback) {
          this.onErrorCallback(error);
        }
      };

      // Start recording with time slices
      this.mediaRecorder.start(this.options.chunkDuration);
      this.isRecording = true;

      console.log('Recording started');
    } catch (error) {
      const err = error as Error;
      console.error('Failed to start recording:', err);
      throw new Error(`Failed to start recording: ${err.message}`);
    }
  }

  /**
   * Stop recording audio
   */
  async stopRecording(): Promise<void> {
    if (!this.isRecording || !this.mediaRecorder) {
      console.warn('Not currently recording');
      return;
    }

    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve();
        return;
      }

      this.mediaRecorder.onstop = () => {
        console.log('Recording stopped');
        this.isRecording = false;
        resolve();
      };

      // Stop the recorder
      if (this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      } else {
        this.isRecording = false;
        resolve();
      }
    });
  }

  /**
   * Release microphone resources
   */
  destroy(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.audioStream) {
      this.audioStream.getTracks().forEach((track) => track.stop());
      this.audioStream = null;
    }

    this.mediaRecorder = null;
    this.isRecording = false;
    this.onChunkCallback = null;
    this.onErrorCallback = null;

    console.log('Microphone resources released');
  }

  /**
   * Register callback for audio chunks
   */
  onChunk(callback: AudioChunkCallback): void {
    this.onChunkCallback = callback;
  }

  /**
   * Register callback for errors
   */
  onError(callback: ErrorCallback): void {
    this.onErrorCallback = callback;
  }

  /**
   * Get the best supported MIME type for audio recording
   */
  private getSupportedMimeType(): string {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        console.log(`Using MIME type: ${type}`);
        return type;
      }
    }

    // Fallback to browser default
    console.warn('No preferred MIME type supported, using browser default');
    return '';
  }

  /**
   * Check if currently recording
   */
  get recording(): boolean {
    return this.isRecording;
  }

  /**
   * Check if microphone is initialized
   */
  get initialized(): boolean {
    return this.audioStream !== null;
  }

  /**
   * Get current audio stream
   */
  get stream(): MediaStream | null {
    return this.audioStream;
  }
}
