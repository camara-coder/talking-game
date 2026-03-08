import React from 'react';
import type { CatMood } from '../types';

interface MoodIndicatorProps {
  mood: CatMood;
  catName?: string;
}

const MOOD_CONFIG: Record<CatMood, { emoji: string; label: string; color: string }> = {
  happy:   { emoji: '😸', label: 'Happy',   color: '#F4A261' },
  bored:   { emoji: '😒', label: 'Bored',   color: '#8B9DB0' },
  curious: { emoji: '🔍', label: 'Curious', color: '#6BB5FF' },
  sleepy:  { emoji: '😴', label: 'Sleepy',  color: '#9B8EA8' },
};

export const MoodIndicator: React.FC<MoodIndicatorProps> = ({
  mood,
  catName = 'Whiskers',
}) => {
  const config = MOOD_CONFIG[mood] ?? MOOD_CONFIG.happy;

  return (
    <div
      className="mood-indicator"
      style={{ borderColor: config.color }}
      title={`${catName} is feeling ${config.label.toLowerCase()}`}
    >
      <span className="mood-emoji">{config.emoji}</span>
      <span className="mood-label" style={{ color: config.color }}>
        {config.label}
      </span>
    </div>
  );
};
