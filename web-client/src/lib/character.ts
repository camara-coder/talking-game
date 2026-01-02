import * as PIXI from 'pixi.js';
import type { GameState } from '../types';

export class Character {
  private app: PIXI.Application | null = null;
  private container: PIXI.Container | null = null;
  private body: PIXI.Graphics | null = null;
  private eyes: PIXI.Graphics | null = null;
  private mouth: PIXI.Graphics | null = null;
  private currentState: GameState = 'idle';
  private animationFrame = 0;
  private isInitialized = false;

  constructor(canvas: HTMLCanvasElement, width: number, height: number) {
    // Initialize PixiJS application
    this.app = new PIXI.Application();

    // Setup is now async in PixiJS v8
    this.app.init({
      canvas,
      width,
      height,
      backgroundColor: 0x87ceeb, // Sky blue background
      antialias: true,
    }).then(() => {
      if (this.app) {
        this.setup();
      }
    }).catch((error) => {
      console.error('Failed to initialize PixiJS:', error);
    });
  }

  private setup(): void {
    if (!this.app) return;

    // Create graphics objects
    this.container = new PIXI.Container();
    this.body = new PIXI.Graphics();
    this.eyes = new PIXI.Graphics();
    this.mouth = new PIXI.Graphics();

    // Add container to stage
    this.app.stage.addChild(this.container);

    // Position container in center
    this.container.x = this.app.screen.width / 2;
    this.container.y = this.app.screen.height / 2;

    // Add parts to container
    this.container.addChild(this.body);
    this.container.addChild(this.eyes);
    this.container.addChild(this.mouth);

    // Draw initial character
    this.drawCharacter();

    // Start animation loop
    this.app.ticker.add(() => this.animate());

    this.isInitialized = true;
  }

  private drawCharacter(): void {
    if (!this.body || !this.eyes || !this.mouth) return;

    // Draw body (simple circle for POC) - PixiJS v8 API
    this.body.clear();
    this.body.circle(0, 0, 80);
    this.body.fill(0xffcc00); // Yellow

    // Draw eyes
    this.drawEyes();

    // Draw mouth based on state
    this.drawMouth();
  }

  private drawEyes(): void {
    if (!this.eyes) return;

    this.eyes.clear();

    const eyeSize = this.currentState === 'listening' ? 8 : 6;
    const eyeY = this.currentState === 'listening' ? -25 : -20;

    // Left eye - PixiJS v8 API
    this.eyes.circle(-25, eyeY, eyeSize);
    this.eyes.fill(0x000000); // Black

    // Right eye - PixiJS v8 API
    this.eyes.circle(25, eyeY, eyeSize);
    this.eyes.fill(0x000000); // Black
  }

  private drawMouth(): void {
    if (!this.mouth) return;

    this.mouth.clear();

    switch (this.currentState) {
      case 'idle':
        // Slight smile - PixiJS v8 API
        this.mouth.setStrokeStyle({ width: 3, color: 0x000000 });
        this.mouth.arc(0, 10, 30, 0.2, Math.PI - 0.2);
        this.mouth.stroke();
        break;

      case 'listening':
        // Open circle (attentive) - PixiJS v8 API
        this.mouth.circle(0, 20, 10);
        this.mouth.fill(0x000000);
        break;

      case 'processing':
        // Thoughtful expression (horizontal line) - PixiJS v8 API
        this.mouth.setStrokeStyle({ width: 3, color: 0x000000 });
        this.mouth.moveTo(-20, 20);
        this.mouth.lineTo(20, 20);
        this.mouth.stroke();
        break;

      case 'speaking':
        // Animated mouth (open/close) - PixiJS v8 API
        const mouthOpen = Math.sin(this.animationFrame * 0.3) > 0;
        if (mouthOpen) {
          this.mouth.ellipse(0, 25, 20, 15);
          this.mouth.fill(0x000000);
        } else {
          this.mouth.setStrokeStyle({ width: 3, color: 0x000000 });
          this.mouth.arc(0, 20, 20, 0.3, Math.PI - 0.3);
          this.mouth.stroke();
        }
        break;
    }
  }

  private animate(): void {
    if (!this.container || !this.app) return;

    this.animationFrame++;

    // Breathing animation (gentle scale pulse)
    if (this.currentState === 'idle') {
      const scale = 1 + Math.sin(this.animationFrame * 0.05) * 0.02;
      this.container.scale.set(scale);
    } else {
      this.container.scale.set(1);
    }

    // Redraw mouth for speaking animation
    if (this.currentState === 'speaking') {
      this.drawMouth();
    }

    // Bounce animation for listening
    if (this.currentState === 'listening') {
      this.container.y = this.app.screen.height / 2 + Math.sin(this.animationFrame * 0.1) * 5;
    } else {
      this.container.y = this.app.screen.height / 2;
    }
  }

  setState(state: GameState): void {
    if (this.currentState !== state) {
      this.currentState = state;
      this.drawCharacter();
    }
  }

  destroy(): void {
    if (this.app) {
      try {
        this.app.destroy(true, { children: true });
      } catch (error) {
        console.error('Error destroying PixiJS app:', error);
      }
      this.app = null;
    }
    this.container = null;
    this.body = null;
    this.eyes = null;
    this.mouth = null;
    this.isInitialized = false;
  }
}
