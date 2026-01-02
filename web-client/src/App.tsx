import { useVoiceService } from './hooks/useVoiceService';
import { CharacterCanvas } from './components/CharacterCanvas';
import { PushToTalkButton } from './components/PushToTalkButton';
import { CaptionDisplay } from './components/CaptionDisplay';
import './App.css';

function App() {
  const {
    gameState,
    transcript,
    replyText,
    error,
    isConnected,
    startListening,
    stopListening,
  } = useVoiceService();

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎮 Voice Game for Kids</h1>
        <div className="status-indicator">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          <span className="status-text">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            ⚠️ {error}
          </div>
        )}

        <div className="game-container">
          <CharacterCanvas gameState={gameState} width={600} height={400} />

          <CaptionDisplay transcript={transcript} replyText={replyText} />

          <div className="controls">
            <PushToTalkButton
              gameState={gameState}
              onPress={startListening}
              onRelease={stopListening}
              disabled={!isConnected}
            />
          </div>

          <div className="instructions">
            <p>Hold the button and speak, then release to send your message!</p>
            <p>Try asking: "What is 5 plus 5?" or "What is a cat?"</p>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Local Voice AI • Powered by Ollama & Pipecat</p>
      </footer>
    </div>
  );
}

export default App;
