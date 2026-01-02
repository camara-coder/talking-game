using System;
using UnityEngine;
using UnityEngine.UI;

namespace KidsVoiceGame.UI
{
    /// <summary>
    /// Push-to-talk button controller
    /// </summary>
    [RequireComponent(typeof(Button))]
    public class PushToTalkButton : MonoBehaviour
    {
        [Header("UI References")]
        [SerializeField] private Text buttonLabel;

        [Header("Button States")]
        [SerializeField] private string idleText = "Hold to Talk";
        [SerializeField] private string listeningText = "Listening...";
        [SerializeField] private string processingText = "Thinking...";
        [SerializeField] private Color idleColor = Color.green;
        [SerializeField] private Color listeningColor = Color.red;
        [SerializeField] private Color disabledColor = Color.gray;

        private Button button;
        private Image buttonImage;
        private bool isPressed = false;
        private bool isEnabled = true;

        public bool IsPressed => isPressed;
        public bool IsEnabled => isEnabled;

        // Events
        public event Action OnPressStart;
        public event Action OnPressEnd;

        private void Awake()
        {
            button = GetComponent<Button>();
            buttonImage = GetComponent<Image>();

            // Set up button listeners
            var eventTrigger = gameObject.AddComponent<UnityEngine.EventSystems.EventTrigger>();

            // Press down
            var pointerDown = new UnityEngine.EventSystems.EventTrigger.Entry
            {
                eventID = UnityEngine.EventSystems.EventTriggerType.PointerDown
            };
            pointerDown.callback.AddListener((data) => { HandlePressStart(); });
            eventTrigger.triggers.Add(pointerDown);

            // Release
            var pointerUp = new UnityEngine.EventSystems.EventTrigger.Entry
            {
                eventID = UnityEngine.EventSystems.EventTriggerType.PointerUp
            };
            pointerUp.callback.AddListener((data) => { HandlePressEnd(); });
            eventTrigger.triggers.Add(pointerUp);

            SetIdleState();
        }

        private void HandlePressStart()
        {
            if (!isEnabled) return;

            isPressed = true;
            SetListeningState();
            OnPressStart?.Invoke();
        }

        private void HandlePressEnd()
        {
            if (!isPressed) return;

            isPressed = false;
            SetProcessingState();
            OnPressEnd?.Invoke();
        }

        /// <summary>
        /// Set button to idle state (ready to talk)
        /// </summary>
        public void SetIdleState()
        {
            isEnabled = true;
            button.interactable = true;

            if (buttonLabel != null)
                buttonLabel.text = idleText;

            if (buttonImage != null)
                buttonImage.color = idleColor;
        }

        /// <summary>
        /// Set button to listening state (recording)
        /// </summary>
        public void SetListeningState()
        {
            if (buttonLabel != null)
                buttonLabel.text = listeningText;

            if (buttonImage != null)
                buttonImage.color = listeningColor;
        }

        /// <summary>
        /// Set button to processing state (thinking)
        /// </summary>
        public void SetProcessingState()
        {
            isEnabled = false;
            button.interactable = false;

            if (buttonLabel != null)
                buttonLabel.text = processingText;

            if (buttonImage != null)
                buttonImage.color = disabledColor;
        }

        /// <summary>
        /// Set button to disabled state (speaking or error)
        /// </summary>
        public void SetDisabledState()
        {
            isEnabled = false;
            button.interactable = false;

            if (buttonImage != null)
                buttonImage.color = disabledColor;
        }
    }
}
