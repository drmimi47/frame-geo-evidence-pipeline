"""Export a PDF to the website's Reconstruction view (no video ingestion or index changes)."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def export_document(pdf: Path, output: Path, title: str, subtitle: str, width: int = 2800) -> dict:
    import fitz  # PyMuPDF: needed only when importing/replacing a PDF
    from PIL import Image

    if not title.strip():
        raise ValueError("title must not be empty")
    if not 800 <= width <= 6000:
        raise ValueError("width must be between 800 and 6000 pixels")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "title": title, "subtitle": subtitle, "pages": []}
    # Keep the editable research text when replacing the PDF.
    existing = output / "document.json"
    if existing.is_file():
        previous = json.loads(existing.read_text(encoding="utf-8"))
        if isinstance(previous.get("research"), dict):
            manifest["research"] = previous["research"]
    # Complete the export before changing the manifest; a failed PDF leaves the current view intact.
    with TemporaryDirectory(dir=output) as tmp, fitz.open(pdf) as doc:
        if doc.needs_pass or not len(doc):
            raise ValueError("PDF must be unencrypted and contain at least one page")
        stage = Path(tmp)
        for index, page in enumerate(doc):
            scale = width / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=92, method=6)
            content = buf.getvalue()
            name = f"page-{index + 1:03d}-{hashlib.sha256(content).hexdigest()[:12]}.webp"
            (stage / name).write_bytes(content)
            manifest["pages"].append({"src": name, "width": pix.width, "height": pix.height})
        for page in manifest["pages"]:
            (stage / page["src"]).replace(output / page["src"])
        draft = stage / "document.json"
        draft.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        draft.replace(output / "document.json")
    # Keep prior page assets: open tabs may still reference them. Only the manifest selects shown pages.
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--title", default="Water Level Reconstruction")
    parser.add_argument("--subtitle", default="Rozumivka Plateau — Paramonov Memorial Sign: 2000 & 2022")
    parser.add_argument("--width", type=int, default=2800, help="longest page edge in pixels (800..6000)")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] /
                        "src/image_evidence/web/documents")
    args = parser.parse_args()
    try:
        manifest = export_document(args.pdf, args.output, args.title, args.subtitle, args.width)
    except ImportError:
        parser.exit(1, 'Install the importer first: python -m pip install -e ".[document]"\n')
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not import PDF: {error}\n")
    print(f"Imported {len(manifest['pages'])} pages. Open the website and click Reconstruction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
