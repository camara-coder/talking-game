/**
 * Browser Microphone Capture using Web Audio API + AudioWorklet
 * Captures RAW PCM audio from the user's microphone for streaming
 * This avoids MediaRecorder's WebM chunk concatenation issues
 */

export type AudioChunkCallback = (chunk: ArrayBuffer) => void;
export type ErrorCallback = (error: Error) => void;

export interface MicrophoneOptions {
  /** Audio sample rate (default: 16000 for STT) */
  sampleRate?: number;
  /** Audio chunk duration in milliseconds (not used with AudioWorklet) */
  chunkDuration?: number;
  /** MIME type (not used with raw PCM) */
  mimeType?: string;
}

export class MicrophoneCapture {
  private audioContext: AudioContext | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  private audioStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private silentGainNode: GainNode | null = null;
  private isRecording = false;

  private onChunkCallback: AudioChunkCallback | null = null;
  private onErrorCallback: ErrorCallback | null = null;

  private options: Required<MicrophoneOptions>;

  constructor(options: MicrophoneOptions = {}) {
    this.options = {
      sampleRate: options.sampleRate ?? 16000,
      chunkDuration: options.chunkDuration ?? 100,
      mimeType: options.mimeType ?? '',
    };
  }

  /**
   * Request microphone permission and initialize audio stream + AudioContext
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

      // Create AudioContext with desired sample rate
      // Note: Android Chrome may ignore the requested sampleRate and use the
      // device's native rate (e.g. 44100 or 48000). We detect and handle this.
      this.audioContext = new AudioContext({
        sampleRate: this.options.sampleRate,
      });

      console.log('Microphone access granted');
      console.log('Audio constraints:', {
        requestedSampleRate: this.options.sampleRate,
        actualSampleRate: this.audioContext.sampleRate,
        sampleRateMatch: this.audioContext.sampleRate === this.options.sampleRate,
        format: 'PCM16',
      });

      if (this.audioContext.sampleRate !== this.options.sampleRate) {
        console.warn(
          `AudioContext sample rate mismatch: requested ${this.options.sampleRate}Hz, ` +
          `got ${this.audioContext.sampleRate}Hz. Backend will resample.`
        );
      }

      // Load AudioWorklet module
      await this.audioContext.audioWorklet.addModule('/pcm-processor.js');
      console.log('AudioWorklet processor loaded');

    } catch (error) {
      const err = error as Error;
      console.error('Failed to initialize audio:', err);

      if (err.name === 'NotAllowedError') {
        throw new Error('Microphone permission denied. Please allow microphone access.');
      } else if (err.name === 'NotFoundError') {
        throw new Error('No microphone found. Please connect a microphone.');
      } else {
        throw new Error(`Failed to initialize audio: ${err.message}`);
      }
    }
  }

  /**
   * Start recording audio using AudioWorklet
   */
  async startRecording(): Promise<void> {
    if (this.isRecording) {
      console.warn('Already recording');
      return;
    }

    if (!this.audioStream || !this.audioContext) {
      await this.initialize();
    }

    if (!this.audioStream || !this.audioContext) {
      throw new Error('Audio not initialized');
    }

    try {
      // Resume AudioContext if suspended (critical for Android Chrome and mobile browsers).
      // AudioContexts created outside user gestures start suspended on mobile.
      // This resume call happens inside a user gesture handler (button press),
      // so the browser will allow it.
      if (this.audioContext.state === 'suspended') {
        console.log('AudioContext is suspended, resuming for mobile...');
        await this.audioContext.resume();
        console.log('AudioContext resumed, state:', this.audioContext.state);
      }

      // Create source node from microphone stream
      this.sourceNode = this.audioContext.createMediaStreamSource(this.audioStream);

      // Create AudioWorklet node
      this.audioWorkletNode = new AudioWorkletNode(
        this.audioContext,
        'pcm-processor'
      );

      // Handle PCM data from AudioWorklet
      this.audioWorkletNode.port.onmessage = (event) => {
        if (event.data.type === 'audio') {
          const pcmData = event.data.data as ArrayBuffer;
          console.log(`PCM chunk received: ${pcmData.byteLength} bytes`);

          if (this.onChunkCallback) {
            this.onChunkCallback(pcmData);
          }
        }
      };

      // Handle errors
      this.audioWorkletNode.port.onmessageerror = (event) => {
        const error = new Error(`AudioWorklet error: ${event}`);
        console.error(error);
        if (this.onErrorCallback) {
          this.onErrorCallback(error);
        }
      };

      // Connect: microphone -> AudioWorklet -> silent GainNode -> destination
      // On mobile browsers, the audio processing graph may be suspended or
      // garbage-collected if there's no path to the destination. Connecting
      // through a zero-gain node keeps the graph alive without producing output.
      this.sourceNode.connect(this.audioWorkletNode);
      this.silentGainNode = this.audioContext.createGain();
      this.silentGainNode.gain.value = 0;
      this.audioWorkletNode.connect(this.silentGainNode);
      this.silentGainNode.connect(this.audioContext.destination);

      this.isRecording = true;
      console.log('Recording started (PCM mode), actualSampleRate:', this.audioContext.sampleRate);

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
    if (!this.isRecording) {
      console.warn('Not currently recording');
      return;
    }

    try {
      // Disconnect audio nodes
      if (this.sourceNode && this.audioWorkletNode) {
        this.sourceNode.disconnect(this.audioWorkletNode);
      }
      if (this.audioWorkletNode && this.silentGainNode) {
        this.audioWorkletNode.disconnect(this.silentGainNode);
      }
      if (this.silentGainNode) {
        this.silentGainNode.disconnect();
      }

      // Cleanup
      this.audioWorkletNode = null;
      this.sourceNode = null;
      this.silentGainNode = null;
      this.isRecording = false;

      console.log('Recording stopped');
    } catch (error) {
      const err = error as Error;
      console.error('Error stopping recording:', err);
      this.isRecording = false;
    }
  }

  /**
   * Release microphone resources
   */
  destroy(): void {
    // Disconnect audio nodes
    if (this.sourceNode && this.audioWorkletNode) {
      this.sourceNode.disconnect(this.audioWorkletNode);
    }
    if (this.audioWorkletNode && this.silentGainNode) {
      this.audioWorkletNode.disconnect(this.silentGainNode);
    }
    if (this.silentGainNode) {
      this.silentGainNode.disconnect();
    }

    // Stop microphone stream
    if (this.audioStream) {
      this.audioStream.getTracks().forEach((track) => track.stop());
      this.audioStream = null;
    }

    // Close AudioContext
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
    }

    // Cleanup
    this.audioContext = null;
    this.audioWorkletNode = null;
    this.sourceNode = null;
    this.silentGainNode = null;
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

  /**
   * Get the actual sample rate used by the AudioContext.
   * On Android Chrome, this may differ from the requested rate.
   */
  get actualSampleRate(): number {
    return this.audioContext?.sampleRate ?? this.options.sampleRate;
  }
}
