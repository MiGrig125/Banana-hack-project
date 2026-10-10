"""API smoke tests (no real external API calls)."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_png_bytes(size=(64, 64), color=(100, 150, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "AI Photo Studio" in r.text


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "providers" in data
    assert data["database"] is True


def test_providers(client):
    r = client.get("/api/providers")
    assert r.status_code == 200
    data = r.json()
    assert "providers" in data
    names = [p["name"] for p in data["providers"]]
    assert "mock" in names or "openai" in names


def test_generate_with_mock(client, monkeypatch):
    # Force mock provider via env is hard; call with provider=mock
    r = client.post(
        "/api/generate",
        json={"prompt": "a red cube", "provider": "mock"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["status"] == "completed"
    assert data["result_url"]


def test_enhance_local(client):
    png = _make_png_bytes()
    r = client.post(
        "/api/enhance",
        data={"mode": "auto"},
        files={"image": ("test.png", png, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["result_url"]


def test_invalid_image(client):
    r = client.post(
        "/api/enhance",
        data={"mode": "auto"},
        files={"image": ("bad.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False


def test_history(client):
    r = client.get("/api/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_result_path_traversal(client):
    r = client.get("/api/results/../../etc/passwd")
    assert r.status_code in (404, 400)
