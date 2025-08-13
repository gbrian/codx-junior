# [[{"id": "5402e4fc-8572-4c5b-91a3-a0fbd00fdf88", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/whisper/audio_manager.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Extract voices", "description": "1. The user provided an example script for voice separation, transcription, and diarization using various audio processing libraries.\n2. The request was to integrate this functionality into an `AudioManager` class to manage audio tasks.\n3. Instructions included isolating vocals using Demucs and performing transcription with WhisperModel.\n4. A NeMo model was suggested for diarization, with additional steps for handling audio and timestamps.\n5. A list of new libraries required for these functionalities was provided, including Demucs, PyTorch, Torchaudio, NeMo, and others.", "created_at": "2025-08-12 16:31:23.940972", "updated_at": "2025-08-13T04:32:02.446742", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Whisper", "column": "To Do", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Whisper/To Do/extract-voices.5402e4fc-8572-4c5b-91a3-a0fbd00fdf88.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "1722f79d-e00e-422a-8b79-ec4947d8137a", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-12 16:31:23.939005", "updated_at": "2025-08-12 16:31:23.939032", "images": [], "files": ["/shared/codx-junior/api/codx/junior/whisper/audio_manager.py"], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
@file://audio_manager.py
We must try to separate voices in the audio.
Below there's an example, intregate it with AudioManager. 
````
import argparse
import logging
import os
import re


import faster_whisper
import torch
import torchaudio


from ctc_forced_aligner import (
    generate_emissions,
    get_alignments,
    get_spans,
    load_alignment_model,
    postprocess_results,
    preprocess_text,
)
from deepmultilingualpunctuation import PunctuationModel
from nemo.collections.asr.models.msdd_models import NeuralDiarizer


from helpers import (
    cleanup,
    create_config,
    find_numeral_symbol_tokens,
    get_realigned_ws_mapping_with_punctuation,
    get_sentences_speaker_mapping,
    get_speaker_aware_transcript,
    get_words_speaker_mapping,
    langs_to_iso,
    process_language_arg,
    punct_model_langs,
    whisper_langs,
    write_srt,
)


mtypes = {"cpu": "int8", "cuda": "float16"}


pid = os.getpid()
temp_outputs_dir = f"temp_outputs_{pid}"


# Initialize parser
parser = argparse.ArgumentParser()
parser.add_argument(
    "-a", "--audio", help="name of the target audio file", required=True
)
parser.add_argument(
    "--no-stem",
    action="store_false",
    dest="stemming",
    default=True,
    help="Disables source separation."
    "This helps with long files that don't contain a lot of music.",
)


parser.add_argument(
    "--suppress_numerals",
    action="store_true",
    dest="suppress_numerals",
    default=False,
    help="Suppresses Numerical Digits."
    "This helps the diarization accuracy but converts all digits into written text.",
)


parser.add_argument(
    "--whisper-model",
    dest="model_name",
    default="medium.en",
    help="name of the Whisper model to use",
)


parser.add_argument(
    "--batch-size",
    type=int,
    dest="batch_size",
    default=8,
    help="Batch size for batched inference, reduce if you run out of memory, "
    "set to 0 for original whisper longform inference",
)


parser.add_argument(
    "--language",
    type=str,
    default=None,
    choices=whisper_langs,
    help="Language spoken in the audio, specify None to perform language detection",
)


parser.add_argument(
    "--device",
    dest="device",
    default="cuda" if torch.cuda.is_available() else "cpu",
    help="if you have a GPU use 'cuda', otherwise 'cpu'",
)


args = parser.parse_args()
language = process_language_arg(args.language, args.model_name)


if args.stemming:
    # Isolate vocals from the rest of the audio


    return_code = os.system(
        f'python -m demucs.separate -n htdemucs --two-stems=vocals "{args.audio}" -o "{temp_outputs_dir}" --device "{args.device}"'
    )


    if return_code != 0:
        logging.warning(
            "Source splitting failed, using original audio file. "
            "Use --no-stem argument to disable it."
        )
        vocal_target = args.audio
    else:
        vocal_target = os.path.join(
            temp_outputs_dir,
            "htdemucs",
            os.path.splitext(os.path.basename(args.audio))[0],
            "vocals.wav",
        )
else:
    vocal_target = args.audio




# Transcribe the audio file


whisper_model = faster_whisper.WhisperModel(
    args.model_name, device=args.device, compute_type=mtypes[args.device]
)
whisper_pipeline = faster_whisper.BatchedInferencePipeline(whisper_model)
audio_waveform = faster_whisper.decode_audio(vocal_target)
suppress_tokens = (
    find_numeral_symbol_tokens(whisper_model.hf_tokenizer)
    if args.suppress_numerals
    else [-1]
)


if args.batch_size > 0:
    transcript_segments, info = whisper_pipeline.transcribe(
        audio_waveform,
        language,
        suppress_tokens=suppress_tokens,
        batch_size=args.batch_size,
    )
else:
    transcript_segments, info = whisper_model.transcribe(
        audio_waveform,
        language,
        suppress_tokens=suppress_tokens,
        vad_filter=True,
    )


full_transcript = "".join(segment.text for segment in transcript_segments)


# clear gpu vram
del whisper_model, whisper_pipeline
torch.cuda.empty_cache()


# Forced Alignment
alignment_model, alignment_tokenizer = load_alignment_model(
    args.device,
    dtype=torch.float16 if args.device == "cuda" else torch.float32,
)


emissions, stride = generate_emissions(
    alignment_model,
    torch.from_numpy(audio_waveform)
    .to(alignment_model.dtype)
    .to(alignment_model.device),
    batch_size=args.batch_size,
)


del alignment_model
torch.cuda.empty_cache()


tokens_starred, text_starred = preprocess_text(
    full_transcript,
    romanize=True,
    language=langs_to_iso[info.language],
)


segments, scores, blank_token = get_alignments(
    emissions,
    tokens_starred,
    alignment_tokenizer,
)


spans = get_spans(tokens_starred, segments, blank_token)


word_timestamps = postprocess_results(text_starred, spans, stride, scores)




# convert audio to mono for NeMo combatibility
ROOT = os.getcwd()
temp_path = os.path.join(ROOT, temp_outputs_dir)
os.makedirs(temp_path, exist_ok=True)
torchaudio.save(
    os.path.join(temp_path, "mono_file.wav"),
    torch.from_numpy(audio_waveform).unsqueeze(0).float(),
    16000,
    channels_first=True,
)




# Initialize NeMo MSDD diarization model
msdd_model = NeuralDiarizer(cfg=create_config(temp_path)).to(args.device)
msdd_model.diarize()


del msdd_model
torch.cuda.empty_cache()


# Reading timestamps <> Speaker Labels mapping




speaker_ts = []
with open(os.path.join(temp_path, "pred_rttms", "mono_file.rttm"), "r") as f:
    lines = f.readlines()
    for line in lines:
        line_list = line.split(" ")
        s = int(float(line_list[5]) * 1000)
        e = s + int(float(line_list[8]) * 1000)
        speaker_ts.append([s, e, int(line_list[11].split("_")[-1])])


wsm = get_words_speaker_mapping(word_timestamps, speaker_ts, "start")


if info.language in punct_model_langs:
    # restoring punctuation in the transcript to help realign the sentences
    punct_model = PunctuationModel(model="kredor/punctuate-all")


    words_list = list(map(lambda x: x["word"], wsm))


    labled_words = punct_model.predict(words_list, chunk_size=230)


    ending_puncts = ".?!"
    model_puncts = ".,;:!?"


    # We don't want to punctuate U.S.A. with a period. Right?
    is_acronym = lambda x: re.fullmatch(r"\b(?:[a-zA-Z]\.){2,}", x)


    for word_dict, labeled_tuple in zip(wsm, labled_words):
        word = word_dict["word"]
        if (
            word
            and labeled_tuple[1] in ending_puncts
            and (word[-1] not in model_puncts or is_acronym(word))
        ):
            word += labeled_tuple[1]
            if word.endswith(".."):
                word = word.rstrip(".")
            word_dict["word"] = word


else:
    logging.warning(
        f"Punctuation restoration is not available for {info.language} language."
        " Using the original punctuation."
    )


wsm = get_realigned_ws_mapping_with_punctuation(wsm)
ssm = get_sentences_speaker_mapping(wsm, speaker_ts)


with open(f"{os.path.splitext(args.audio)[0]}.txt", "w", encoding="utf-8-sig") as f:
    get_speaker_aware_transcript(ssm, f)


with open(f"{os.path.splitext(args.audio)[0]}.srt", "w", encoding="utf-8-sig") as srt:
    write_srt(ssm, srt)


cleanup(temp_path)
```
## [[{"doc_id": "edadfe9b-a666-4411-ade6-9ee9703bed33", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-08-12 16:31:23.939005", "updated_at": "2025-08-12 16:31:23.939032", "images": [], "files": [], "meta_data": {"time_taken": 13.554882526397705, "first_chunk_time_taken": 0.0002944469451904297, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
To integrate the voice separation example with the `AudioManager` class, we will need to include some of the essential methods and configurations present in the example script into the `AudioManager`. Here's how the integration can be done:

1. Add necessary configurations and initializations.
2. Add the functionality to separate voices using Demucs.
3. Integrate the transcription and diarization functionality.

Here's how you can integrate these features into the `AudioManager`:

```python
import logging
import time
from typing import List, Dict
from faster_whisper import WhisperModel
from tempfile import NamedTemporaryFile
import ffmpeg
import os
import json
import torchaudio
import torch
from nemo.collections.asr.models.msdd_models import NeuralDiarizer

# Add necessary imports
from deepmultilingualpunctuation import PunctuationModel
from ctc_forced_aligner import (
    generate_emissions,
    get_alignments,
    get_spans,
    load_alignment_model,
    postprocess_results,
    preprocess_text,
)
from helpers import (
    cleanup,
    create_config,
    find_numeral_symbol_tokens,
    get_realigned_ws_mapping_with_punctuation,
    get_sentences_speaker_mapping,
    get_speaker_aware_transcript,
    get_words_speaker_mapping,
    langs_to_iso,
    process_language_arg,
    punct_model_langs,
    whisper_langs,
    write_srt,
)

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

    def transcribe_and_diarize(self, file_path: str) -> Dict[str, str or List[Dict[str, str]]]:
        """
        Separate voices, transcribe and perform diarization on the given file.
        
        Parameters:
            file_path (str): Path to the local file.

        Returns:
            Dict[str, str or List[Dict[str, str]]]: Transcription results including elapsed time, transcript, and diarization information.
        """
        # Isolate vocals from the rest of the audio
        temp_outputs_dir = f"temp_outputs"
        return_code = os.system(
            f'python -m demucs.separate -n htdemucs --two-stems=vocals "{file_path}" -o "{temp_outputs_dir}"'
        )

        if return_code != 0:
            logger.warning(
                "Source splitting failed, using original audio file."
            )
            vocal_target = file_path
        else:
            vocal_target = os.path.join(
                temp_outputs_dir,
                "htdemucs",
                os.path.splitext(os.path.basename(file_path))[0],
                "vocals.wav",
            )
        
        # Now perform transcription using the audio with separated vocals
        logger.info("Starting transcription for file (with separated vocals): %s", vocal_target)
        start_time = time.perf_counter()
        transcript = self._perform_transcription(vocal_target)
        elapsed_time: float = time.perf_counter() - start_time

        logger.info(
            "Transcription completed in %.2f seconds for file: %s", elapsed_time, vocal_target
        )

        # Diarization: convert audio to mono for NeMo compatibility
        torchaudio.save(
            os.path.join(temp_outputs_dir, "mono_file.wav"),
            torchaudio.load(vocal_target)[0].unsqueeze(0).float(),
            16000,
            channels_first=True,
        )

        # Initialize NeMo MSDD diarization model
        msdd_model = NeuralDiarizer(cfg=create_config(temp_outputs_dir)).to("cuda" if torch.cuda.is_available() else "cpu")
        msdd_model.diarize()
        
        # Read timestamps <> Speaker Labels mapping
        speaker_ts = []
        with open(os.path.join(temp_outputs_dir, "pred_rttms", "mono_file.rttm"), "r") as f:
            lines = f.readlines()
            for line in lines:
                line_list = line.split(" ")
                s = int(float(line_list[5]) * 1000)
                e = s + int(float(line_list[8]) * 1000)
                speaker_ts.append([s, e, int(line_list[11].split("_")[-1])])
        
        # Cleanup
        cleanup(temp_outputs_dir)

        return {
            "elapsed_time": "%.2f" % elapsed_time,
            "transcript": transcript,
            "file_path": file_path,
            "speaker_timestamps": speaker_ts
        }

    # Existing methods...

    def _perform_transcription(self, file_path: str) -> List[Dict[str, str]]:
        """
        Perform transcription on the given file.

        Parameters:
            file_path (str): Path to the media file.

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
```

This integrated approach utilizes both Demucs for voice separation and NeMo for speaker diarization. This code abstracts the source separation, transcription, and diarization steps into a single method `transcribe_and_diarize`, which can be used to process audio files accordingly.
## [[{"doc_id": "7cae09ee-3328-49b3-a495-1ef05605dec3", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-12 16:31:23.939005", "updated_at": "2025-08-12 16:31:23.939032", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Give me a list of new libs we need to install
## [[{"doc_id": "207c077a-9820-4333-9a2b-4296c9f5b753", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-08-12 16:31:23.939005", "updated_at": "2025-08-12 16:31:23.939032", "images": [], "files": [], "meta_data": {"time_taken": 10.217733383178711, "first_chunk_time_taken": 0.00022745132446289062, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
To integrate the provided functionality for voice separation, transcription, and diarization into the `AudioManager` class as described, you will need the following new Python libraries:

1. **Demucs**: For source separation (voice isolation).
   - Install via: `pip install demucs`

2. **Faster Whisper**: For transcription, which you already have, but let's confirm it:
   - Install via: `pip install faster-whisper`

3. **Pytorch**: As a dependency for models like Whisper and NeMo.
   - It's typically installed with GPU support if needed, e.g.,
   - Install via: `pip install torch` (or follow specific installation instructions for GPUs).

4. **TorchAudio**: For handling audio data with Pytorch.
   - Install via: `pip install torchaudio`

5. **NeMo**: For neural diarization.
   - Install using: `pip install nemo_toolkit[all]`

6. **CTC-Forced-Aligner**: For forced alignment.
   - No direct pip installation command specified. Ensure to follow specific installation or setup instructions if needed.

7. **DeepMultilingualPunctuation**: For punctuation restoration.
   - Install via: `pip install deepmultilingualpunctuation`

If you do not already have these installed, these would be the additional dependencies needed to perform the tasks described in the updated code. Make sure to check the specific installation requirements for each library, especially for Pytorch, to ensure compatibility with your hardware (e.g., CPU vs. GPU support).