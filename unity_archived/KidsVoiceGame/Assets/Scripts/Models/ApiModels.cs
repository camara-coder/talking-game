using System;
using System.Collections.Generic;

namespace KidsVoiceGame.Models
{
    /// <summary>
    /// Game state enum
    /// </summary>
    public enum GameState
    {
        Idle,
        Listening,
        Thinking,
        Speaking,
        Error
    }

    /// <summary>
    /// WebSocket event types
    /// </summary>
    public enum EventType
    {
        State,
        TranscriptPartial,
        TranscriptFinal,
        ReplyText,
        ReplyAudioReady,
        Error
    }

    // ===== Request Models =====

    [Serializable]
    public class SessionStartRequest
    {
        public string session_id;
        public string language = "en";
        public string mode = "ptt";
    }

    [Serializable]
    public class SessionStopRequest
    {
        public string session_id;
        public bool return_audio = true;
    }

    // ===== Response Models =====

    [Serializable]
    public class SessionStartResponse
    {
        public string session_id;
        public string status;
        public string timestamp;
    }

    [Serializable]
    public class SessionStopResponse
    {
        public string session_id;
        public string status;
        public string timestamp;
    }

    // ===== WebSocket Event Models =====

    [Serializable]
    public class WebSocketEvent
    {
        public string type;
        public string session_id;
        public string turn_id;
        public string ts;
        public EventPayload payload;
    }

    [Serializable]
    public class EventPayload
    {
        // State event
        public string state;

        // Transcript event
        public string text;

        // Audio ready event
        public string url;
        public int duration_ms;
        public string format;
        public int sample_rate_hz;
        public int channels;

        // Error event
        public string code;
        public string message;
    }

    // ===== Helper Classes =====

    public static class EventTypeHelper
    {
        public static EventType Parse(string typeString)
        {
            switch (typeString)
            {
                case "state":
                    return EventType.State;
                case "transcript.partial":
                    return EventType.TranscriptPartial;
                case "transcript.final":
                    return EventType.TranscriptFinal;
                case "reply.text":
                    return EventType.ReplyText;
                case "reply.audio_ready":
                    return EventType.ReplyAudioReady;
                case "error":
                    return EventType.Error;
                default:
                    return EventType.State;
            }
        }
    }

    public static class GameStateHelper
    {
        public static GameState Parse(string stateString)
        {
            switch (stateString)
            {
                case "idle":
                    return GameState.Idle;
                case "listening":
                    return GameState.Listening;
                case "processing":
                    return GameState.Thinking;
                case "speaking":
                    return GameState.Speaking;
                case "error":
                    return GameState.Error;
                default:
                    return GameState.Idle;
            }
        }
    }
}
