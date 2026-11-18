"""Photos: a phone upload becomes a JPEG in object storage, addressed by photo id."""

from __future__ import annotations

import io

import pytest
from PIL import Image


def make_image(size=(1200, 900), color=(30, 120, 90)) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def make_asset(client, product) -> dict:
    response = client.post("/api/v1/assets", json={"product_id": product["id"], "state": "stored"})
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, asset_id: str, payload: bytes, name: str = "photo.jpg"):
    return client.post(
        f"/api/v1/assets/{asset_id}/photos",
        files={"file": (name, payload, "image/jpeg")},
    )


def test_upload_then_read_full_and_thumb(client, product):
    asset = make_asset(client, product)

    response = upload(client, asset["id"], make_image())
    assert response.status_code == 201, response.text
    photo = response.json()
    assert photo["url"].endswith(photo["id"])
    assert photo["thumb_url"].endswith("?size=thumb")
    assert (photo["width"], photo["height"]) == (1200, 900)

    full = client.get(photo["url"])
    assert full.status_code == 200
    assert full.headers["content-type"] == "image/jpeg"
    assert full.headers["cache-control"].startswith("public")

    thumb = client.get(photo["thumb_url"])
    assert thumb.status_code == 200
    assert len(thumb.content) < len(full.content)

    # The photo shows up on the asset payload, so the list page needs no extra call.
    reloaded = client.get(f"/api/v1/assets/{asset['id']}").json()
    assert [p["id"] for p in reloaded["photos"]] == [photo["id"]]


def test_large_phone_photo_is_downscaled(client, product):
    asset = make_asset(client, product)
    photo = upload(client, asset["id"], make_image(size=(4000, 3000))).json()
    assert max(photo["width"], photo["height"]) == 1920
    assert photo["bytes"] < len(make_image(size=(4000, 3000)))


def test_same_bytes_twice_is_idempotent(client, product):
    asset = make_asset(client, product)
    payload = make_image()
    first = upload(client, asset["id"], payload).json()
    second = upload(client, asset["id"], payload)
    assert second.status_code == 201
    assert second.json()["id"] == first["id"]
    assert len(client.get(f"/api/v1/assets/{asset['id']}").json()["photos"]) == 1


def test_same_photo_on_two_assets_is_stored_once(client, product):
    payload = make_image(color=(90, 30, 120))
    one = make_asset(client, product)
    two = make_asset(client, product)
    a = upload(client, one["id"], payload).json()
    b = upload(client, two["id"], payload).json()
    assert a["id"] != b["id"]
    # Removing one row must not break the other: the object is shared.
    assert client.delete(f"/api/v1/photos/{a['id']}").status_code == 204
    assert client.get(b["url"]).status_code == 200


def test_delete_removes_row_and_bytes(client, product):
    asset = make_asset(client, product)
    photo = upload(client, asset["id"], make_image(color=(200, 100, 0))).json()

    assert client.delete(f"/api/v1/photos/{photo['id']}").status_code == 204
    assert client.get(photo["url"]).status_code == 404
    assert client.get(f"/api/v1/assets/{asset['id']}").json()["photos"] == []


def test_rejects_non_image_and_oversized(client, product):
    asset = make_asset(client, product)
    assert upload(client, asset["id"], b"definitely not a photo").status_code == 422

    oversized = b"\xff\xd8\xff" + b"0" * (21 * 1024 * 1024)
    assert upload(client, asset["id"], oversized).status_code == 422


def test_exif_orientation_is_applied(client, product):
    """Phones often store a sideways image plus an orientation tag."""
    image = Image.new("RGB", (800, 400), (10, 20, 30))
    exif = image.getexif()
    exif[274] = 6  # Orientation: rotate 90° CW on display
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)

    asset = make_asset(client, product)
    photo = upload(client, asset["id"], buffer.getvalue()).json()
    assert (photo["width"], photo["height"]) == (400, 800)
