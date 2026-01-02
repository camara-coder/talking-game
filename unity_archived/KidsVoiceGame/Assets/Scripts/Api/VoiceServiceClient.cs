using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using KidsVoiceGame.Models;

namespace KidsVoiceGame.Api
{
    /// <summary>
    /// HTTP client for Voice Service API
    /// </summary>
    public class VoiceServiceClient : MonoBehaviour
    {
        [Header("Service Configuration")]
        [SerializeField] private string serviceHost = "127.0.0.1";
        [SerializeField] private int servicePort = 8008;

        private string BaseUrl => $"http://{serviceHost}:{servicePort}";

        /// <summary>
        /// Start a new session
        /// </summary>
        public IEnumerator StartSession(Action<SessionStartResponse> onSuccess, Action<string> onError)
        {
            string url = $"{BaseUrl}/api/session/start";

            SessionStartRequest request = new SessionStartRequest
            {
                language = "en",
                mode = "ptt"
            };

            string jsonData = JsonUtility.ToJson(request);

            using (UnityWebRequest webRequest = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);
                webRequest.uploadHandler = new UploadHandlerRaw(bodyRaw);
                webRequest.downloadHandler = new DownloadHandlerBuffer();
                webRequest.SetRequestHeader("Content-Type", "application/json");

                yield return webRequest.SendWebRequest();

                if (webRequest.result == UnityWebRequest.Result.Success)
                {
                    string responseText = webRequest.downloadHandler.text;
                    SessionStartResponse response = JsonUtility.FromJson<SessionStartResponse>(responseText);
                    onSuccess?.Invoke(response);
                }
                else
                {
                    onError?.Invoke($"StartSession failed: {webRequest.error}");
                }
            }
        }

        /// <summary>
        /// Stop current session (triggers pipeline processing)
        /// </summary>
        public IEnumerator StopSession(string sessionId, Action<SessionStopResponse> onSuccess, Action<string> onError)
        {
            string url = $"{BaseUrl}/api/session/stop";

            SessionStopRequest request = new SessionStopRequest
            {
                session_id = sessionId,
                return_audio = true
            };

            string jsonData = JsonUtility.ToJson(request);

            using (UnityWebRequest webRequest = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);
                webRequest.uploadHandler = new UploadHandlerRaw(bodyRaw);
                webRequest.downloadHandler = new DownloadHandlerBuffer();
                webRequest.SetRequestHeader("Content-Type", "application/json");

                yield return webRequest.SendWebRequest();

                if (webRequest.result == UnityWebRequest.Result.Success)
                {
                    string responseText = webRequest.downloadHandler.text;
                    SessionStopResponse response = JsonUtility.FromJson<SessionStopResponse>(responseText);
                    onSuccess?.Invoke(response);
                }
                else
                {
                    onError?.Invoke($"StopSession failed: {webRequest.error}");
                }
            }
        }

        /// <summary>
        /// Download audio file
        /// </summary>
        public IEnumerator DownloadAudio(string audioUrl, Action<AudioClip> onSuccess, Action<string> onError)
        {
            using (UnityWebRequest webRequest = UnityWebRequestMultimedia.GetAudioClip(audioUrl, AudioType.WAV))
            {
                yield return webRequest.SendWebRequest();

                if (webRequest.result == UnityWebRequest.Result.Success)
                {
                    AudioClip clip = DownloadHandlerAudioClip.GetContent(webRequest);
                    onSuccess?.Invoke(clip);
                }
                else
                {
                    onError?.Invoke($"DownloadAudio failed: {webRequest.error}");
                }
            }
        }

        /// <summary>
        /// Check service health
        /// </summary>
        public IEnumerator CheckHealth(Action<bool> onComplete)
        {
            string url = $"{BaseUrl}/health";

            using (UnityWebRequest webRequest = UnityWebRequest.Get(url))
            {
                yield return webRequest.SendWebRequest();
                onComplete?.Invoke(webRequest.result == UnityWebRequest.Result.Success);
            }
        }
    }
}
