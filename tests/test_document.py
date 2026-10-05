"""Document assets use the existing static server; importing is separate from video ingestion."""

import importlib.util
import io
import json
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src/image_evidence/web"


def test_bundled_document_pages_are_complete_and_ordered():
    data = json.loads((WEB / "documents/document.json").read_text(encoding="utf-8"))
    assert data["title"] == "Water Level Reconstruction"
    assert data["subtitle"] == "Rozumivka Plateau — Paramonov Memorial Sign: 2000 & 2022"
    assert len(data["pages"]) == 10
    for index, page in enumerate(data["pages"], 1):
        assert page["src"].startswith(f"page-{index:03d}-")
        with Image.open(WEB / "documents" / page["src"]) as img:
            assert img.size == (page["width"], page["height"])
            img.verify()


def test_document_assets_are_served_without_library_records(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from image_evidence.api import create_app

    with TestClient(create_app(tmp_path / "library")) as client:
        response = client.get("/static/documents/document.json")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache"
        for page in response.json()["pages"]:
            response = client.get("/static/documents/" + page["src"])
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/webp"
            with Image.open(io.BytesIO(response.content)) as img:
                assert img.size == (page["width"], page["height"])
        assert client.get("/api/stats").json()["frames"] == 0


def test_import_preserves_page_order_aspect_and_existing_document_on_failure(tmp_path):
    fitz = pytest.importorskip("fitz")
    spec = importlib.util.spec_from_file_location("import_document", ROOT / "scripts/import_document.py")
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    pdf = tmp_path / "private-filename.pdf"
    with fitz.open() as doc:
        for width, height, color in [(400, 200, (1, 0, 0)), (200, 400, (0, 0, 1))]:
            page = doc.new_page(width=width, height=height)
            page.draw_rect(page.rect, color=color, fill=color)
        doc.save(pdf)
    output = tmp_path / "assets"
    data = importer.export_document(pdf, output, "Study", "Subtitle", width=800)
    assert "private-filename" not in json.dumps(data)
    assert [(p["width"], p["height"]) for p in data["pages"]] == [(800, 400), (400, 800)]
    for page, channel in zip(data["pages"], [0, 2]):
        with Image.open(output / page["src"]) as img:
            pixel = img.getpixel((200, 200))
            assert pixel[channel] > 240 and min(pixel) < 10
    # Replacing a PDF preserves research text edited in the manifest.
    data["research"] = {"description": "Custom research", "site": "Test site"}
    (output / "document.json").write_text(json.dumps(data), encoding="utf-8")
    updated = importer.export_document(pdf, output, "New title", "New subtitle", width=800)
    assert updated["research"] == data["research"]
    before = (output / "document.json").read_bytes()
    with pytest.raises(Exception):
        importer.export_document(tmp_path / "missing.pdf", output, "New", "", width=800)
    assert (output / "document.json").read_bytes() == before
    assert all((output / p["src"]).is_file() for p in data["pages"])
