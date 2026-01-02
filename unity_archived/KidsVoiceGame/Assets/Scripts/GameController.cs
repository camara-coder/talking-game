using System;
using UnityEngine;
using KidsVoiceGame.Api;
using KidsVoiceGame.Audio;
using KidsVoiceGame.Models;
using KidsVoiceGame.UI;

namespace KidsVoiceGame
{
    /// <summary>
    /// Main game controller - orchestrates all components
    /// </summary>
    public class GameController : MonoBehaviour
    {
        [Header("Service Components")]
        [SerializeField] private VoiceServiceClient serviceClient;
        [SerializeField] private VoiceWebSocketClient webSocketClient;

        [Header("Audio")]
        [SerializeField] private VoiceAudioPlayer audioPlayer;

        [Header("UI Components")]
        [SerializeField] private PushToTalkButton pushToTalkButton;
        [SerializeField] private CaptionController captionController;
        [SerializeField] private CharacterStateController characterController;

        [Header("Settings")]
        [SerializeField] private bool checkHealthOnStart = true;

        private string currentSessionId;
        private GameState currentState = GameState.Idle;

        private void Start()
        {
            InitializeComponents();

            if (checkHealthOnStart)
            {
                StartCoroutine(CheckServiceHealth());
            }
        }

        private void InitializeComponents()
        {
            // Subscribe to button events
            if (pushToTalkButton != null)
            {
                pushToTalkButton.OnPressStart += HandleTalkButtonPressed;
                pushToTalkButton.OnPressEnd += HandleTalkButtonReleased;
            }

            // Subscribe to WebSocket events
            if (webSocketClient != null)
            {
                webSocketClient.OnStateChanged += HandleStateChanged;
                webSocketClient.OnTranscriptReceived += HandleTranscriptReceived;
                webSocketClient.OnReplyReceived += HandleReplyReceived;
                webSocketClient.OnAudioReady += HandleAudioReady;
                webSocketClient.OnError += HandleError;
            }

            // Subscribe to audio events
            if (audioPlayer != null)
            {
                audioPlayer.OnPlaybackStarted += HandleAudioPlaybackStarted;
                audioPlayer.OnPlaybackComplete += HandleAudioPlaybackComplete;
            }

            Debug.Log("GameController initialized");
        }

        /// <summary>
        /// Check if voice service is healthy
        /// </summary>
        private System.Collections.IEnumerator CheckServiceHealth()
        {
            Debug.Log("Checking voice service health...");

            yield return serviceClient.CheckHealth((isHealthy) =>
            {
                if (isHealthy)
                {
                    Debug.Log("Voice service is healthy!");
                    SetState(GameState.Idle);
                }
                else
                {
                    Debug.LogError("Voice service is not responding!");
                    SetState(GameState.Error);
                }
            });
        }

        /// <summary>
        /// Handle talk button pressed (start listening)
        /// </summary>
        private void HandleTalkButtonPressed()
        {
            Debug.Log("Talk button pressed - starting session");
            StartCoroutine(StartListeningSession());
        }

        /// <summary>
        /// Handle talk button released (stop listening, process)
        /// </summary>
        private void HandleTalkButtonReleased()
        {
            Debug.Log("Talk button released - stopping session");
            StartCoroutine(StopListeningSession());
        }

        /// <summary>
        /// Start a new listening session
        /// </summary>
        private System.Collections.IEnumerator StartListeningSession()
        {
            // Start session via HTTP
            yield return serviceClient.StartSession(
                onSuccess: async (response) =>
                {
                    currentSessionId = response.session_id;
                    Debug.Log($"Session started: {currentSessionId}");

                    // Connect WebSocket
                    try
                    {
                        await webSocketClient.Connect(currentSessionId);
                        Debug.Log("WebSocket connected");
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"WebSocket connection failed: {ex.Message}");
                        SetState(GameState.Error);
                    }
                },
                onError: (error) =>
                {
                    Debug.LogError($"Failed to start session: {error}");
                    SetState(GameState.Error);
                    pushToTalkButton.SetIdleState();
                }
            );
        }

        /// <summary>
        /// Stop listening session and trigger processing
        /// </summary>
        private System.Collections.IEnumerator StopListeningSession()
        {
            if (string.IsNullOrEmpty(currentSessionId))
            {
                Debug.LogError("No active session to stop");
                yield break;
            }

            // Stop session via HTTP (triggers pipeline processing)
            yield return serviceClient.StopSession(
                currentSessionId,
                onSuccess: (response) =>
                {
                    Debug.Log($"Session stopped: {response.session_id}");
                    // State updates will come via WebSocket events
                },
                onError: (error) =>
                {
                    Debug.LogError($"Failed to stop session: {error}");
                    SetState(GameState.Error);
                    pushToTalkButton.SetIdleState();
                }
            );
        }

        /// <summary>
        /// Handle state change from WebSocket
        /// </summary>
        private void HandleStateChanged(GameState newState)
        {
            Debug.Log($"State changed: {currentState} -> {newState}");
            SetState(newState);
        }

        /// <summary>
        /// Handle transcript from WebSocket
        /// </summary>
        private void HandleTranscriptReceived(string transcript)
        {
            Debug.Log($"Transcript: {transcript}");

            if (captionController != null)
            {
                captionController.ShowUserTranscript(transcript);
            }
        }

        /// <summary>
        /// Handle reply text from WebSocket
        /// </summary>
        private void HandleReplyReceived(string reply)
        {
            Debug.Log($"Reply: {reply}");

            if (captionController != null)
            {
                captionController.ShowReply(reply);
            }
        }

        /// <summary>
        /// Handle audio ready event from WebSocket
        /// </summary>
        private void HandleAudioReady(string audioUrl, int durationMs)
        {
            Debug.Log($"Audio ready: {audioUrl} ({durationMs}ms)");

            // Download and play audio
            StartCoroutine(DownloadAndPlayAudio(audioUrl));
        }

        /// <summary>
        /// Download and play audio clip
        /// </summary>
        private System.Collections.IEnumerator DownloadAndPlayAudio(string audioUrl)
        {
            yield return serviceClient.DownloadAudio(
                audioUrl,
                onSuccess: (clip) =>
                {
                    Debug.Log($"Audio downloaded: {clip.length}s");

                    if (audioPlayer != null)
                    {
                        audioPlayer.Play(clip);
                    }
                },
                onError: (error) =>
                {
                    Debug.LogError($"Failed to download audio: {error}");
                    SetState(GameState.Error);
                }
            );
        }

        /// <summary>
        /// Handle audio playback started
        /// </summary>
        private void HandleAudioPlaybackStarted()
        {
            Debug.Log("Audio playback started");
            SetState(GameState.Speaking);
        }

        /// <summary>
        /// Handle audio playback complete
        /// </summary>
        private void HandleAudioPlaybackComplete()
        {
            Debug.Log("Audio playback complete");

            // Disconnect WebSocket
            _ = webSocketClient.Disconnect();

            // Return to idle
            SetState(GameState.Idle);
        }

        /// <summary>
        /// Handle error from WebSocket
        /// </summary>
        private void HandleError(string error)
        {
            Debug.LogError($"Voice service error: {error}");
            SetState(GameState.Error);

            // Show error in caption
            if (captionController != null)
            {
                captionController.ShowReply($"Error: {error}");
            }

            // Reset after a delay
            Invoke(nameof(ResetToIdle), 3f);
        }

        /// <summary>
        /// Reset to idle state
        /// </summary>
        private void ResetToIdle()
        {
            SetState(GameState.Idle);

            if (captionController != null)
            {
                captionController.ClearAll();
            }
        }

        /// <summary>
        /// Set current game state and update UI
        /// </summary>
        private void SetState(GameState newState)
        {
            currentState = newState;

            // Update character visual
            if (characterController != null)
            {
                characterController.SetState(newState);
            }

            // Update button state
            if (pushToTalkButton != null)
            {
                switch (newState)
                {
                    case GameState.Idle:
                        pushToTalkButton.SetIdleState();
                        break;
                    case GameState.Listening:
                        pushToTalkButton.SetListeningState();
                        break;
                    case GameState.Thinking:
                    case GameState.Speaking:
                        pushToTalkButton.SetDisabledState();
                        break;
                    case GameState.Error:
                        pushToTalkButton.SetIdleState();
                        break;
                }
            }
        }

        private void OnDestroy()
        {
            // Unsubscribe from events
            if (pushToTalkButton != null)
            {
                pushToTalkButton.OnPressStart -= HandleTalkButtonPressed;
                pushToTalkButton.OnPressEnd -= HandleTalkButtonReleased;
            }

            if (webSocketClient != null)
            {
                webSocketClient.OnStateChanged -= HandleStateChanged;
                webSocketClient.OnTranscriptReceived -= HandleTranscriptReceived;
                webSocketClient.OnReplyReceived -= HandleReplyReceived;
                webSocketClient.OnAudioReady -= HandleAudioReady;
                webSocketClient.OnError -= HandleError;
            }

            if (audioPlayer != null)
            {
                audioPlayer.OnPlaybackStarted -= HandleAudioPlaybackStarted;
                audioPlayer.OnPlaybackComplete -= HandleAudioPlaybackComplete;
            }
        }
    }
}
