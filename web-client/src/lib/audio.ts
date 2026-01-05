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

  async playAudio(audioData: ArrayBuffer): Promise<void> {
    console.log('🔊 AudioPlayer.playAudio called');
    console.log('  Audio data size:', audioData.byteLength, 'bytes');

    // Ensure we have a valid AudioContext
    this.ensureAudioContext();

    if (!this.audioContext) {
      throw new Error('Failed to create AudioContext');
    }

    console.log('  AudioContext state:', this.audioContext.state);

    // Stop any currently playing audio
    this.stop();

    try {
      // Decode audio data
      console.log('  Decoding audio data...');
      const audioBuffer = await this.audioContext.decodeAudioData(audioData);
      console.log('  Audio decoded successfully');
      console.log('  Duration:', audioBuffer.duration.toFixed(2), 'seconds');
      console.log('  Sample rate:', audioBuffer.sampleRate, 'Hz');
      console.log('  Channels:', audioBuffer.numberOfChannels);

      // Create source node
      console.log('  Creating audio source...');
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext.destination);

      // Setup completion callback
      this.currentSource.onended = () => {
        console.log('  Audio playback ended');
        this.currentSource = null;
        if (this.onPlaybackCompleteCallback) {
          this.onPlaybackCompleteCallback();
        }
      };

      // Resume audio context if suspended (browser autoplay policy)
      if (this.audioContext.state === 'suspended') {
        console.log('  AudioContext is suspended, resuming...');
        await this.audioContext.resume();
        console.log('  AudioContext resumed, state:', this.audioContext.state);
      }

      // Play audio
      console.log('  Starting audio playback...');
      this.currentSource.start(0);
      console.log('✅ Audio playback started successfully!');
    } catch (error) {
      console.error('❌ Failed to play audio:', error);
      console.error('  Error details:', {
        name: (error as Error).name,
        message: (error as Error).message,
        stack: (error as Error).stack
      });
      throw error;
    }
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
