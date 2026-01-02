"""
Voice Processing Pipeline
Orchestrates all processors to convert audio to text response
"""
import logging
import numpy as np
from typing import Optional, Dict, Any
import time

from app.pipeline.processors.vad_processor import VADProcessor
from app.pipeline.processors.stt_elevenlabs import ElevenLabsSTTProcessor as STTProcessor
from app.pipeline.processors.skills_router import SkillsRouterProcessor
from app.pipeline.processors.llm_ollama import OllamaLLMProcessor
from app.pipeline.processors.response_shaper import ResponseShaperProcessor
from app.config import settings

logger = logging.getLogger(__name__)


class VoicePipeline:
    """Voice processing pipeline"""

    def __init__(self):
        """Initialize voice pipeline with all processors"""
        logger.info("Initializing voice pipeline...")

        # Initialize processors
        self.vad = VADProcessor()
        self.stt = STTProcessor()
        self.skills_router = SkillsRouterProcessor()
        self.llm = OllamaLLMProcessor()
        self.response_shaper = ResponseShaperProcessor()

        logger.info("Voice pipeline initialized successfully")

    def process(
        self,
        audio: np.ndarray,
        sample_rate: int = None,
        context: list = None
    ) -> Dict[str, Any]:
        """
        Process audio through complete pipeline

        Args:
            audio: Audio data as float32 numpy array
            sample_rate: Sample rate in Hz
            context: Conversation context (previous turns)

        Returns:
            Dictionary with:
                - transcript: Transcribed text
                - reply_text: Generated reply
                - route: "math" or "llm"
                - processing_time_ms: Total processing time
                - error: Error message if any
        """
        if sample_rate is None:
            sample_rate = settings.AUDIO_SAMPLE_RATE

        start_time = time.time()

        result = {
            "transcript": None,
            "reply_text": None,
            "route": None,
            "processing_time_ms": 0,
            "error": None
        }

        try:
            logger.info("=" * 60)
            logger.info("Starting voice pipeline processing")
            logger.info("=" * 60)

            # Step 1: VAD - Trim silence
            logger.info("Step 1: VAD processing...")
            vad_audio = self.vad.process(audio)

            if vad_audio is None:
                result["error"] = "No speech detected"
                logger.warning(result["error"])
                return result

            # Step 2: STT - Transcribe
            logger.info("Step 2: STT processing...")
            transcript = self.stt.transcribe(vad_audio, sample_rate)

            if not transcript:
                result["error"] = "Transcription failed or empty"
                logger.warning(result["error"])
                return result

            result["transcript"] = transcript
            logger.info(f"Transcript: '{transcript}'")

            # Step 3: Skills Router - Check for math or route to LLM
            logger.info("Step 3: Skills routing...")
            route, math_response = self.skills_router.route(transcript)
            result["route"] = route

            if route == "math" and math_response:
                # Math was handled deterministically
                reply_text = math_response
                logger.info(f"Math route: '{reply_text}'")

            elif route == "llm" or (route == "math" and not math_response):
                # Route to LLM
                logger.info("Step 4: LLM processing...")
                llm_response = self.llm.generate(
                    prompt=transcript,
                    context=context
                )

                if not llm_response:
                    result["error"] = "LLM generation failed"
                    logger.warning(result["error"])
                    return result

                reply_text = llm_response
                logger.info(f"LLM response: '{reply_text}'")

            else:
                result["error"] = "Unknown routing error"
                logger.error(result["error"])
                return result

            # Step 5: Response Shaper - Enforce kid-mode constraints
            logger.info("Step 5: Response shaping...")
            shaped_reply = self.response_shaper.shape(reply_text)
            result["reply_text"] = shaped_reply

            logger.info(f"Final reply: '{shaped_reply}'")

            # Calculate total time
            elapsed_ms = int((time.time() - start_time) * 1000)
            result["processing_time_ms"] = elapsed_ms

            logger.info("=" * 60)
            logger.info(f"Pipeline complete: {elapsed_ms}ms")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            result["error"] = str(e)
            return result


# Global pipeline instance (singleton for model loading)
_pipeline_instance = None


def get_pipeline() -> VoicePipeline:
    """Get or create global pipeline instance"""
    global _pipeline_instance

    if _pipeline_instance is None:
        _pipeline_instance = VoicePipeline()

    return _pipeline_instance
