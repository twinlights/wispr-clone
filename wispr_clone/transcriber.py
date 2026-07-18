"""
Local, fully offline speech-to-text using faster-whisper (CTranslate2
backend - CPU-efficient, no GPU required).

Multilingual Whisper models handle Dutch (including Flemish speech) and
English natively, with automatic language detection per utterance unless
a language is forced in config.yaml.
"""
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8",
                 language=None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def reload_model(self, model_size):
        """Reload the Whisper model with a new size."""
        self.model_size = model_size
        self.model = WhisperModel(
            model_size, device=self.device, compute_type=self.compute_type
        )

    def transcribe(self, audio, sample_rate=16000):
        if audio is None or len(audio) == 0:
            return "", None
        segments, info = self.model.transcribe(
            audio,
            language=self.language,      # None = auto-detect (NL/EN/...)
            vad_filter=True,              # trims leading/trailing silence
            beam_size=5,
        )
        text = "".join(seg.text for seg in segments).strip()
        detected_lang = info.language if info else self.language
        return text, detected_lang
