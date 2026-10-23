"""Local speech-to-text with Indic-Transcribe Flex. Audio never leaves this machine and
is never stored: each recording lives in a temporary file only while it is transcribed."""

import io
import os
import sys
import tempfile
import threading
import wave
from array import array

from backend.config import SPEECH_MODEL, SPEECH_MODEL_DIR


SAMPLE_RATE = 16_000
MIN_AUDIO_SECONDS = 0.3
MAX_AUDIO_SECONDS = 30  # the model is trained on clips of up to 30 s
MAX_AUDIO_BYTES = 44 + MAX_AUDIO_SECONDS * SAMPLE_RATE * 2 + 1_024
MAX_TRANSCRIPT_LENGTH = 1_000  # the question box limit
SILENCE_LEVEL = 200  # peak 16-bit sample below which a recording counts as silent
WAIT_SECONDS = 30
# The first request also loads the 4.6 GB model, so allow more than one transcription.
TIMEOUT_SECONDS = 120
# Tamil: Tamil words in Tamil script, English words (PAN, Aadhaar) and numbers in Latin.
MODES = {"ta": "mixed", "en": "native"}

_model = None
# One transcription (or the first model load) at a time; others wait, then get "busy".
_lock = threading.Lock()


class AudioError(ValueError):
    """The recording is unusable; the message is safe to show the citizen."""


class SpeechUnavailableError(RuntimeError):
    pass


class SpeechBusyError(RuntimeError):
    pass


class TranscriptionError(RuntimeError):
    pass


def check_audio(data: bytes) -> float:
    """Seconds of speech in a 16 kHz mono 16-bit WAV, or AudioError."""
    try:
        with wave.open(io.BytesIO(data)) as audio:
            shape = audio.getnchannels(), audio.getsampwidth(), audio.getframerate()
            pcm = audio.readframes(MAX_AUDIO_SECONDS * SAMPLE_RATE + 1)
    except (wave.Error, EOFError) as error:
        raise AudioError("The recording is not a valid WAV file.") from error
    if shape != (1, 2, SAMPLE_RATE):
        raise AudioError("The recording must be 16 kHz mono 16-bit WAV.")
    seconds = len(pcm) / 2 / SAMPLE_RATE
    if seconds > MAX_AUDIO_SECONDS:
        raise AudioError(f"The recording is longer than {MAX_AUDIO_SECONDS} seconds.")
    samples = array("h", pcm[: len(pcm) // 2 * 2])
    if seconds < MIN_AUDIO_SECONDS or max(map(abs, samples), default=0) < SILENCE_LEVEL:
        raise AudioError("No speech was heard. Check your microphone and try again.")
    return seconds


def _load():
    global _model
    if _model is None:
        try:
            from huggingface_hub import snapshot_download

            model_dir = SPEECH_MODEL_DIR or snapshot_download(SPEECH_MODEL, local_files_only=True)
            # The model's own loading code ships inside its download (see its model card).
            if model_dir not in sys.path:
                sys.path.insert(0, model_dir)
            from indic_transcribe import IndicTranscribe

            _model = IndicTranscribe.from_pretrained(model_dir)
        except Exception as error:  # package, weights or model code missing or broken
            raise SpeechUnavailableError("The speech model is not installed.") from error
    return _model


def transcribe(data: bytes, language: str) -> str:
    """Transcript of one recording in the citizen's selected language ("ta" or "en")."""
    check_audio(data)
    if not _lock.acquire(timeout=WAIT_SECONDS):
        raise SpeechBusyError("Voice input is busy.")
    path = None
    try:
        model = _load()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as file:
            path = file.name
            file.write(data)
        text = model(path, lang=language, mode=MODES[language])
    except SpeechUnavailableError:
        raise
    except Exception as error:
        raise TranscriptionError("The recording could not be transcribed.") from error
    finally:
        _lock.release()
        if path:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    if not isinstance(text, str) or not text.strip():
        raise AudioError("No speech was recognised. Try again or type your question.")
    return text.strip()[:MAX_TRANSCRIPT_LENGTH]
