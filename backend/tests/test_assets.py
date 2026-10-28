"""Behaviour tests for the asset and tag rules.

These are written against the HTTP surface on purpose: the refactor behind it
can move code around as long as these keep passing.
"""

from __future__ import annotations

import re


def make_asset(client, product, **fields):
    payload = {"product_id": product["id"], "state": "stored"}
    payload.update(fields)
    response = client.post("/api/v1/assets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_product_duplicate_is_rejected(client, product):
    again = client.post(
        "/api/v1/products",
        json={"kit_name": product["kit_name"], "manufacturer": product["manufacturer"], "source": "pytest"},
    )
    assert again.status_code == 409


CODE_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{5}$")


def test_asset_gets_a_random_code_and_an_audit_row(client, product):
    asset = make_asset(client, product)
    # Crockford Base32: no I, L, O or U, so a code survives a phone keypad.
    assert CODE_RE.match(asset["code"]), asset["code"]
    assert not asset["code"].startswith("M-")
    assert asset["state"] == "stored"

    changes = client.get(f"/api/v1/assets/{asset['id']}/state-changes").json()
    assert [(c["from_state"], c["to_state"]) for c in changes] == [(None, "stored")]


def test_state_change_is_audited_and_invalid_state_rejected(client, product):
    asset = make_asset(client, product)

    moved = client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "displayed"})
    assert moved.status_code == 200
    changes = client.get(f"/api/v1/assets/{asset['id']}/state-changes").json()
    assert [(c["from_state"], c["to_state"]) for c in changes] == [(None, "stored"), ("stored", "displayed")]

    # Same state twice does not add a second audit row.
    client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "displayed"})
    assert len(client.get(f"/api/v1/assets/{asset['id']}/state-changes").json()) == 2

    assert client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "nope"}).status_code == 422


def test_bulk_create_allocates_one_code_each(client, product):
    response = client.post(
        "/api/v1/assets/bulk",
        json={"product_ids": [product["id"], product["id"]], "state": "pending"},
    )
    assert response.status_code == 201
    codes = [item["code"] for item in response.json()]
    assert len(codes) == len(set(codes)) == 2


def test_each_bag_gets_its_own_code(client, product):
    asset = make_asset(client, product)
    first = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()
    second = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "配件包 2"}).json()
    third = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "地台"}).json()

    # Stickers are independent: no suffix, no visible relation to the asset code.
    codes = [first["code"], second["code"], third["code"]]
    assert len(set(codes)) == 3
    assert asset["code"] not in codes
    assert all(CODE_RE.match(code) for code in codes)
    assert [tag["seq"] for tag in (first, second, third)] == [1, 2, 3]
    assert [tag["title"] for tag in (first, second, third)] == ["本体", "配件包 2", "地台"]


def test_bulk_tags_skips_assets_that_already_have_one(client, product):
    asset = make_asset(client, product)
    client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"})

    response = client.post("/api/v1/assets/bulk/tags", json={"asset_ids": [asset["id"]]})
    assert response.status_code == 201
    assert response.json() == []


def test_tag_title_is_validated_and_renamable(client, product):
    asset = make_asset(client, product)
    tag = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()

    assert client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "x" * 25}).status_code == 422

    renamed = client.patch(f"/api/v1/tags/{tag['id']}", json={"title": "配件包 1"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "配件包 1"
    assert client.patch(f"/api/v1/tags/{tag['id']}", json={"title": "   "}).status_code == 422


def test_printing_moves_the_stamp_and_reprint_keeps_the_code(client, product):
    asset = make_asset(client, product)
    tag = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()
    code = tag["code"]

    def in_queue(status):
        rows = client.get(f"/api/v1/tags?status={status}").json()
        return [row for row in rows if row["code"] == code]

    assert len(in_queue("open")) == 1
    client.post("/api/v1/tags/bulk/printed", json={"tag_ids": [tag["id"]]})
    assert in_queue("open") == []
    first_stamp = in_queue("printed")[0]["printed_at"]

    # Reprint the same sticker: same code, newer stamp, still one row.
    client.post(f"/api/v1/tags/{tag['id']}/printed")
    reprinted = in_queue("printed")
    assert len(reprinted) == 1
    assert reprinted[0]["printed_at"] >= first_stamp


def test_deleting_an_asset_removes_its_tags(client, product):
    asset = make_asset(client, product)
    tag = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()

    assert client.delete(f"/api/v1/assets/{asset['id']}").status_code == 200
    codes = [t["code"] for t in client.get("/api/v1/tags?status=all").json()]
    assert tag["code"] not in codes


def test_codes_are_unique_across_a_batch(client, product):
    codes = [make_asset(client, product)["code"] for _ in range(8)]
    assert len(set(codes)) == len(codes)
    assert all(CODE_RE.match(code) for code in codes)


def test_lookup_by_code_tolerates_typed_variants(client, product):
    asset = make_asset(client, product)
    tag = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()
    code = tag["code"]

    assert client.get(f"/api/v1/assets/by-code/{code}").json()["id"] == asset["id"]

    # Lower case, a stray separator, and the characters a sticker reader confuses.
    typed = code.lower().replace("0", "o").replace("1", "i")
    assert client.get(f"/api/v1/assets/by-code/{typed[:2]}-{typed[2:]}").json()["id"] == asset["id"]

    # The asset's own code resolves too.
    assert client.get(f"/api/v1/assets/by-code/{asset['code']}").json()["id"] == asset["id"]

    assert client.get("/api/v1/assets/by-code/ZZZZZ").status_code == 404


def test_qr_is_a_standalone_svg(client):
    response = client.get("/api/v1/qr", params={"data": "M-001"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    # <img src> needs the namespace; segno's inline output omits it.
    assert b'xmlns="http://www.w3.org/2000/svg"' in response.content


def test_search_finds_assets_by_name_and_code(client, product):
    asset = make_asset(client, product)
    by_name = client.get("/api/v1/assets", params={"q": product["kit_name"]}).json()
    by_code = client.get("/api/v1/assets", params={"q": asset["code"]}).json()
    assert asset["id"] in [a["id"] for a in by_name]
    assert asset["id"] in [a["id"] for a in by_code]
