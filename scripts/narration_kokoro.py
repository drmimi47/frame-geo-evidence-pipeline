"""The narration's lines (config/narration.yaml) rendered with Kokoro, one WAV per line, into the storyboard's
narration/ folder with narration.json (each line's file, length and key). Only lines whose words, pronunciations or
voice changed are rendered again. A draft voice (the user, 6 November 2026); the storyboard build lays the lines.

Kokoro (Apache-2.0) runs in its own environment, kept off the project's (torch): on a short path, since espeak-ng
caps its data path at 160 characters:
    uv venv -p 3.12 ~/.cache/kokoro-vo/env && VIRTUAL_ENV=~/.cache/kokoro-vo/env uv pip install kokoro soundfile \
        pip "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
    ~/.cache/kokoro-vo/env/bin/python -I scripts/narration_kokoro.py [--root libraries/conductive-seam] [--force]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import espeakng_loader
import numpy as np
import soundfile as sf
import yaml
from phonemizer.backend.espeak.wrapper import EspeakWrapper

EspeakWrapper.set_library(espeakng_loader.get_library_path())   # the bundled espeak-ng, for words not in Kokoro's lexicon
EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
from kokoro import KPipeline  # noqa: E402

SR = 24000          # Kokoro's own rate; the storyboard plays it as it is
GAP_S = 0.3         # between the sentences of one line, as Kokoro splits them


def marked(text: str, pronounce: dict[str, str]) -> str:
    """The line with each place name given as phonemes, Kokoro's [word](/phonemes/)."""
    for word, ph in sorted(pronounce.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"(?<![\w\[])({re.escape(word)})(?![\w\]])", rf"[\1](/{ph}/)", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=Path("config/narration.yaml"))
    ap.add_argument("--root", type=Path, default=Path("libraries/conductive-seam"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(a.config.read_text())["narration"]
    voice, pron = cfg["voice"], cfg.get("pronounce") or {}
    if voice.get("engine") != "kokoro":
        print(f"narration: the voice is {voice.get('engine')}, not kokoro", file=sys.stderr)
        return 1
    out = a.root / "storyboard" / "narration"
    out.mkdir(parents=True, exist_ok=True)
    man_path = out / "narration.json"
    old = json.loads(man_path.read_text())["lines"] if man_path.exists() else {}
    pipe = KPipeline(lang_code=voice.get("lang", "b"))
    lines, done = {}, 0
    for ln in cfg["lines"]:
        text = marked(ln["text"], pron)
        key = hashlib.sha256(json.dumps([voice, text], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        f = out / f"{ln['id']}.wav"
        if not a.force and old.get(ln["id"], {}).get("key") == key and f.exists():
            lines[ln["id"]] = old[ln["id"]]
            continue
        gap = np.zeros(int(SR * GAP_S), dtype=np.float32)
        parts = [np.asarray(audio, dtype=np.float32) for _, _, audio in
                 pipe(text, voice=voice["voice"], speed=float(voice.get("speed", 1.0)), split_pattern=r"\n+")]
        y = np.concatenate([x for p in parts for x in (p, gap)][:-1])
        sf.write(f, y, SR, subtype="PCM_24")
        lines[ln["id"]] = {"file": f.name, "seconds": round(len(y) / SR, 3), "key": key, "text": ln["text"]}
        done += 1
        print(f"  {ln['id']:<12} {len(y) / SR:5.1f} s  {ln['text'][:70]}")
    man_path.write_text(json.dumps({"voice": voice, "synthesized": "Kokoro-82M (Apache-2.0), a synthesized voice",
                                    "lines": lines}, indent=1, ensure_ascii=False))
    for f in out.glob("*.wav"):   # lines removed from the config
        if f.stem not in lines:
            f.unlink()
    print(f"narration: {done} rendered, {len(lines) - done} unchanged → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
