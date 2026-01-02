using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace KidsVoiceGame.UI
{
    /// <summary>
    /// Displays captions/subtitles for user speech and game responses
    /// </summary>
    public class CaptionController : MonoBehaviour
    {
        [Header("UI References")]
        [SerializeField] private Text userTranscriptText;
        [SerializeField] private Text replyText;
        [SerializeField] private CanvasGroup userCaptionGroup;
        [SerializeField] private CanvasGroup replyCaptionGroup;

        [Header("Display Settings")]
        [SerializeField] private float fadeInDuration = 0.3f;
        [SerializeField] private float fadeOutDuration = 0.5f;
        [SerializeField] private float userCaptionDisplayTime = 3f;

        private Coroutine userCaptionCoroutine;
        private Coroutine replyCaptionCoroutine;

        private void Awake()
        {
            // Start with captions hidden
            if (userCaptionGroup != null)
                userCaptionGroup.alpha = 0;

            if (replyCaptionGroup != null)
                replyCaptionGroup.alpha = 0;
        }

        /// <summary>
        /// Show user transcript
        /// </summary>
        public void ShowUserTranscript(string text)
        {
            if (string.IsNullOrEmpty(text)) return;

            if (userTranscriptText != null)
                userTranscriptText.text = $"You: {text}";

            if (userCaptionCoroutine != null)
                StopCoroutine(userCaptionCoroutine);

            userCaptionCoroutine = StartCoroutine(ShowUserCaptionTemporary());
        }

        /// <summary>
        /// Show game reply
        /// </summary>
        public void ShowReply(string text)
        {
            if (string.IsNullOrEmpty(text)) return;

            if (replyText != null)
                replyText.text = text;

            if (replyCaptionCoroutine != null)
                StopCoroutine(replyCaptionCoroutine);

            replyCaptionCoroutine = StartCoroutine(ShowReplyCaptionWithFade());
        }

        /// <summary>
        /// Hide reply caption
        /// </summary>
        public void HideReply()
        {
            if (replyCaptionCoroutine != null)
                StopCoroutine(replyCaptionCoroutine);

            replyCaptionCoroutine = StartCoroutine(FadeOutCaption(replyCaptionGroup));
        }

        /// <summary>
        /// Clear all captions
        /// </summary>
        public void ClearAll()
        {
            if (userCaptionCoroutine != null)
                StopCoroutine(userCaptionCoroutine);

            if (replyCaptionCoroutine != null)
                StopCoroutine(replyCaptionCoroutine);

            if (userCaptionGroup != null)
                userCaptionGroup.alpha = 0;

            if (replyCaptionGroup != null)
                replyCaptionGroup.alpha = 0;
        }

        /// <summary>
        /// Show user caption temporarily, then fade out
        /// </summary>
        private IEnumerator ShowUserCaptionTemporary()
        {
            // Fade in
            yield return FadeInCaption(userCaptionGroup);

            // Display
            yield return new WaitForSeconds(userCaptionDisplayTime);

            // Fade out
            yield return FadeOutCaption(userCaptionGroup);
        }

        /// <summary>
        /// Show reply caption with fade in
        /// </summary>
        private IEnumerator ShowReplyCaptionWithFade()
        {
            yield return FadeInCaption(replyCaptionGroup);
        }

        /// <summary>
        /// Fade in a caption group
        /// </summary>
        private IEnumerator FadeInCaption(CanvasGroup group)
        {
            if (group == null) yield break;

            float elapsed = 0;
            while (elapsed < fadeInDuration)
            {
                elapsed += Time.deltaTime;
                group.alpha = Mathf.Lerp(0, 1, elapsed / fadeInDuration);
                yield return null;
            }

            group.alpha = 1;
        }

        /// <summary>
        /// Fade out a caption group
        /// </summary>
        private IEnumerator FadeOutCaption(CanvasGroup group)
        {
            if (group == null) yield break;

            float elapsed = 0;
            float startAlpha = group.alpha;

            while (elapsed < fadeOutDuration)
            {
                elapsed += Time.deltaTime;
                group.alpha = Mathf.Lerp(startAlpha, 0, elapsed / fadeOutDuration);
                yield return null;
            }

            group.alpha = 0;
        }
    }
}
