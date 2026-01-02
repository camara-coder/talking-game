/**
 * Tests for CaptionDisplay component
 */
import React from 'react';
import { render, screen } from '../../test/utils';
import { CaptionDisplay } from '../CaptionDisplay';

describe('CaptionDisplay', () => {
  describe('Rendering', () => {
    it('renders transcript when provided', () => {
      render(<CaptionDisplay transcript="Hello world" replyText="" />);

      expect(screen.getByText('You said:')).toBeInTheDocument();
      expect(screen.getByText('Hello world')).toBeInTheDocument();
    });

    it('renders reply text when provided', () => {
      render(<CaptionDisplay transcript="" replyText="How can I help?" />);

      expect(screen.getByText('Character says:')).toBeInTheDocument();
      expect(screen.getByText('How can I help?')).toBeInTheDocument();
    });

    it('renders both transcript and reply', () => {
      render(
        <CaptionDisplay
          transcript="What is five plus five"
          replyText="Five plus five is ten"
        />
      );

      expect(screen.getByText('What is five plus five')).toBeInTheDocument();
      expect(screen.getByText('Five plus five is ten')).toBeInTheDocument();
    });

    it('renders nothing when both are empty', () => {
      const { container } = render(
        <CaptionDisplay transcript="" replyText="" />
      );

      // Should render the container but with no visible text
      expect(container.querySelector('.caption-display')).toBeInTheDocument();
      expect(screen.queryByText('You said:')).not.toBeInTheDocument();
      expect(screen.queryByText('Character says:')).not.toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('applies transcript style', () => {
      const { container } = render(<CaptionDisplay transcript="Test transcript" replyText="" />);

      const transcriptBox = container.querySelector('.transcript-box');
      expect(transcriptBox).toBeInTheDocument();
    });

    it('applies reply style', () => {
      const { container } = render(<CaptionDisplay transcript="" replyText="Test reply" />);

      const replyBox = container.querySelector('.reply-box');
      expect(replyBox).toBeInTheDocument();
    });
  });

  describe('Updates', () => {
    it('updates transcript when prop changes', () => {
      const { rerender } = render(
        <CaptionDisplay transcript="First" replyText="" />
      );

      expect(screen.getByText(/First/)).toBeInTheDocument();

      rerender(<CaptionDisplay transcript="Second" replyText="" />);

      expect(screen.queryByText(/First/)).not.toBeInTheDocument();
      expect(screen.getByText(/Second/)).toBeInTheDocument();
    });

    it('updates reply when prop changes', () => {
      const { rerender } = render(
        <CaptionDisplay transcript="" replyText="First reply" />
      );

      expect(screen.getByText(/First reply/)).toBeInTheDocument();

      rerender(<CaptionDisplay transcript="" replyText="Second reply" />);

      expect(screen.queryByText(/First reply/)).not.toBeInTheDocument();
      expect(screen.getByText(/Second reply/)).toBeInTheDocument();
    });

    it('clears transcript when set to empty', () => {
      const { rerender } = render(
        <CaptionDisplay transcript="Test" replyText="" />
      );

      expect(screen.getByText(/Test/)).toBeInTheDocument();

      rerender(<CaptionDisplay transcript="" replyText="" />);

      expect(screen.queryByText(/Test/)).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('renders semantic HTML structure', () => {
      const { container } = render(
        <CaptionDisplay transcript="Test" replyText="Reply" />
      );

      const captionDisplay = container.querySelector('.caption-display');
      expect(captionDisplay).toBeInTheDocument();
      expect(captionDisplay?.querySelector('.transcript-box')).toBeInTheDocument();
      expect(captionDisplay?.querySelector('.reply-box')).toBeInTheDocument();
    });
  });

  describe('Long text handling', () => {
    it('handles long transcript text', () => {
      const longText = 'A'.repeat(500);

      render(<CaptionDisplay transcript={longText} replyText="" />);

      expect(screen.getByText(new RegExp(longText))).toBeInTheDocument();
    });

    it('handles long reply text', () => {
      const longText = 'B'.repeat(500);

      render(<CaptionDisplay transcript="" replyText={longText} />);

      expect(screen.getByText(new RegExp(longText))).toBeInTheDocument();
    });
  });

  describe('Special characters', () => {
    it('renders special characters in transcript', () => {
      render(
        <CaptionDisplay
          transcript="What's 5 + 5? Is it <10>?"
          replyText=""
        />
      );

      expect(
        screen.getByText(/What's 5 \+ 5\? Is it <10>\?/)
      ).toBeInTheDocument();
    });

    it('renders special characters in reply', () => {
      render(
        <CaptionDisplay
          transcript=""
          replyText="It's 10! Math is fun :)"
        />
      );

      expect(
        screen.getByText(/It's 10! Math is fun :\)/)
      ).toBeInTheDocument();
    });
  });
});
