/**
 * Tests for PushToTalkButton component
 */
import React from 'react';
import { render, screen, userEvent } from '../../test/utils';
import { PushToTalkButton } from '../PushToTalkButton';
import { GameState } from '../../types';

describe('PushToTalkButton', () => {
  const mockOnPress = jest.fn();
  const mockOnRelease = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders button with correct text when idle', () => {
      render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(screen.getByText('Hold to Talk')).toBeInTheDocument();
    });

    it('renders button with correct text when listening', () => {
      render(
        <PushToTalkButton
          gameState="listening"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(screen.getByText('Release to Send')).toBeInTheDocument();
    });

    it('renders button with correct text when thinking', () => {
      render(
        <PushToTalkButton
          gameState="thinking"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });

    it('renders button with correct text when speaking', () => {
      render(
        <PushToTalkButton
          gameState="speaking"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(screen.getByText('Speaking...')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('applies idle style', () => {
      const { container } = render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = container.querySelector('button');
      expect(button).toHaveStyle({ backgroundColor: '#44ff44' });
    });

    it('applies listening style', () => {
      const { container } = render(
        <PushToTalkButton
          gameState="listening"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = container.querySelector('button');
      expect(button).toHaveStyle({ backgroundColor: '#ff4444' });
    });
  });

  describe('Interaction', () => {
    it('calls onPress when mouse down', async () => {
      const user = userEvent.setup();

      render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = screen.getByRole('button');
      await user.pointer({ keys: '[MouseLeft>]', target: button });

      expect(mockOnPress).toHaveBeenCalledTimes(1);
    });

    it('calls onRelease when button is released', async () => {
      const user = userEvent.setup();

      render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = screen.getByRole('button');

      // Mouse down (press)
      await user.pointer({ keys: '[MouseLeft>]', target: button });
      expect(mockOnPress).toHaveBeenCalled();

      // Mouse up (release)
      await user.pointer({ keys: '[/MouseLeft]' });
      expect(mockOnRelease).toHaveBeenCalled();
    });

    it('is disabled when thinking', () => {
      render(
        <PushToTalkButton
          gameState="thinking"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('is disabled when speaking', () => {
      render(
        <PushToTalkButton
          gameState="speaking"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('is enabled when idle', () => {
      render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
    });
  });

  describe('State transitions', () => {
    it('updates text when state changes', () => {
      const { rerender } = render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(screen.getByText('Hold to Talk')).toBeInTheDocument();

      rerender(
        <PushToTalkButton
          gameState="listening"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(screen.getByText('Release to Send')).toBeInTheDocument();
    });

    it('updates disabled state when state changes', () => {
      const { rerender } = render(
        <PushToTalkButton
          gameState="idle"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();

      rerender(
        <PushToTalkButton
          gameState="thinking"
          onPress={mockOnPress}
          onRelease={mockOnRelease}
        />
      );

      expect(button).toBeDisabled();
    });
  });
});
