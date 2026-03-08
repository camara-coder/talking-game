/**
 * CatCharacter — Whiskers the talking cat, drawn with PixiJS v8 Graphics API.
 *
 * States: idle | listening | processing | speaking | silly | sleeping
 * Mood affects color palette and animation energy.
 */
import * as PIXI from 'pixi.js';
import type { GameState, CatMood } from '../types';

// Colour palettes per mood
const PALETTES: Record<CatMood, { body: number; belly: number; inner_ear: number; nose: number }> = {
  happy:   { body: 0xF4A261, belly: 0xFFE8CC, inner_ear: 0xFF8FAB, nose: 0xFF6B8A },
  bored:   { body: 0x8B9DB0, belly: 0xCDD5DF, inner_ear: 0xA9B9C8, nose: 0x7A8FA0 },
  curious: { body: 0x6BB5FF, belly: 0xD6ECFF, inner_ear: 0x99CCFF, nose: 0x4488DD },
  sleepy:  { body: 0x9B8EA8, belly: 0xE0D8E8, inner_ear: 0xC9B8D8, nose: 0x7B6A8A },
};

export class CatCharacter {
  private app: PIXI.Application | null = null;
  private root: PIXI.Container | null = null;
  private body: PIXI.Graphics | null = null;
  private belly: PIXI.Graphics | null = null;
  private earL: PIXI.Graphics | null = null;
  private earR: PIXI.Graphics | null = null;
  private eyeL: PIXI.Graphics | null = null;
  private eyeR: PIXI.Graphics | null = null;
  private nose: PIXI.Graphics | null = null;
  private mouth: PIXI.Graphics | null = null;
  private tail: PIXI.Graphics | null = null;
  private whiskerGroup: PIXI.Graphics | null = null;
  private zzzText: PIXI.Text | null = null;
  private starBurst: PIXI.Container | null = null;

  private frame = 0;
  private currentState: GameState = 'idle';
  private currentMood: CatMood = 'happy';
  private isInitialized = false;

  constructor(canvas: HTMLCanvasElement, width: number, height: number) {
    this.app = new PIXI.Application();
    this.app.init({
      canvas,
      width,
      height,
      backgroundColor: 0x1a1a2e,
      antialias: true,
    }).then(() => {
      if (this.app) this._setup();
    }).catch(console.error);
  }

  // ──────────────────────────────────────────────
  // Setup
  // ──────────────────────────────────────────────

  private _setup(): void {
    if (!this.app) return;
    const W = this.app.screen.width;
    const H = this.app.screen.height;

    // Gradient background
    const bg = new PIXI.Graphics();
    bg.rect(0, 0, W, H);
    bg.fill(0x1a1a2e);
    this.app.stage.addChild(bg);

    // Stars
    this._addStars(bg, W, H);

    this.root = new PIXI.Container();
    this.root.x = W / 2;
    this.root.y = H / 2 + 20;
    this.app.stage.addChild(this.root);

    this.tail        = new PIXI.Graphics();
    this.body        = new PIXI.Graphics();
    this.belly       = new PIXI.Graphics();
    this.earL        = new PIXI.Graphics();
    this.earR        = new PIXI.Graphics();
    this.whiskerGroup = new PIXI.Graphics();
    this.eyeL        = new PIXI.Graphics();
    this.eyeR        = new PIXI.Graphics();
    this.nose        = new PIXI.Graphics();
    this.mouth       = new PIXI.Graphics();

    // ZZZ for sleeping
    this.zzzText = new PIXI.Text({ text: '', style: { fontSize: 22, fill: 0xffffff, fontFamily: 'Arial' } });
    this.zzzText.alpha = 0;
    this.zzzText.x = 55;
    this.zzzText.y = -80;

    // Star burst container for silly mode
    this.starBurst = new PIXI.Container();

    this.root.addChild(this.tail);
    this.root.addChild(this.earL);
    this.root.addChild(this.earR);
    this.root.addChild(this.body);
    this.root.addChild(this.belly);
    this.root.addChild(this.whiskerGroup);
    this.root.addChild(this.eyeL);
    this.root.addChild(this.eyeR);
    this.root.addChild(this.nose);
    this.root.addChild(this.mouth);
    this.root.addChild(this.zzzText!);
    this.root.addChild(this.starBurst);

    this._drawAll();

    this.app.ticker.add(() => this._animate());
    this.isInitialized = true;
  }

  private _addStars(g: PIXI.Graphics, W: number, H: number): void {
    for (let i = 0; i < 80; i++) {
      const x = Math.random() * W;
      const y = Math.random() * H;
      const r = Math.random() * 1.5 + 0.5;
      g.circle(x, y, r);
      const bright = Math.floor(155 + Math.random() * 100);
      g.fill(bright * 0x10000 + bright * 0x100 + bright);
    }
  }

  // ──────────────────────────────────────────────
  // Drawing
  // ──────────────────────────────────────────────

  private _palette() {
    return PALETTES[this.currentMood];
  }

  private _drawAll(): void {
    this._drawTail();
    this._drawEars();
    this._drawBody();
    this._drawWhiskers();
    this._drawEyes();
    this._drawNose();
    this._drawMouth();
  }

  private _drawTail(): void {
    if (!this.tail) return;
    const p = this._palette();
    this.tail.clear();
    // Curved tail sweeping to the right
    const tailAngle = Math.sin(this.frame * 0.04) * 0.4;
    this.tail.setStrokeStyle({ width: 12, color: p.body, cap: 'round' });
    this.tail.moveTo(30, 30);
    this.tail.bezierCurveTo(
      90 + Math.sin(tailAngle) * 20, 60,
      90, 120 + Math.cos(tailAngle) * 15,
      60 + Math.sin(tailAngle * 1.5) * 25, 130
    );
    this.tail.stroke();
  }

  private _drawEars(): void {
    if (!this.earL || !this.earR) return;
    const p = this._palette();

    this.earL.clear();
    this.earR.clear();

    const earTilt = this.currentState === 'listening' ? -0.2 : 0;

    // Left ear
    this.earL.poly([-55, -55, -80, -95, -35, -65]);
    this.earL.fill(p.body);
    this.earL.poly([-57, -59, -75, -90, -40, -67]);
    this.earL.fill(p.inner_ear);
    this.earL.rotation = earTilt;

    // Right ear
    this.earR.poly([55, -55, 80, -95, 35, -65]);
    this.earR.fill(p.body);
    this.earR.poly([57, -59, 75, -90, 40, -67]);
    this.earR.fill(p.inner_ear);
    this.earR.rotation = -earTilt;
  }

  private _drawBody(): void {
    if (!this.body || !this.belly) return;
    const p = this._palette();

    this.body.clear();
    this.belly.clear();

    // Head
    this.body.ellipse(0, 0, 75, 70);
    this.body.fill(p.body);

    // Body below
    this.body.ellipse(0, 80, 55, 65);
    this.body.fill(p.body);

    // Belly patch
    this.belly.ellipse(0, 80, 32, 45);
    this.belly.fill(p.belly);
  }

  private _drawWhiskers(): void {
    if (!this.whiskerGroup) return;
    this.whiskerGroup.clear();

    const wobble = Math.sin(this.frame * 0.06) * 2;

    this.whiskerGroup.setStrokeStyle({ width: 1.5, color: 0xffffff, alpha: 0.85 });

    // Left whiskers
    for (let i = 0; i < 3; i++) {
      const y = -8 + i * 8 + wobble * (i - 1) * 0.5;
      this.whiskerGroup.moveTo(-20, y);
      this.whiskerGroup.lineTo(-75, y + (i - 1) * 6);
    }
    // Right whiskers
    for (let i = 0; i < 3; i++) {
      const y = -8 + i * 8 + wobble * (i - 1) * 0.5;
      this.whiskerGroup.moveTo(20, y);
      this.whiskerGroup.lineTo(75, y + (i - 1) * 6);
    }
    this.whiskerGroup.stroke();
  }

  private _drawEyes(): void {
    if (!this.eyeL || !this.eyeR) return;
    const p = this._palette();
    const isSleepy = this.currentState === 'sleeping' || this.currentMood === 'sleepy';
    const isListening = this.currentState === 'listening';
    const isSilly = this.currentState === 'silly';

    this.eyeL.clear();
    this.eyeR.clear();

    const eyeY = -15;

    if (isSleepy) {
      // Half-closed sleepy eyes
      const blink = Math.abs(Math.sin(this.frame * 0.015));
      this.eyeL.ellipse(-27, eyeY, 11, 5 * blink + 2);
      this.eyeL.fill(0x2a2a2a);
      this.eyeR.ellipse(27, eyeY, 11, 5 * blink + 2);
      this.eyeR.fill(0x2a2a2a);
    } else if (isSilly) {
      // Spiral/swirl eyes for silly mode
      this._drawSwirlEye(this.eyeL, -27, eyeY);
      this._drawSwirlEye(this.eyeR, 27, eyeY);
    } else {
      // Normal eyes with pupil slit
      const eyeH = isListening ? 14 : 12;
      const eyeW = isListening ? 13 : 12;

      // Iris
      this.eyeL.ellipse(-27, eyeY, eyeW, eyeH);
      this.eyeL.fill(0x5ece7b);
      this.eyeR.ellipse(27, eyeY, eyeW, eyeH);
      this.eyeR.fill(0x5ece7b);

      // Pupil slit
      const pupilW = this.currentState === 'processing' ? 2 : 4;
      this.eyeL.ellipse(-27, eyeY, pupilW, eyeH - 1);
      this.eyeL.fill(0x111111);
      this.eyeR.ellipse(27, eyeY, pupilW, eyeH - 1);
      this.eyeR.fill(0x111111);

      // Highlight
      this.eyeL.circle(-24, eyeY - 4, 2.5);
      this.eyeL.fill(0xffffff);
      this.eyeR.circle(24, eyeY - 4, 2.5);
      this.eyeR.fill(0xffffff);
    }
  }

  private _drawSwirlEye(g: PIXI.Graphics, x: number, y: number): void {
    // X eyes for silly
    g.setStrokeStyle({ width: 2.5, color: 0xff4444 });
    g.moveTo(x - 7, y - 7); g.lineTo(x + 7, y + 7);
    g.moveTo(x + 7, y - 7); g.lineTo(x - 7, y + 7);
    g.stroke();
  }

  private _drawNose(): void {
    if (!this.nose) return;
    const p = this._palette();
    this.nose.clear();
    this.nose.poly([0, 2, -6, -4, 6, -4]);
    this.nose.fill(p.nose);
  }

  private _drawMouth(): void {
    if (!this.mouth) return;
    this.mouth.clear();

    const mouthY = 10;

    switch (this.currentState) {
      case 'speaking': {
        const open = Math.abs(Math.sin(this.frame * 0.35));
        if (open > 0.4) {
          this.mouth.ellipse(0, mouthY + 4, 12 * open, 10 * open);
          this.mouth.fill(0x2a0a0a);
        } else {
          this.mouth.setStrokeStyle({ width: 2, color: 0x333333 });
          this.mouth.arc(0, mouthY - 2, 14, 0.3, Math.PI - 0.3);
          this.mouth.stroke();
        }
        break;
      }
      case 'silly': {
        // Tongue out
        this.mouth.setStrokeStyle({ width: 2.5, color: 0x333333 });
        this.mouth.arc(0, mouthY - 3, 15, 0.2, Math.PI - 0.2);
        this.mouth.stroke();
        this.mouth.ellipse(0, mouthY + 13, 8, 11);
        this.mouth.fill(0xff6b9d);
        break;
      }
      case 'sleeping': {
        // Small z-z line
        this.mouth.setStrokeStyle({ width: 2, color: 0x888888 });
        this.mouth.moveTo(-8, mouthY);
        this.mouth.lineTo(8, mouthY);
        this.mouth.stroke();
        break;
      }
      case 'listening': {
        // Open oval (attentive)
        this.mouth.ellipse(0, mouthY + 4, 8, 7);
        this.mouth.fill(0x2a0a0a);
        break;
      }
      case 'processing': {
        // Thoughtful pursed lips
        this.mouth.setStrokeStyle({ width: 2.5, color: 0x555555 });
        this.mouth.moveTo(-10, mouthY);
        this.mouth.lineTo(10, mouthY);
        this.mouth.stroke();
        break;
      }
      default: {
        // Idle smile
        this.mouth.setStrokeStyle({ width: 2.5, color: 0x333333 });
        this.mouth.arc(0, mouthY - 4, 14, 0.25, Math.PI - 0.25);
        this.mouth.stroke();
        break;
      }
    }
  }

  // ──────────────────────────────────────────────
  // Animation loop
  // ──────────────────────────────────────────────

  private _animate(): void {
    if (!this.root || !this.app) return;
    this.frame++;

    const W = this.app.screen.width;
    const H = this.app.screen.height;
    const baseY = H / 2 + 20;

    switch (this.currentState) {
      case 'idle': {
        // Gentle breathing
        const breathe = 1 + Math.sin(this.frame * 0.025) * 0.018;
        this.root.scale.set(breathe);
        this.root.y = baseY + Math.sin(this.frame * 0.025) * 2;
        this._drawTail();
        // Occasional slow blink
        if (this.frame % 180 < 12) {
          this._drawEyes();
        }
        break;
      }
      case 'listening': {
        // Bounce with excitement
        this.root.y = baseY + Math.sin(this.frame * 0.15) * 6;
        this.root.scale.set(1.05);
        this._drawEars();
        this._drawWhiskers();
        break;
      }
      case 'processing': {
        // Head-tilt thinking
        this.root.rotation = Math.sin(this.frame * 0.05) * 0.08;
        this.root.y = baseY;
        this.root.scale.set(1.0);
        this._drawEyes();
        this._drawMouth();
        break;
      }
      case 'speaking': {
        // Animated mouth + slight bounce
        this.root.y = baseY + Math.sin(this.frame * 0.2) * 3;
        this.root.rotation = 0;
        this.root.scale.set(1.02);
        this._drawMouth();
        break;
      }
      case 'silly': {
        // Spin + bounce + stars
        this.root.rotation = Math.sin(this.frame * 0.25) * 0.35;
        const jump = Math.abs(Math.sin(this.frame * 0.18)) * 18;
        this.root.y = baseY - jump;
        this.root.scale.set(1 + Math.abs(Math.sin(this.frame * 0.18)) * 0.08);
        this._drawEyes();
        this._drawMouth();
        this._drawTail();
        this._animateStars();
        break;
      }
      case 'sleeping': {
        // Slow sway + ZZZ
        this.root.rotation = Math.sin(this.frame * 0.012) * 0.06;
        this.root.y = baseY + 6;
        this.root.scale.set(0.98);
        this._animateZzz();
        this._drawEyes();
        break;
      }
    }

    this._drawWhiskers();
  }

  private _animateZzz(): void {
    if (!this.zzzText) return;
    const cycle = (this.frame % 200) / 200;
    if (cycle < 0.5) {
      this.zzzText.text = cycle < 0.17 ? 'z' : cycle < 0.33 ? 'zz' : 'zzz';
      this.zzzText.alpha = Math.min(cycle * 4, 1);
      this.zzzText.y = -80 - cycle * 30;
    } else {
      this.zzzText.alpha = Math.max(0, 1 - (cycle - 0.5) * 4);
    }
  }

  private _animateStars(): void {
    if (!this.starBurst) return;
    if (this.frame % 8 === 0) {
      this.starBurst.removeChildren();
      for (let i = 0; i < 6; i++) {
        const star = new PIXI.Graphics();
        const angle = (i / 6) * Math.PI * 2 + this.frame * 0.1;
        const r = 90 + Math.sin(this.frame * 0.15) * 15;
        const sx = Math.cos(angle) * r;
        const sy = Math.sin(angle) * r;
        star.star(sx, sy, 4, 7, 3);
        star.fill(0xFFD700);
        this.starBurst.addChild(star);
      }
    }
  }

  // ──────────────────────────────────────────────
  // Public API
  // ──────────────────────────────────────────────

  setState(state: GameState): void {
    if (this.currentState === state) return;
    this.currentState = state;

    // Clean up state-specific effects
    if (state !== 'sleeping' && this.zzzText) this.zzzText.alpha = 0;
    if (state !== 'silly' && this.starBurst) this.starBurst.removeChildren();
    if (this.root) this.root.rotation = 0;

    this._drawAll();
  }

  setMood(mood: CatMood): void {
    if (this.currentMood === mood) return;
    this.currentMood = mood;
    this._drawAll();
  }

  destroy(): void {
    if (this.app) {
      try { this.app.destroy(true, { children: true }); } catch (_) {}
      this.app = null;
    }
    this.root = null;
    this.isInitialized = false;
  }
}
