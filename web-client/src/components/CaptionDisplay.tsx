import React from 'react';

interface CaptionDisplayProps {
  transcript: string;
  replyText: string;
}

export const CaptionDisplay: React.FC<CaptionDisplayProps> = ({
  transcript,
  replyText,
}) => {
  return (
    <div className="caption-display">
      {transcript && (
        <div className="transcript-box">
          <div className="caption-label">You said:</div>
          <div className="caption-text">{transcript}</div>
        </div>
      )}
      {replyText && (
        <div className="reply-box">
          <div className="caption-label">Character says:</div>
          <div className="caption-text">{replyText}</div>
        </div>
      )}
    </div>
  );
};
