using System;
using System.Threading.Tasks;
using UnityEngine;
using NativeWebSocket;
using KidsVoiceGame.Models;

namespace KidsVoiceGame.Api
{
    /// <summary>
    /// WebSocket client for real-time events from Voice Service
    /// </summary>
    public class VoiceWebSocketClient : MonoBehaviour
    {
        [Header("Service Configuration")]
        [SerializeField] private string serviceHost = "127.0.0.1";
        [SerializeField] private int servicePort = 8008;

        private WebSocket websocket;
        private string currentSessionId;

        // Events
        public event Action<GameState> OnStateChanged;
        public event Action<string> OnTranscriptReceived;
        public event Action<string> OnReplyReceived;
        public event Action<string, int> OnAudioReady; // URL, duration_ms
        public event Action<string> OnError;

        private void Update()
        {
            #if !UNITY_WEBGL || UNITY_EDITOR
            websocket?.DispatchMessageQueue();
            #endif
        }

        /// <summary>
        /// Connect to WebSocket
        /// </summary>
        public async Task Connect(string sessionId)
        {
            currentSessionId = sessionId;
            string wsUrl = $"ws://{serviceHost}:{servicePort}/ws?session_id={sessionId}";

            Debug.Log($"Connecting to WebSocket: {wsUrl}");

            websocket = new WebSocket(wsUrl);

            websocket.OnOpen += () =>
            {
                Debug.Log("WebSocket connected!");
            };

            websocket.OnError += (e) =>
            {
                Debug.LogError($"WebSocket error: {e}");
                OnError?.Invoke(e);
            };

            websocket.OnClose += (e) =>
            {
                Debug.Log($"WebSocket closed: {e}");
            };

            websocket.OnMessage += (bytes) =>
            {
                string message = System.Text.Encoding.UTF8.GetString(bytes);
                HandleMessage(message);
            };

            await websocket.Connect();
        }

        /// <summary>
        /// Disconnect from WebSocket
        /// </summary>
        public async Task Disconnect()
        {
            if (websocket != null && websocket.State == WebSocketState.Open)
            {
                await websocket.Close();
            }
        }

        /// <summary>
        /// Handle incoming WebSocket message
        /// </summary>
        private void HandleMessage(string message)
        {
            Debug.Log($"WebSocket message: {message}");

            try
            {
                WebSocketEvent wsEvent = JsonUtility.FromJson<WebSocketEvent>(message);
                EventType eventType = EventTypeHelper.Parse(wsEvent.type);

                switch (eventType)
                {
                    case EventType.State:
                        if (wsEvent.payload != null && !string.IsNullOrEmpty(wsEvent.payload.state))
                        {
                            GameState state = GameStateHelper.Parse(wsEvent.payload.state);
                            Debug.Log($"State changed: {state}");
                            OnStateChanged?.Invoke(state);
                        }
                        break;

                    case EventType.TranscriptPartial:
                    case EventType.TranscriptFinal:
                        if (wsEvent.payload != null && !string.IsNullOrEmpty(wsEvent.payload.text))
                        {
                            Debug.Log($"Transcript: {wsEvent.payload.text}");
                            OnTranscriptReceived?.Invoke(wsEvent.payload.text);
                        }
                        break;

                    case EventType.ReplyText:
                        if (wsEvent.payload != null && !string.IsNullOrEmpty(wsEvent.payload.text))
                        {
                            Debug.Log($"Reply: {wsEvent.payload.text}");
                            OnReplyReceived?.Invoke(wsEvent.payload.text);
                        }
                        break;

                    case EventType.ReplyAudioReady:
                        if (wsEvent.payload != null && !string.IsNullOrEmpty(wsEvent.payload.url))
                        {
                            Debug.Log($"Audio ready: {wsEvent.payload.url}");
                            OnAudioReady?.Invoke(wsEvent.payload.url, wsEvent.payload.duration_ms);
                        }
                        break;

                    case EventType.Error:
                        if (wsEvent.payload != null)
                        {
                            string errorMsg = $"{wsEvent.payload.code}: {wsEvent.payload.message}";
                            Debug.LogError($"Error event: {errorMsg}");
                            OnError?.Invoke(errorMsg);
                        }
                        break;
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error parsing WebSocket message: {ex.Message}");
            }
        }

        private void OnDestroy()
        {
            if (websocket != null)
            {
                _ = Disconnect();
            }
        }
    }
}
