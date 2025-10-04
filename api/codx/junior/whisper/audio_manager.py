
    
      
import logging
import time
from typing import List, Dict
from faster_whisper import WhisperModel
import requests
from tempfile import NamedTemporaryFile
import ffmpeg
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for conversion formats
SUPPORTED_CONVERSIONS: Dict[str, List[str]] = {'webm': ['wav', 'mp4']}
SUPPORTED_EXTRACTIONS: set = {'webm', 'wav', 'mp4', 'mp3'}

WHISPER_MODEL = WhisperModel(
    "small", device="cpu", compute_type="float32"
)

class AudioManager:
    """Class to manage conversion and transcription of audio/video files."""

    def __init__(self) -> None:
        """Initialize the audio manager with model configurations."""
        self.model: WhisperModel = WHISPER_MODEL

    def transcribe_from_file(self, file_path: str) -> Dict[str, str or List[Dict[str, str]]]:
        """
        Extract text from an audio or video file given a file path.

        Parameters:
            file_path (str): Path to the local file.
            language (str): Language of the audio content.

        Returns:
            Dict[str, str or List[Dict[str, str]]]: Transcription results including elapsed time and transcript.
        """
        start_time = time.perf_counter()
            
        transcript_file_path = f"{file_path}.transcript.json"
        is_new = not os.path.isfile(transcript_file_path)
        transcript = None
        if is_new:
            logger.info("Starting transcription for file: %s", file_path)
            transcript = self._perform_transcription(file_path)
            with open(transcript_file_path, "w") as file:
                file.write(json.dumps(transcript))

        elapsed_time: float = time.perf_counter() - start_time
        logger.info(
            "Transcription completed in %.2f seconds for file: %s", elapsed_time, file_path
        )
   
        return {
            "is_new": is_new,
            "elapsed_time": "%.2f" % elapsed_time,
            "transcript": transcript,
            "file_path": file_path,
            "transcript_file_path": transcript_file_path,
        }

    def _perform_transcription(self, file_path: str) -> List[Dict[str, str]]:
        """
        Perform transcription on the given file.

        Parameters:
            file_path (str): Path to the media file.
            language (str): Language of the audio content.

        Returns:
            List[Dict[str, str]]: List of transcription segments.
        """
        # Performing the transcription using WhisperModel.
        segments, _ = self.model.transcribe(
            file_path,
            vad_filter=True,
            no_repeat_ngram_size=2,
        )

        transcript = [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in segments
        ]

        return transcript

    def is_valid_media_file(self, file_path: str) -> bool:
        """Checks if the file has a valid media extension"""
        return True if file_path.split(".")[-1] in SUPPORTED_CONVERSIONS else False

    def convert_format(self, file_path: str, output_format: str) -> str:
        """
        Convert a given media file to the specified output format.

        Parameters:
            file_path (str): Path to the input media file.
            output_format (str): Desired output format (e.g., 'wav', 'mp4').

        Returns:
            str: Path to the converted file.
        """
        logger.info("Converting file: %s to format: %s", file_path, output_format)
        input_format = file_path.split('.')[-1]

        if output_format not in SUPPORTED_CONVERSIONS.get(input_format, []):
            error_message = (
                "Conversion from %s to %s not supported." % (input_format, output_format)
            )
            logger.error(error_message)
            raise ValueError(error_message)

        output_file: str = file_path.replace(input_format, output_format)

        try:
            ffmpeg.input(file_path).output(output_file).run(capture_stdout=True, capture_stderr=True)
            logger.info("File converted successfully: %s", output_file)
        except ffmpeg.Error as e:
            logger.error("Failed to convert file due to ffmpeg error: %s", e)
            raise

        return output_file
