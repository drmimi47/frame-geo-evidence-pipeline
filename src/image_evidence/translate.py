"""Local machine translation of subtitles into English (Helsinki-NLP opus-mt, offline once downloaded).

A reading aid only: translation mangles place names ("Нікополь" -> "Nicopolis"), so place matching always
reads the original text. Needs the [classify] extra (torch, transformers, sentencepiece).
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

MODELS = {"uk": "Helsinki-NLP/opus-mt-uk-en", "ru": "Helsinki-NLP/opus-mt-ru-en"}
BATCH = 16
_loaded: dict[str, tuple] = {}


def available(lang: str) -> bool:
    if lang not in MODELS:
        return False
    try:
        import sentencepiece  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


def model_name(lang: str) -> str:
    return MODELS[lang]


PIECE_WORDS = 18  # opus-mt drops whole sentences from long inputs, so it gets one sentence at a time


def _pieces(text: str) -> list[str]:
    """A paragraph as sentences; a long unpunctuated run (auto captions) as chunks of about PIECE_WORDS words."""
    out = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        words = sentence.split()
        n = max(1, round(len(words) / PIECE_WORDS))
        size = -(-len(words) // n)
        out += [" ".join(words[i : i + size]) for i in range(0, len(words), size)]
    return [p for p in out if p]


def to_english(texts: list[str], lang: str) -> list[str]:
    """Translate each text (a subtitle paragraph) from ``lang`` into English, piece by piece."""
    pieces = [_pieces(t) for t in texts]
    flat = _translate([p for ps in pieces for p in ps], lang)
    out, k = [], 0
    for ps in pieces:
        out.append(" ".join(flat[k : k + len(ps)]))
        k += len(ps)
    return out


def _translate(texts: list[str], lang: str) -> list[str]:
    import torch
    from transformers import MarianMTModel, MarianTokenizer

    if lang not in _loaded:
        name = MODELS[lang]
        log.info("loading translation model %s", name)
        device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        _loaded[lang] = (MarianTokenizer.from_pretrained(name), MarianMTModel.from_pretrained(name).eval().to(device))
    tok, model = _loaded[lang]
    out: list[str] = []
    for i in range(0, len(texts), BATCH):
        batch = tok(texts[i : i + BATCH], return_tensors="pt", padding=True, truncation=True, max_length=512).to(model.device)
        n = int(batch["input_ids"].shape[1])
        with torch.no_grad():  # output about as long as the input: stops a model stuck repeating itself
            ids = model.generate(**batch, max_length=None, max_new_tokens=int(n * 1.5) + 10, no_repeat_ngram_size=4)
        out += tok.batch_decode(ids, skip_special_tokens=True)
    return out
