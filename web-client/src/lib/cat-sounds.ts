/**
 * Cat Sound Manager
 * Synthesizes cat sounds using the Web Audio API — no audio files needed.
 * Sounds are generated procedurally to approximate meows, purring, and yawns.
 */

export type CatSoundName =
  | 'meow_short'
  | 'meow_long'
  | 'meow_happy'
  | 'meow_bored'
  | 'meow_curious'
  | 'meow_sleepy'
  | 'purr'
  | 'yawn';

export class CatSoundManager {
  private audioCtx: AudioContext | null = null;

  /** Must be called from a user gesture to unlock Web Audio on mobile */
  unlock(): void {
    if (!this.audioCtx) {
      this.audioCtx = new AudioContext();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  play(name: CatSoundName): void {
    if (!this.audioCtx) {
      this.audioCtx = new AudioContext();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }

    switch (name) {
      case 'meow_short':   return this._meow(0.3, 600, 400, 0.35);
      case 'meow_long':    return this._meow(0.6, 500, 350, 0.4);
      case 'meow_happy':   return this._meowChirp();
      case 'meow_bored':   return this._meow(0.8, 450, 300, 0.25);
      case 'meow_curious': return this._meowRising();
      case 'meow_sleepy':  return this._meow(0.9, 380, 320, 0.2);
      case 'purr':         return this._purr(2.5);
      case 'yawn':         return this._yawn();
    }
  }

  playRandom(mood: string): void {
    const sounds: Record<string, CatSoundName[]> = {
      happy:   ['meow_short', 'meow_happy', 'purr', 'meow_short'],
      bored:   ['meow_long',  'yawn',       'meow_bored'],
      curious: ['meow_curious','meow_short', 'meow_curious'],
      sleepy:  ['purr',       'yawn',       'meow_sleepy', 'purr'],
    };
    const list = sounds[mood] ?? sounds.happy;
    this.play(list[Math.floor(Math.random() * list.length)]);
  }

  // ─────────────────────────────────────────────
  // Sound synthesizers
  // ─────────────────────────────────────────────

  private _ctx(): AudioContext {
    return this.audioCtx!;
  }

  /** Generic meow — frequency sweeps from startHz down to endHz over duration */
  private _meow(duration: number, startHz: number, endHz: number, volume: number): void {
    const ctx = this._ctx();
    const t = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    // Slight vibrato
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();

    lfo.frequency.value = 5.5;
    lfoGain.gain.value = 18;
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(startHz, t);
    osc.frequency.exponentialRampToValueAtTime(endHz, t + duration * 0.7);
    osc.frequency.setValueAtTime(endHz, t + duration * 0.7);

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(volume, t + 0.06);
    gain.gain.setValueAtTime(volume, t + duration * 0.6);
    gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

    osc.connect(gain);
    gain.connect(ctx.destination);

    lfo.start(t);
    osc.start(t);
    lfo.stop(t + duration + 0.1);
    osc.stop(t + duration + 0.1);
  }

  /** Happy chirp — quick ascending squeak */
  private _meowChirp(): void {
    const ctx = this._ctx();
    const t = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(500, t);
    osc.frequency.exponentialRampToValueAtTime(900, t + 0.12);
    osc.frequency.exponentialRampToValueAtTime(650, t + 0.22);

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.35, t + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.22);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.3);
  }

  /** Curious meow — rising inflection at the end */
  private _meowRising(): void {
    const ctx = this._ctx();
    const t = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(480, t);
    osc.frequency.linearRampToValueAtTime(420, t + 0.25);
    osc.frequency.exponentialRampToValueAtTime(680, t + 0.5);

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.35, t + 0.07);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.55);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.6);
  }

  /** Purring — low frequency rumble with AM modulation */
  private _purr(duration: number): void {
    const ctx = this._ctx();
    const t = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const amOsc = ctx.createOscillator();
    const amGain = ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.value = 110;

    // AM at ~25Hz — the purr rate
    amOsc.frequency.value = 25;
    amGain.gain.value = 0.08;
    amOsc.connect(amGain);
    amGain.connect(gain.gain);

    gain.gain.setValueAtTime(0.12, t);
    gain.gain.linearRampToValueAtTime(0.15, t + 0.4);
    gain.gain.setValueAtTime(0.15, t + duration - 0.4);
    gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

    osc.connect(gain);
    gain.connect(ctx.destination);

    amOsc.start(t);
    osc.start(t);
    amOsc.stop(t + duration);
    osc.stop(t + duration);
  }

  /** Yawn — slow sweep up then down with filter */
  private _yawn(): void {
    const ctx = this._ctx();
    const t = ctx.currentTime;
    const dur = 1.4;

    const osc = ctx.createOscillator();
    const filter = ctx.createBiquadFilter();
    const gain = ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(200, t);
    osc.frequency.linearRampToValueAtTime(450, t + dur * 0.45);
    osc.frequency.linearRampToValueAtTime(180, t + dur);

    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(600, t);
    filter.frequency.linearRampToValueAtTime(1200, t + dur * 0.45);
    filter.frequency.linearRampToValueAtTime(500, t + dur);
    filter.Q.value = 1.2;

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.3, t + 0.15);
    gain.gain.setValueAtTime(0.3, t + dur * 0.7);
    gain.gain.exponentialRampToValueAtTime(0.001, t + dur);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    osc.start(t);
    osc.stop(t + dur + 0.1);
  }

  destroy(): void {
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }
  }
}
