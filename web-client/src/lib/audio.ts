export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;
  private onPlaybackCompleteCallback?: () => void;

  constructor() {
    // Don't create AudioContext here - will be created on first user interaction
    // This is important for mobile browsers
  }

  private ensureAudioContext(): void {
    // Create AudioContext if it doesn't exist
    if (!this.audioContext || this.audioContext.state === 'closed') {
      console.log('  Creating AudioContext...');
      this.audioContext = new AudioContext();
      console.log('  AudioContext created, state:', this.audioContext.state);
    }
  }

  /**
   * Unlock audio on mobile browsers
   * Call this in response to user interaction (e.g., button press)
   */
  async unlock(): Promise<void> {
    this.ensureAudioContext();

    if (this.audioContext && this.audioContext.state === 'suspended') {
      console.log('🔓 Unlocking AudioContext for mobile...');
      await this.audioContext.resume();
      console.log('✅ AudioContext unlocked, state:', this.audioContext.state);
    }
  }

  /**
   * Decode and play audio, returning a Promise that resolves when playback
   * ENDS (not just when it starts).  This makes it safe to await and chain
   * multiple segments back-to-back without overlapping.
   */
  async playAudio(audioData: ArrayBuffer): Promise<void> {
    this.ensureAudioContext();
    if (!this.audioContext) throw new Error('Failed to create AudioContext');

    // Stop whatever is currently playing
    this.stop();

    const audioBuffer = await this.audioContext.decodeAudioData(audioData);

    this.currentSource = this.audioContext.createBufferSource();
    this.currentSource.buffer = audioBuffer;
    this.currentSource.connect(this.audioContext.destination);

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    return new Promise<void>((resolve) => {
      this.currentSource!.onended = () => {
        this.currentSource = null;
        if (this.onPlaybackCompleteCallback) {
          this.onPlaybackCompleteCallback();
        }
        resolve();
      };
      this.currentSource!.start(0);
    });
  }

  stop(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (error) {
        // Ignore if already stopped
      }
      this.currentSource = null;
    }
  }

  get isPlaying(): boolean {
    return this.currentSource !== null;
  }

  onPlaybackComplete(callback: () => void): void {
    this.onPlaybackCompleteCallback = callback;
  }

  destroy(): void {
    this.stop();
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch((error) => {
        console.error('Error closing audio context:', error);
      });
    }
  }
}
