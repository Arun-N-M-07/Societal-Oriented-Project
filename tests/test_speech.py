import importlib.util
import io
import math
import os
import time
import unittest
import wave
from unittest.mock import patch

from db_support import make_client

from backend import speech


def wav(seconds=1.0, rate=16_000, channels=1, loud=True):
    samples = int(seconds * rate)
    frames = b"".join(
        int(8_000 * math.sin(i / 8) if loud else 0).to_bytes(2, "little", signed=True) for i in range(samples)
    ) * channels
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(frames)
    return buffer.getvalue()


class FakeModel:
    def __init__(self, text="Passport renew pannanum"):
        self.text, self.calls = text, []

    def __call__(self, path, lang, mode):
        with open(path, "rb") as file:
            self.calls.append((path, file.read(), lang, mode))
        if isinstance(self.text, Exception):
            raise self.text
        return self.text


class CheckAudioTest(unittest.TestCase):
    def test_accepts_16_khz_mono_speech(self):
        self.assertAlmostEqual(speech.check_audio(wav(2)), 2.0)

    def test_rejects_unusable_recordings(self):
        for data, reason in [
            (b"not audio", "not a valid WAV"),
            (b"RIFF\x00\x00\x00\x00WAVE", "not a valid WAV"),
            (wav(rate=44_100), "16 kHz mono"),
            (wav(channels=2), "16 kHz mono"),
            (wav(0.1), "No speech"),
            (wav(loud=False), "No speech"),
            (wav(31), "longer than 30 seconds"),
        ]:
            with self.subTest(reason), self.assertRaisesRegex(speech.AudioError, reason):
                speech.check_audio(data)


class TranscribeTest(unittest.TestCase):
    def setUp(self):
        self.model = FakeModel()
        model = patch("backend.speech._model", self.model)
        model.start()
        self.addCleanup(model.stop)

    def test_transcribes_in_the_selected_language_and_deletes_the_audio(self):
        audio = wav()
        self.assertEqual(speech.transcribe(audio, "ta"), "Passport renew pannanum")
        self.assertEqual(speech.transcribe(audio, "en"), "Passport renew pannanum")

        (path, sent, lang, mode), (_, _, lang2, mode2) = self.model.calls
        self.assertEqual((sent, lang, mode, lang2, mode2), (audio, "ta", "mixed", "en", "native"))
        self.assertFalse(os.path.exists(path))

    def test_deletes_the_audio_and_frees_the_model_when_transcription_fails(self):
        self.model.text = RuntimeError("decoder crashed")
        with self.assertRaises(speech.TranscriptionError):
            speech.transcribe(wav(), "ta")
        self.assertFalse(os.path.exists(self.model.calls[0][0]))
        self.assertFalse(speech._lock.locked())

    def test_empty_transcript_is_an_audio_error(self):
        self.model.text = "  "
        with self.assertRaisesRegex(speech.AudioError, "No speech was recognised"):
            speech.transcribe(wav(), "ta")

    def test_reports_busy_instead_of_queueing_forever(self):
        with patch("backend.speech.WAIT_SECONDS", 0.01), speech._lock:
            with self.assertRaises(speech.SpeechBusyError):
                speech.transcribe(wav(), "ta")
        self.assertEqual(self.model.calls, [])

    def test_missing_model_is_unavailable(self):
        with patch("backend.speech._model", None), patch("backend.speech.SPEECH_MODEL_DIR", "/nonexistent-model"):
            with self.assertRaises(speech.SpeechUnavailableError):
                speech.transcribe(wav(), "ta")
        self.assertFalse(speech._lock.locked())

    @unittest.skipUnless(importlib.util.find_spec("huggingface_hub"), "speech requirements not installed")
    def test_weights_are_only_read_from_the_local_cache(self):
        with patch("backend.speech._model", None), patch(
            "huggingface_hub.snapshot_download", side_effect=OSError("not in cache")
        ) as download, self.assertRaises(speech.SpeechUnavailableError):
            speech.transcribe(wav(), "ta")
        self.assertTrue(download.call_args.kwargs["local_files_only"])


class TranscribeApiTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client(admin=False)

    def post(self, data, language="ta", content_type="audio/wav"):
        return self.client.post(
            f"/api/speech/transcribe?language={language}", content=data, headers={"Content-Type": content_type}
        )

    def test_returns_the_transcript(self):
        with patch("backend.speech._model", FakeModel("PAN card epdi apply panradhu?")):
            response = self.post(wav())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"text": "PAN card epdi apply panradhu?", "language": "ta"})

    def test_rejects_bad_requests_with_safe_messages(self):
        with patch("backend.speech._model", FakeModel()) as model:
            self.assertEqual(self.post(wav(), content_type="application/json").status_code, 415)
            self.assertEqual(self.post(wav(), language="hi").status_code, 422)
            self.assertEqual(self.post(b"x" * (speech.MAX_AUDIO_BYTES + 1)).status_code, 413)
            response = self.post(b"not audio")
            self.assertEqual((response.status_code, response.json()["detail"]), (422, "The recording is not a valid WAV file."))
            self.assertEqual(model.calls, [])

    def test_times_out_slow_transcriptions(self):
        with patch("backend.routes.TIMEOUT_SECONDS", 0.05), patch("backend.routes.transcribe", side_effect=lambda *_: time.sleep(0.5)):
            response = self.post(wav())
        self.assertEqual(response.status_code, 504)
        self.assertIn("took too long", response.json()["detail"])

    def test_reports_model_failures_without_internal_details(self):
        cases = [
            (speech.SpeechUnavailableError("missing weights at /secret/path"), 503, "not set up"),
            (speech.SpeechBusyError("busy"), 503, "busy"),
            (speech.TranscriptionError("CUDA error"), 502, "could not be transcribed"),
        ]
        for error, status, detail in cases:
            with self.subTest(status=status), patch("backend.routes.transcribe", side_effect=error):
                response = self.post(wav())
            self.assertEqual(response.status_code, status)
            self.assertIn(detail, response.json()["detail"])
            self.assertNotIn("/secret/path", response.text)
            self.assertNotIn("CUDA", response.text)


if __name__ == "__main__":
    unittest.main()
