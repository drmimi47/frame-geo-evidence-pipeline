"""On-screen text (OCR) for frames, via Apple Vision on macOS (the [ocr] extra).

Burned-in captions, street signs and titles ("Часів Яр 2021", "Проспект Миру") are frame-level
evidence of place and time. Returns None when no OCR engine is available, so callers can skip.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from .schema import OcrLine, OcrResult, Provenance

log = logging.getLogger(__name__)
LANGUAGES = ["uk-UA", "ru-RU", "en-US"]


def available() -> bool:
    return importlib.util.find_spec("Vision") is not None


def read_text(path: Path) -> OcrResult | None:
    if not available():
        return None
    import Vision
    from Foundation import NSURL

    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(LANGUAGES)
    req.setUsesLanguageCorrection_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(str(path)), None)
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        log.warning("OCR failed for %s: %s", path, err)
        return None
    lines = []
    for r in req.results() or []:
        c = r.topCandidates_(1)[0]
        b = r.boundingBox()  # normalised, origin bottom-left
        lines.append(OcrLine(
            text=str(c.string()),
            confidence=round(float(c.confidence()), 2),
            box=(round(b.origin.x, 4), round(1 - b.origin.y - b.size.height, 4), round(b.size.width, 4), round(b.size.height, 4)),
        ))
    return OcrResult(lines=lines, provenance=Provenance(method="apple_vision_ocr", model="VNRecognizeTextRequest",
                                                        evidence=f"accurate, languages {LANGUAGES}"))
