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
        json={"kit_name": product["kit_name"], "manufacturer_id": product["manufacturer_id"], "source": "pytest"},
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


def test_bulk_tags_puts_assets_back_in_the_queue(client, product):
    # No sticker yet: the bulk action issues one.
    fresh = make_asset(client, product)
    issued = client.post("/api/v1/assets/bulk/tags", json={"asset_ids": [fresh["id"]]}).json()
    assert len(issued) == 1
    assert issued[0]["printed_at"] is None

    # Printed once, then selected again: the same sticker returns to the queue.
    client.post("/api/v1/tags/bulk/printed", json={"tag_ids": [issued[0]["id"]]})
    again = client.post("/api/v1/assets/bulk/tags", json={"asset_ids": [fresh["id"]]}).json()
    assert [tag["code"] for tag in again] == [issued[0]["code"]]
    assert all(tag["printed_at"] is None for tag in again)

    open_codes = [t["code"] for t in client.get("/api/v1/tags?status=open").json()]
    assert issued[0]["code"] in open_codes


def test_bulk_tags_requeues_every_bag_of_an_asset(client, product):
    asset = make_asset(client, product)
    first = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()
    second = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "地台"}).json()
    client.post("/api/v1/tags/bulk/printed", json={"tag_ids": [first["id"], second["id"]]})

    back = client.post("/api/v1/assets/bulk/tags", json={"asset_ids": [asset["id"]]}).json()
    assert sorted(tag["code"] for tag in back) == sorted([first["code"], second["code"]])
    assert all(tag["printed_at"] is None for tag in back)


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


def test_allocator_skips_codes_already_in_use(client, product, monkeypatch):
    taken = make_asset(client, product)["code"]

    from app.services import codes

    # Pretend the generator keeps handing out a used code before finding a free one.
    sequence = iter([taken, taken, "ZZZZZ"])
    monkeypatch.setattr(codes, "new_code", lambda: next(sequence))

    created = client.post("/api/v1/assets", json={"product_id": product["id"], "state": "pending"})
    assert created.status_code == 201
    assert created.json()["code"] == "ZZZZZ"


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


def test_allowed_next_states_are_part_of_the_asset_payload(client, product):
    pending = make_asset(client, product, state="pending")
    assert pending["allowed_next_states"] == ["displayed", "keep", "sold"]

    stored = make_asset(client, product, state="stored")
    assert stored["allowed_next_states"] == ["displayed", "sold"]

    sold = client.patch(f"/api/v1/assets/{pending['id']}", json={"state": "sold"}).json()
    assert sold["state"] == "sold"
    assert sold["allowed_next_states"] == []


def test_every_non_sold_state_can_be_sold(client, product):
    for state in ("pending", "keep", "displayed", "stored"):
        asset = make_asset(client, product, state=state)
        sold = client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "sold"})
        assert sold.status_code == 200, f"{state}: {sold.text}"
        assert sold.json()["state"] == "sold"
        assert sold.json()["allowed_next_states"] == []


def test_selling_retires_tags_and_is_terminal(client, product):
    asset = make_asset(client, product, state="pending")
    tag = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()

    sold = client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "sold"})
    assert sold.status_code == 200, sold.text
    assert sold.json()["state"] == "sold"

    # The sticker row is kept, but stamped as retired.
    tags = client.get(f"/api/v1/assets/{asset['id']}").json()["tags"]
    assert len(tags) == 1
    assert tags[0]["retired_at"] is not None

    def codes(status):
        return [row["code"] for row in client.get(f"/api/v1/tags?status={status}").json()]

    assert tag["code"] not in codes("open")
    assert tag["code"] not in codes("printed")
    assert tag["code"] in codes("retired")
    assert tag["code"] in codes("all")

    # A retired sticker cannot be printed, and a sold asset cannot gain a bag.
    assert client.post(f"/api/v1/tags/{tag['id']}/printed").status_code == 409
    assert client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "地台"}).status_code == 409

    # Sold is a sink: no route may move the asset back.
    assert client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "pending"}).status_code == 409
    assert client.post(
        "/api/v1/assets/bulk/state",
        json={"asset_ids": [asset["id"]], "state": "displayed"},
    ).status_code == 409


def test_bulk_sold_from_mixed_states_retires_every_tag(client, product):
    pending = make_asset(client, product, state="pending")
    displayed = make_asset(client, product, state="displayed")
    tag_a = client.post(f"/api/v1/assets/{pending['id']}/tags", json={"title": "本体"}).json()
    tag_b = client.post(f"/api/v1/assets/{displayed['id']}/tags", json={"title": "地台"}).json()

    response = client.post(
        "/api/v1/assets/bulk/state",
        json={"asset_ids": [pending["id"], displayed["id"]], "state": "sold"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"updated": 2, "changed": 2}

    for asset_id in (pending["id"], displayed["id"]):
        body = client.get(f"/api/v1/assets/{asset_id}").json()
        assert body["state"] == "sold"
        assert all(tag["retired_at"] is not None for tag in body["tags"])

    retired_codes = [row["code"] for row in client.get("/api/v1/tags?status=retired").json()]
    assert tag_a["code"] in retired_codes
    assert tag_b["code"] in retired_codes


def test_bulk_rejects_a_transition_that_is_not_legal_for_every_asset(client, product):
    pending = make_asset(client, product, state="pending")
    displayed = make_asset(client, product, state="displayed")

    response = client.post(
        "/api/v1/assets/bulk/state",
        json={"asset_ids": [pending["id"], displayed["id"]], "state": "stored"},
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/assets/{pending['id']}").json()["state"] == "pending"
    assert client.get(f"/api/v1/assets/{displayed['id']}").json()["state"] == "displayed"


def test_sold_asset_cannot_requeue_and_bulk_print_skips_retired(client, product):
    asset = make_asset(client, product, state="stored")
    tag = client.post(f"/api/v1/assets/{asset['id']}/tags", json={"title": "本体"}).json()
    client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "sold"})

    requeue = client.post("/api/v1/assets/bulk/tags", json={"asset_ids": [asset["id"]]})
    assert requeue.status_code == 409

    printed = client.post("/api/v1/tags/bulk/printed", json={"tag_ids": [tag["id"]]})
    assert printed.status_code == 200
    assert printed.json() == {"requested": 1, "printed": 0, "retired": 1}


def test_unknown_tag_queue_status_is_rejected(client):
    assert client.get("/api/v1/tags?status=nope").status_code == 422
