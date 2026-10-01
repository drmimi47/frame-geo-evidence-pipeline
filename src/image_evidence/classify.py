"""Multi-label visual classification of frames.

The default backend is zero-shot SigLIP. A label's logit is the max over its
caption phrasings. SigLIP's raw sigmoid scores turned out to be too prompt-
sensitive to threshold directly (correct captions often score < 0.01), so labels
are scored *relatively*: softmax over all labels plus an "other" sink, and every
label with at least ``threshold`` share is kept. This stays multi-label (a frame
can be drone + urban + architecture) while frames that fit nothing fall into
the sink and get no category. Shares are relative confidences, not calibrated
probabilities. Every label's share is stored in ``category_scores``.
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Protocol

import numpy as np
from PIL import Image

from .config import OTHER_LABEL, OTHER_PROMPTS, ClassificationConfig
from .schema import CategoryLabel, Provenance

log = logging.getLogger(__name__)


class Classifier(Protocol):
    provenance: Provenance | None

    def classify(self, images: list[Image.Image]) -> list[tuple[list[CategoryLabel], dict[str, float]]]: ...


class NullClassifier:
    provenance = None

    def classify(self, images: list[Image.Image]) -> list[tuple[list[CategoryLabel], dict[str, float]]]:
        return [([], {}) for _ in images]


class SiglipClassifier:
    def __init__(self, cfg: ClassificationConfig):
        import torch
        from transformers import AutoModel, AutoProcessor
        from transformers.utils import logging as hf_logging

        hf_logging.set_verbosity_error()
        hf_logging.disable_progress_bar()

        self.cfg = cfg
        self.torch = torch
        self.device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        log.info("loading %s on %s", cfg.model, self.device)
        self.processor = AutoProcessor.from_pretrained(cfg.model)
        self.model = AutoModel.from_pretrained(cfg.model).to(self.device).eval()
        self.phrases = {**cfg.labels, OTHER_LABEL: OTHER_PROMPTS}
        self._text_cache: dict = {}
        self.provenance = Provenance(
            method="siglip_zero_shot",
            model=cfg.model,
            evidence=(
                f"softmax share over labels + '{OTHER_LABEL}' sink (max logit over caption prompts per label); "
                f"template={cfg.prompt_template!r}; T={cfg.temperature}; threshold={cfg.threshold}"
            ),
        )

    def embed(self, images: list[Image.Image]) -> np.ndarray:
        """L2-normalised SigLIP image embeddings, one row per image (float32)."""
        torch = self.torch
        rows = []
        for i in range(0, len(images), self.cfg.batch_size):
            batch = [im.convert("RGB") for im in images[i : i + self.cfg.batch_size]]
            with torch.no_grad():
                px = self.processor(images=batch, return_tensors="pt").to(self.device)
                img = self.model.get_image_features(**px)
                img = getattr(img, "pooler_output", img)
                rows.append((img / img.norm(dim=-1, keepdim=True)).float().cpu().numpy())
        return np.concatenate(rows) if rows else np.zeros((0, 0), np.float32)

    def zero_shot(self, emb: np.ndarray, groups: dict[str, list[str]]) -> list[dict[str, float]]:
        """Softmax share of each group (max logit over its captions) for each embedding row."""
        if len(emb) == 0:
            return []
        key = tuple((k, tuple(v)) for k, v in groups.items())
        if key not in self._text_cache:
            self._text_cache[key] = self._text_features(groups)
        text, owner = self._text_cache[key]
        torch = self.torch
        with torch.no_grad():
            img = torch.from_numpy(np.asarray(emb, np.float32)).to(self.device)
            logits = img @ text.T * self.model.logit_scale.exp() + self.model.logit_bias
            per = torch.full((logits.shape[0], len(groups)), float("-inf"), device=logits.device)
            per = per.scatter_reduce(1, owner.expand_as(logits), logits, "amax")
            shares = torch.softmax(per / self.cfg.temperature, dim=1).float().cpu().numpy()
        return [{k: round(float(v), 4) for k, v in zip(groups, row)} for row in shares]

    def _text_features(self, groups: dict[str, list[str]]):
        torch = self.torch
        prompts = [self.cfg.prompt_template.format(p) for k in groups for p in groups[k]]
        owner = torch.tensor([j for j, k in enumerate(groups) for _ in groups[k]], device=self.device)
        with torch.no_grad():
            tok = self.processor(text=prompts, padding="max_length", return_tensors="pt").to(self.device)
            text = self.model.get_text_features(**tok)
            text = getattr(text, "pooler_output", text)
        return (text / text.norm(dim=-1, keepdim=True)).float(), owner

    def classify(self, images: list[Image.Image]) -> list[tuple[list[CategoryLabel], dict[str, float]]]:
        return self.classify_embeddings(self.embed(images)) if images else []

    def classify_embeddings(self, emb: np.ndarray) -> list[tuple[list[CategoryLabel], dict[str, float]]]:
        out = []
        for shares in self.zero_shot(emb, self.phrases):
            scores = {lbl: v for lbl, v in shares.items() if lbl != OTHER_LABEL}
            labels = [
                CategoryLabel(label=k, confidence=v, provenance=self.provenance)
                for k, v in sorted(scores.items(), key=lambda kv: -kv[1])
                if v >= self.cfg.threshold
            ]
            out.append((labels, scores))
        return out


def classify_available() -> bool:
    return all(importlib.util.find_spec(m) for m in ("torch", "transformers"))


def make_classifier(cfg: ClassificationConfig) -> Classifier:
    if cfg.backend == "none":
        return NullClassifier()
    if cfg.backend == "auto" and not classify_available():
        log.warning("classification disabled: install the [classify] extra for SigLIP categories")
        return NullClassifier()
    return SiglipClassifier(cfg)


def subject_score(scores: dict[str, float], cfg: ClassificationConfig) -> float:
    """Share of preferred subjects minus share of unwanted ones, in [-1, 1]."""
    return sum(scores.get(k, 0.0) for k in cfg.prefer) - sum(scores.get(k, 0.0) for k in cfg.avoid)


def choose(times: list[float], scores: list[dict[str, float]], cfg: ClassificationConfig, limit: int) -> list[int]:
    """Indices of the frames to keep: those with subject_score >= min_subject, at most ``limit``.

    When more qualify than fit, the timeline is split into ``limit`` equal slots and the best frame in
    each slot is kept (so one long scenic sequence doesn't crowd out the rest); leftover places go
    to the best remaining frames. Returned in time order.
    """
    ranked = [(subject_score(s, cfg), i) for i, s in enumerate(scores)]
    ok = [(sc, i) for sc, i in ranked if sc >= cfg.min_subject]
    if len(ok) <= limit:
        return sorted(i for _, i in ok)
    t0, t1 = min(times[i] for _, i in ok), max(times[i] for _, i in ok)
    width = (t1 - t0) / limit or 1.0
    best: dict[int, tuple[float, int]] = {}
    for sc, i in ok:
        slot = min(limit - 1, int((times[i] - t0) / width))
        if slot not in best or sc > best[slot][0]:
            best[slot] = (sc, i)
    picked = {i for _, i in best.values()}
    rest = sorted(((sc, i) for sc, i in ok if i not in picked), reverse=True)
    picked.update(i for _, i in rest[: limit - len(picked)])
    return sorted(picked)


# --------------------------------------------------------------------------
# Video-level text signal (title/tags/description). Kept separate from visual labels.
# --------------------------------------------------------------------------

TEXT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "drone": ("drone", "dji", "fpv", "mavic"),
    "aerial": ("aerial", "bird's eye", "birds eye", "from above"),
    "ruins": ("ruins", "destroyed", "destruction", "rubble", "bombed"),
    "reconstruction": ("reconstruction", "rebuild", "rebuilding", "restoration"),
    "urban": ("city", "downtown", "skyline", "urban"),
    "street": ("street", "walking tour", "walk through"),
    "landscape": ("landscape", "mountain", "countryside", "nature"),
    "architecture": ("architecture", "cathedral", "building", "church"),
    "infrastructure": ("bridge", "railway", "highway", "dam", "power line"),
    "industrial": ("factory", "industrial", "plant", "steel", "refinery"),
}


def text_categories(title: str, tags: tuple[str, ...], description: str) -> list[CategoryLabel]:
    fields = {"title": title.lower(), "tags": " | ".join(tags).lower(), "description": description.lower()}
    weights = {"title": 0.6, "tags": 0.5, "description": 0.3}
    out = []
    for label, kws in TEXT_KEYWORDS.items():
        hits = [(f, kw) for f, text in fields.items() for kw in kws if kw in text]
        if hits:
            best = max(hits, key=lambda h: weights[h[0]])
            out.append(CategoryLabel(
                label=label,
                confidence=weights[best[0]],
                provenance=Provenance(method="video_text_keywords", evidence=f"'{best[1]}' in {best[0]}"),
            ))
    return out
