using UnityEngine;
using UnityEngine.UI;
using KidsVoiceGame.Models;

namespace KidsVoiceGame.UI
{
    /// <summary>
    /// Controls character visual state based on game state
    /// </summary>
    public class CharacterStateController : MonoBehaviour
    {
        [Header("Character Visual")]
        [SerializeField] private Image characterImage;
        [SerializeField] private Animator characterAnimator;
        [SerializeField] private Text stateLabel;

        [Header("State Sprites (Optional)")]
        [SerializeField] private Sprite idleSprite;
        [SerializeField] private Sprite listeningSprite;
        [SerializeField] private Sprite thinkingSprite;
        [SerializeField] private Sprite speakingSprite;
        [SerializeField] private Sprite errorSprite;

        [Header("State Colors")]
        [SerializeField] private Color idleColor = Color.white;
        [SerializeField] private Color listeningColor = Color.cyan;
        [SerializeField] private Color thinkingColor = Color.yellow;
        [SerializeField] private Color speakingColor = Color.green;
        [SerializeField] private Color errorColor = Color.red;

        [Header("Animation (Optional)")]
        [SerializeField] private bool useAnimator = false;
        [SerializeField] private float pulseSpeed = 2f;
        [SerializeField] private float pulseAmount = 0.1f;

        private GameState currentState = GameState.Idle;
        private Vector3 originalScale;
        private bool isPulsing = false;

        private void Awake()
        {
            if (characterImage != null)
                originalScale = characterImage.transform.localScale;

            SetState(GameState.Idle);
        }

        private void Update()
        {
            if (isPulsing && characterImage != null)
            {
                float scale = 1f + Mathf.Sin(Time.time * pulseSpeed) * pulseAmount;
                characterImage.transform.localScale = originalScale * scale;
            }
        }

        /// <summary>
        /// Set character state
        /// </summary>
        public void SetState(GameState state)
        {
            currentState = state;

            switch (state)
            {
                case GameState.Idle:
                    SetIdleState();
                    break;
                case GameState.Listening:
                    SetListeningState();
                    break;
                case GameState.Thinking:
                    SetThinkingState();
                    break;
                case GameState.Speaking:
                    SetSpeakingState();
                    break;
                case GameState.Error:
                    SetErrorState();
                    break;
            }

            Debug.Log($"Character state: {state}");
        }

        private void SetIdleState()
        {
            isPulsing = false;
            ResetScale();

            if (characterImage != null)
            {
                characterImage.color = idleColor;
                if (idleSprite != null)
                    characterImage.sprite = idleSprite;
            }

            if (stateLabel != null)
                stateLabel.text = "Ready";

            if (useAnimator && characterAnimator != null)
                characterAnimator.SetTrigger("Idle");
        }

        private void SetListeningState()
        {
            isPulsing = true;

            if (characterImage != null)
            {
                characterImage.color = listeningColor;
                if (listeningSprite != null)
                    characterImage.sprite = listeningSprite;
            }

            if (stateLabel != null)
                stateLabel.text = "Listening...";

            if (useAnimator && characterAnimator != null)
                characterAnimator.SetTrigger("Listening");
        }

        private void SetThinkingState()
        {
            isPulsing = true;

            if (characterImage != null)
            {
                characterImage.color = thinkingColor;
                if (thinkingSprite != null)
                    characterImage.sprite = thinkingSprite;
            }

            if (stateLabel != null)
                stateLabel.text = "Thinking...";

            if (useAnimator && characterAnimator != null)
                characterAnimator.SetTrigger("Thinking");
        }

        private void SetSpeakingState()
        {
            isPulsing = true;

            if (characterImage != null)
            {
                characterImage.color = speakingColor;
                if (speakingSprite != null)
                    characterImage.sprite = speakingSprite;
            }

            if (stateLabel != null)
                stateLabel.text = "Speaking...";

            if (useAnimator && characterAnimator != null)
                characterAnimator.SetTrigger("Speaking");
        }

        private void SetErrorState()
        {
            isPulsing = false;
            ResetScale();

            if (characterImage != null)
            {
                characterImage.color = errorColor;
                if (errorSprite != null)
                    characterImage.sprite = errorSprite;
            }

            if (stateLabel != null)
                stateLabel.text = "Error";

            if (useAnimator && characterAnimator != null)
                characterAnimator.SetTrigger("Error");
        }

        private void ResetScale()
        {
            if (characterImage != null)
                characterImage.transform.localScale = originalScale;
        }
    }
}
