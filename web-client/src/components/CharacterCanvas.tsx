import React, { useEffect, useRef } from 'react';
import { Character } from '../lib/character';
import type { GameState } from '../types';

interface CharacterCanvasProps {
  gameState: GameState;
  width?: number;
  height?: number;
}

export const CharacterCanvas: React.FC<CharacterCanvasProps> = ({
  gameState,
  width = 600,
  height = 400,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const characterRef = useRef<Character | null>(null);

  // Initialize character
  useEffect(() => {
    if (canvasRef.current && !characterRef.current) {
      characterRef.current = new Character(canvasRef.current, width, height);
    }

    return () => {
      if (characterRef.current) {
        characterRef.current.destroy();
        characterRef.current = null;
      }
    };
  }, [width, height]);

  // Update character state
  useEffect(() => {
    if (characterRef.current) {
      characterRef.current.setState(gameState);
    }
  }, [gameState]);

  return <canvas ref={canvasRef} className="character-canvas" />;
};
