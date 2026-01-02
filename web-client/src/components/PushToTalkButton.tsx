import React from 'react';
import type { GameState } from '../types';

interface PushToTalkButtonProps {
  gameState: GameState;
  onPress: () => void;
  onRelease: () => void;
  disabled?: boolean;
}

export const PushToTalkButton: React.FC<PushToTalkButtonProps> = ({
  gameState,
  onPress,
  onRelease,
  disabled = false,
}) => {
  const isListening = gameState === 'listening';
  const isProcessing = gameState === 'processing' || gameState === 'speaking';

  const getButtonText = () => {
    switch (gameState) {
      case 'listening':
        return 'Release to Send';
      case 'processing':
        return 'Processing...';
      case 'speaking':
        return 'Speaking...';
      default:
        return 'Hold to Talk';
    }
  };

  const getButtonColor = () => {
    switch (gameState) {
      case 'listening':
        return '#ff4444';
      case 'processing':
        return '#ffaa00';
      case 'speaking':
        return '#4444ff';
      default:
        return '#44ff44';
    }
  };

  return (
    <button
      className="push-to-talk-button"
      style={{
        backgroundColor: getButtonColor(),
        transform: isListening ? 'scale(1.1)' : 'scale(1)',
        cursor: disabled || isProcessing ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
      onMouseDown={!disabled && !isProcessing ? onPress : undefined}
      onMouseUp={!disabled && !isProcessing ? onRelease : undefined}
      onTouchStart={!disabled && !isProcessing ? onPress : undefined}
      onTouchEnd={!disabled && !isProcessing ? onRelease : undefined}
      disabled={disabled || isProcessing}
    >
      <span className="button-icon">{isListening ? '🎤' : '🗣️'}</span>
      <span className="button-text">{getButtonText()}</span>
    </button>
  );
};
