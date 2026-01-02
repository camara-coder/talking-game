"""
Simple TTS test
"""
import os
from app.pipeline.processors.tts_processor import TTSProcessor


def test_tts():
    """Test TTS processor"""
    print("=" * 60)
    print("TTS PROCESSOR TEST")
    print("=" * 60)

    # Create TTS processor
    print("\n[1] Initializing TTS processor...")
    tts = TTSProcessor()

    # List available voices
    print("\n[2] Available voices:")
    tts.list_voices()

    # Test sentences
    test_sentences = [
        "Hello! I'm your friendly game character.",
        "Five plus five is ten.",
        "What's your favorite animal?",
        "I can help you with math, animals, or colors!"
    ]

    output_dir = "data/test_audio"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[3] Testing TTS synthesis...")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for i, sentence in enumerate(test_sentences):
        output_path = os.path.join(output_dir, f"test_{i+1}.wav")

        print(f"\n  Test {i+1}: '{sentence}'")
        print(f"  Output: {output_path}")

        success = tts.synthesize(sentence, output_path)

        if success:
            file_size = os.path.getsize(output_path)
            print(f"  [OK] Generated ({file_size} bytes)")
        else:
            print(f"  [FAIL] Synthesis failed")

    print("\n" + "=" * 60)
    print("[OK] TTS test complete!")
    print("=" * 60)
    print(f"\nAudio files saved to: {os.path.abspath(output_dir)}")
    print("You can play them to verify TTS quality.")


if __name__ == "__main__":
    test_tts()
