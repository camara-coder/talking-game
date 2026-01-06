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

  // Prevent context menu and text selection on mobile
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (!disabled && !isProcessing) {
      e.preventDefault(); // Prevent text selection on mobile
      onPress();
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!disabled && !isProcessing) {
      e.preventDefault();
      onRelease();
    }
  };

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
        // Prevent text selection on mobile
        WebkitUserSelect: 'none',
        userSelect: 'none',
        WebkitTouchCallout: 'none',
        // Prevent tap highlight on mobile
        WebkitTapHighlightColor: 'transparent',
      }}
      onMouseDown={!disabled && !isProcessing ? onPress : undefined}
      onMouseUp={!disabled && !isProcessing ? onRelease : undefined}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onContextMenu={handleContextMenu}
      disabled={disabled || isProcessing}
    >
      <span className="button-icon">{isListening ? '🎤' : '🗣️'}</span>
      <span className="button-text">{getButtonText()}</span>
    </button>
  );
};
