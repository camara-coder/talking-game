"""
Unit tests for audio utilities
"""
import pytest
import numpy as np
import os
from app.utils.audio_io import save_wav, load_wav, normalize_audio
from app.utils.wav_utils import get_wav_duration, is_valid_wav


class TestWavIO:
    """Test WAV file I/O operations"""

    def test_save_and_load_wav(self, temp_audio_dir, sample_audio_16khz):
        """Test saving and loading WAV files"""
        # Save
        output_path = os.path.join(temp_audio_dir, "test_save.wav")
        save_wav(output_path, sample_audio_16khz, 16000)

        # Check file exists
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        # Load
        loaded_audio, sample_rate = load_wav(output_path)

        # Verify
        assert sample_rate == 16000
        assert loaded_audio.shape == sample_audio_16khz.shape
        np.testing.assert_array_almost_equal(loaded_audio, sample_audio_16khz, decimal=4)

    def test_save_different_sample_rates(self, temp_audio_dir, sample_audio_16khz):
        """Test saving with different sample rates"""
        for sr in [8000, 16000, 24000, 48000]:
            output_path = os.path.join(temp_audio_dir, f"test_{sr}.wav")
            save_wav(output_path, sample_audio_16khz, sr)

            loaded_audio, loaded_sr = load_wav(output_path)
            assert loaded_sr == sr

    def test_save_empty_audio(self, temp_audio_dir):
        """Test saving empty audio"""
        empty_audio = np.array([], dtype=np.float32)
        output_path = os.path.join(temp_audio_dir, "empty.wav")

        with pytest.raises(ValueError):
            save_wav(output_path, empty_audio, 16000)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_wav("nonexistent.wav")


class TestAudioNormalization:
    """Test audio normalization"""

    def test_normalize_loud_audio(self):
        """Test normalizing loud audio"""
        # Create audio that exceeds [-1, 1]
        audio = np.array([0.5, 1.5, -2.0, 0.8], dtype=np.float32)
        normalized = normalize_audio(audio)

        # Should be within [-1, 1]
        assert normalized.min() >= -1.0
        assert normalized.max() <= 1.0

        # Should preserve relative relationships
        assert normalized[1] > normalized[0]  # 1.5 > 0.5
        assert normalized[2] < normalized[3]  # -2.0 < 0.8

    def test_normalize_normal_audio(self, sample_audio_16khz):
        """Test normalizing already normal audio"""
        normalized = normalize_audio(sample_audio_16khz)

        assert normalized.min() >= -1.0
        assert normalized.max() <= 1.0

    def test_normalize_zero_audio(self):
        """Test normalizing zero/silent audio"""
        audio = np.zeros(1000, dtype=np.float32)
        normalized = normalize_audio(audio)

        # Should remain zeros
        np.testing.assert_array_equal(normalized, audio)


class TestWavUtils:
    """Test WAV utility functions"""

    def test_get_wav_duration(self, temp_wav_file):
        """Test getting WAV duration"""
        duration = get_wav_duration(str(temp_wav_file))

        # Should be approximately 1 second (we created 1s of audio)
        assert 0.9 <= duration <= 1.1

    def test_get_wav_duration_nonexistent(self):
        """Test getting duration of non-existent file"""
        with pytest.raises(FileNotFoundError):
            get_wav_duration("nonexistent.wav")

    def test_is_valid_wav(self, temp_wav_file):
        """Test WAV file validation"""
        assert is_valid_wav(str(temp_wav_file))

    def test_is_valid_wav_invalid_file(self, temp_audio_dir):
        """Test validation of invalid WAV file"""
        # Create a non-WAV file
        invalid_file = temp_audio_dir / "invalid.wav"
        invalid_file.write_text("This is not a WAV file")

        assert not is_valid_wav(str(invalid_file))

    def test_is_valid_wav_nonexistent(self):
        """Test validation of non-existent file"""
        assert not is_valid_wav("nonexistent.wav")


class TestAudioConversions:
    """Test audio format conversions"""

    def test_int16_to_float32(self):
        """Test converting int16 to float32"""
        # Create int16 audio
        int16_audio = np.array([0, 16384, -16384, 32767, -32768], dtype=np.int16)

        # Convert to float32
        float32_audio = int16_audio.astype(np.float32) / 32768.0

        # Verify range
        assert float32_audio.min() >= -1.0
        assert float32_audio.max() <= 1.0

        # Verify values
        assert float32_audio[0] == 0.0
        assert abs(float32_audio[3] - 0.999969) < 0.0001  # ~1.0
        assert float32_audio[4] == -1.0

    def test_float32_to_int16(self):
        """Test converting float32 to int16"""
        # Create float32 audio
        float32_audio = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)

        # Convert to int16
        int16_audio = (float32_audio * 32767).astype(np.int16)

        # Verify
        assert int16_audio[0] == 0
        assert int16_audio[1] == 16383
        assert int16_audio[2] == -16383
        assert int16_audio[3] == 32767
        assert int16_audio[4] == -32767


class TestAudioProperties:
    """Test audio property calculations"""

    def test_calculate_rms(self, sample_audio_16khz):
        """Test RMS calculation"""
        rms = np.sqrt(np.mean(sample_audio_16khz ** 2))
        assert rms > 0
        assert rms <= 1.0

    def test_calculate_peak(self, sample_audio_16khz):
        """Test peak calculation"""
        peak = np.max(np.abs(sample_audio_16khz))
        assert peak > 0
        assert peak <= 1.0

    def test_silent_audio_properties(self, silence_audio):
        """Test properties of silent audio"""
        rms = np.sqrt(np.mean(silence_audio ** 2))
        peak = np.max(np.abs(silence_audio))

        assert rms == 0.0
        assert peak == 0.0

    def test_duration_calculation(self, sample_audio_16khz):
        """Test duration calculation"""
        sample_rate = 16000
        duration = len(sample_audio_16khz) / sample_rate

        assert 0.9 <= duration <= 1.1  # Should be ~1 second
