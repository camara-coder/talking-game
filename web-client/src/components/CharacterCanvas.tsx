import React, { useEffect, useRef } from 'react';
import { CatCharacter } from '../lib/cat-character';
import type { GameState, CatMood } from '../types';

interface CharacterCanvasProps {
  gameState: GameState;
  mood?: CatMood;
  width?: number;
  height?: number;
}

export const CharacterCanvas: React.FC<CharacterCanvasProps> = ({
  gameState,
  mood = 'happy',
  width = 600,
  height = 400,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const characterRef = useRef<CatCharacter | null>(null);

  useEffect(() => {
    if (canvasRef.current && !characterRef.current) {
      characterRef.current = new CatCharacter(canvasRef.current, width, height);
    }
    return () => {
      if (characterRef.current) {
        characterRef.current.destroy();
        characterRef.current = null;
      }
    };
  }, [width, height]);

  useEffect(() => {
    characterRef.current?.setState(gameState);
  }, [gameState]);

  useEffect(() => {
    characterRef.current?.setMood(mood);
  }, [mood]);

  return <canvas ref={canvasRef} className="character-canvas" />;
};
