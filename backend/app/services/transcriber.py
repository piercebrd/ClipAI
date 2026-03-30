from faster_whisper import WhisperModel

from app.config import WHISPER_MODEL

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> tuple[list[dict], str]:
    """
    Transcribe audio file using faster-whisper.

    Returns:
      - words: list of {word, start, end}
      - language: detected language code (e.g. "fr", "en")
    """
    model = _get_model()
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                })

    return words, info.language
