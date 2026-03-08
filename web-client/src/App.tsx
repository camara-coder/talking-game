import { useVoiceService } from './hooks/useVoiceService';
import { CharacterCanvas } from './components/CharacterCanvas';
import { PushToTalkButton } from './components/PushToTalkButton';
import { CaptionDisplay } from './components/CaptionDisplay';
import { MoodIndicator } from './components/MoodIndicator';
import './App.css';

const CAT_NAME = 'Whiskers';

function App() {
  const {
    gameState,
    catMood,
    transcript,
    replyText,
    error,
    isConnected,
    startListening,
    stopListening,
  } = useVoiceService();

  const getStateHint = () => {
    switch (gameState) {
      case 'listening':   return `${CAT_NAME} is listening...`;
      case 'processing':  return `${CAT_NAME} is thinking...`;
      case 'speaking':    return `${CAT_NAME} is talking!`;
      case 'silly':       return `${CAT_NAME} is being silly!!`;
      case 'sleeping':    return `${CAT_NAME} is napping... zzzz`;
      default:            return `Say hello to ${CAT_NAME}!`;
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="cat-title">
          <span className="cat-icon">🐱</span>
          <h1>{CAT_NAME}</h1>
          <span className="cat-subtitle">the Talking Cat</span>
        </div>
        <div className="header-right">
          <MoodIndicator mood={catMood} catName={CAT_NAME} />
          <div className="status-indicator">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
            <span className="status-text">{isConnected ? 'Online' : 'Offline'}</span>
          </div>
        </div>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">⚠️ {error}</div>
        )}

        <div className="game-container">
          <div className="state-hint">{getStateHint()}</div>

          <CharacterCanvas
            gameState={gameState}
            mood={catMood}
            width={600}
            height={380}
          />

          <CaptionDisplay
            transcript={transcript}
            replyText={replyText}
            catName={CAT_NAME}
          />

          <div className="controls">
            <PushToTalkButton
              gameState={gameState}
              onPress={startListening}
              onRelease={stopListening}
              disabled={!isConnected}
            />
          </div>

          <div className="instructions">
            <p>Hold the button and talk to {CAT_NAME}!</p>
            <p className="hint-subtle">
              {CAT_NAME} might talk to you first — cats do what they want 🐾
            </p>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>🐾 Local Pet AI • Whiskers runs entirely on your device</p>
      </footer>
    </div>
  );
}

export default App;
