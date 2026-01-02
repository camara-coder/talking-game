using System;
using UnityEngine;

namespace KidsVoiceGame.Audio
{
    /// <summary>
    /// Plays voice audio clips from the service
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    public class VoiceAudioPlayer : MonoBehaviour
    {
        private AudioSource audioSource;

        public bool IsPlaying => audioSource != null && audioSource.isPlaying;

        public event Action OnPlaybackStarted;
        public event Action OnPlaybackComplete;

        private void Awake()
        {
            audioSource = GetComponent<AudioSource>();
            audioSource.playOnAwake = false;
        }

        /// <summary>
        /// Play an audio clip
        /// </summary>
        public void Play(AudioClip clip)
        {
            if (clip == null)
            {
                Debug.LogError("Cannot play null audio clip");
                return;
            }

            Debug.Log($"Playing audio clip: {clip.name} ({clip.length}s)");

            audioSource.clip = clip;
            audioSource.Play();

            OnPlaybackStarted?.Invoke();

            // Start coroutine to detect when playback completes
            StartCoroutine(WaitForPlaybackComplete(clip.length));
        }

        /// <summary>
        /// Stop playback
        /// </summary>
        public void Stop()
        {
            if (audioSource.isPlaying)
            {
                audioSource.Stop();
                Debug.Log("Audio playback stopped");
            }
        }

        private System.Collections.IEnumerator WaitForPlaybackComplete(float duration)
        {
            yield return new WaitForSeconds(duration);

            if (!audioSource.isPlaying)
            {
                Debug.Log("Audio playback complete");
                OnPlaybackComplete?.Invoke();
            }
        }
    }
}
