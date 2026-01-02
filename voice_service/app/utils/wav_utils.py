"""
WAV file utilities for parsing and creating WAV files
"""
import struct
import logging

logger = logging.getLogger(__name__)


def get_wav_duration(file_path: str) -> float:
    """
    Get duration of WAV file in seconds

    Args:
        file_path: Path to WAV file

    Returns:
        Duration in seconds
    """
    try:
        with open(file_path, 'rb') as f:
            # Read RIFF header
            riff = f.read(12)
            if riff[:4] != b'RIFF' or riff[8:12] != b'WAVE':
                raise ValueError("Not a valid WAV file")

            # Find fmt chunk
            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    raise ValueError("fmt chunk not found")

                chunk_id = chunk_header[:4]
                chunk_size = struct.unpack('<I', chunk_header[4:8])[0]

                if chunk_id == b'fmt ':
                    # Read fmt chunk
                    fmt_data = f.read(chunk_size)
                    sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                    byte_rate = struct.unpack('<I', fmt_data[8:12])[0]
                    break
                else:
                    # Skip this chunk
                    f.seek(chunk_size, 1)

            # Find data chunk
            f.seek(12)  # Back to after RIFF header
            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    raise ValueError("data chunk not found")

                chunk_id = chunk_header[:4]
                chunk_size = struct.unpack('<I', chunk_header[4:8])[0]

                if chunk_id == b'data':
                    # Calculate duration
                    duration = chunk_size / byte_rate
                    return duration
                else:
                    # Skip this chunk
                    f.seek(chunk_size, 1)

    except Exception as e:
        logger.error(f"Error getting WAV duration: {e}")
        return 0.0


def get_wav_info(file_path: str) -> dict:
    """
    Get detailed information about WAV file

    Args:
        file_path: Path to WAV file

    Returns:
        Dictionary with WAV file information
    """
    try:
        with open(file_path, 'rb') as f:
            # Read RIFF header
            riff = f.read(12)
            if riff[:4] != b'RIFF' or riff[8:12] != b'WAVE':
                raise ValueError("Not a valid WAV file")

            file_size = struct.unpack('<I', riff[4:8])[0] + 8

            # Find and read fmt chunk
            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    raise ValueError("fmt chunk not found")

                chunk_id = chunk_header[:4]
                chunk_size = struct.unpack('<I', chunk_header[4:8])[0]

                if chunk_id == b'fmt ':
                    fmt_data = f.read(chunk_size)
                    audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                    num_channels = struct.unpack('<H', fmt_data[2:4])[0]
                    sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                    byte_rate = struct.unpack('<I', fmt_data[8:12])[0]
                    block_align = struct.unpack('<H', fmt_data[12:14])[0]
                    bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
                    break
                else:
                    f.seek(chunk_size, 1)

            # Find data chunk
            f.seek(12)
            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    raise ValueError("data chunk not found")

                chunk_id = chunk_header[:4]
                chunk_size = struct.unpack('<I', chunk_header[4:8])[0]

                if chunk_id == b'data':
                    data_size = chunk_size
                    break
                else:
                    f.seek(chunk_size, 1)

            # Calculate duration
            duration = data_size / byte_rate

            return {
                'file_size': file_size,
                'audio_format': audio_format,
                'num_channels': num_channels,
                'sample_rate': sample_rate,
                'byte_rate': byte_rate,
                'bits_per_sample': bits_per_sample,
                'data_size': data_size,
                'duration': duration
            }

    except Exception as e:
        logger.error(f"Error getting WAV info: {e}")
        return {}
