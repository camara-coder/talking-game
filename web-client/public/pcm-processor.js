/**
 * AudioWorklet Processor for Raw PCM Audio Capture
 * Captures audio samples and converts Float32 to PCM16 format
 * This file runs in the AudioWorklet thread (separate from main thread)
 */

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.sampleBuffer = [];
    this.bufferSize = 4096; // Send chunks of 4096 samples (~256ms at 16kHz)
  }

  /**
   * Process audio samples
   * @param {Float32Array[][]} inputs - Input audio data
   * @param {Float32Array[][]} outputs - Output audio data (unused)
   * @param {Object} parameters - Parameters (unused)
   * @returns {boolean} - True to keep processor alive
   */
  process(inputs, outputs, parameters) {
    const input = inputs[0];

    // If no input, keep processor alive
    if (!input || !input.length) {
      return true;
    }

    // Get first channel (mono)
    const inputChannel = input[0];

    // Convert Float32 samples to PCM16 and accumulate
    for (let i = 0; i < inputChannel.length; i++) {
      // Clamp to [-1.0, 1.0] and convert to 16-bit signed integer
      const sample = Math.max(-1, Math.min(1, inputChannel[i]));
      const pcm16Sample = Math.floor(sample * 32767);
      this.sampleBuffer.push(pcm16Sample);
    }

    // Send buffer when it reaches target size
    if (this.sampleBuffer.length >= this.bufferSize) {
      // Convert to Int16Array (2 bytes per sample)
      const pcmData = new Int16Array(this.sampleBuffer);

      // Send to main thread
      this.port.postMessage({
        type: 'audio',
        data: pcmData.buffer, // Transfer ArrayBuffer
      }, [pcmData.buffer]); // Transfer ownership for performance

      // Clear buffer
      this.sampleBuffer = [];
    }

    return true; // Keep processor alive
  }
}

// Register the processor
registerProcessor('pcm-processor', PCMProcessor);
