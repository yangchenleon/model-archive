"""Behaviour tests for collections: human-defined scope, derived progress."""

from __future__ import annotations

from uuid import uuid4


def make_manufacturer(client, name):
    rows = client.get("/api/v1/manufacturers", params={"q": name}).json()
    for row in rows:
        if row["name"] == name:
            return row
    response = client.post("/api/v1/manufacturers", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def make_line(client, manufacturer_id, name):
    rows = client.get("/api/v1/product-lines", params={"manufacturer_id": manufacturer_id}).json()
    for row in rows:
        if row["name"] == name:
            return row
    response = client.post(
        "/api/v1/product-lines",
        json={"manufacturer_id": manufacturer_id, "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_product(client, name, manufacturer="测试厂", line="RG", code=None):
    maker = make_manufacturer(client, manufacturer)
    target_line = make_line(client, maker["id"], line) if line else None
    payload = {
        "kit_name": name,
        "manufacturer_id": maker["id"],
        "source": "pytest",
    }
    if target_line is not None:
        payload["product_line_id"] = target_line["id"]
    if code:
        payload["product_code"] = code
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def make_collection(client, title="测试收藏集", **fields):
    response = client.post("/api/v1/collections", json={"title": title, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def add_items(client, collection_id, products):
    response = client.post(
        f"/api/v1/collections/{collection_id}/items/bulk",
        json={"product_ids": [product["id"] for product in products]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def make_asset(client, product, state="pending"):
    response = client.post(
        "/api/v1/assets",
        json={"product_id": product["id"], "state": state},
    )
    assert response.status_code == 201, response.text
    return response.json()


def get_collection(client, collection_id):
    response = client.get(f"/api/v1/collections/{collection_id}")
    assert response.status_code == 200, response.text
    return response.json()


def test_collection_crud_and_empty_stats(client):
    collection = make_collection(client, "RG 扎古全制霸", description="只收万代 RG 扎古")
    assert collection["status"] == "active"
    assert collection["stats"] == {
        "total": 0,
        "owned": 0,
        "built": 0,
        "unbuilt": 0,
        "missing": 0,
        "sold_only": 0,
        "extra_copies": 0,
        "percent": 0,
        "completed": False,
    }

    renamed = client.patch(
        f"/api/v1/collections/{collection['id']}",
        json={"title": "RG 扎古", "status": "planning", "description": "先列范围"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "RG 扎古"
    assert renamed.json()["status"] == "planning"

    assert client.post("/api/v1/collections", json={"title": "RG 扎古"}).status_code == 409
    assert client.post("/api/v1/collections", json={"title": "   "}).status_code == 422
    assert client.post("/api/v1/collections", json={"title": "x", "status": "nope"}).status_code == 422

    other = make_collection(client, "另一个收藏集")
    assert client.patch(
        f"/api/v1/collections/{other['id']}", json={"title": "RG 扎古"}
    ).status_code == 409

    deleted = client.delete(f"/api/v1/collections/{collection['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["items"] == 0
    assert client.get(f"/api/v1/collections/{collection['id']}").status_code == 404


def test_targets_must_be_existing_products_and_duplicates_are_skipped(client):
    collection = make_collection(client)
    first = make_product(client, "夏亚专用扎古II", code="02")
    second = make_product(client, "量产型扎古II", code="04")

    assert client.post(
        f"/api/v1/collections/{collection['id']}/items",
        json={"product_id": str(uuid4())},
    ).status_code == 404

    added = client.post(
        f"/api/v1/collections/{collection['id']}/items",
        json={"product_id": first["id"]},
    )
    assert added.status_code == 201
    assert added.json()["name"] == "夏亚专用扎古II"
    assert added.json()["owned"] is False

    assert client.post(
        f"/api/v1/collections/{collection['id']}/items",
        json={"product_id": first["id"]},
    ).status_code == 409

    bulk = add_items(client, collection["id"], [first, second])
    assert bulk == {"added": 1, "skipped": 1}

    # A bad id fails the whole batch: the second product is not inserted.
    before = get_collection(client, collection["id"])["stats"]["total"]
    bad = client.post(
        f"/api/v1/collections/{collection['id']}/items/bulk",
        json={"product_ids": [str(uuid4())]},
    )
    assert bad.status_code == 404
    assert get_collection(client, collection["id"])["stats"]["total"] == before

    listed = client.get(f"/api/v1/collections/{collection['id']}/items").json()
    assert listed["total"] == 2
    assert [item["product_code"] for item in listed["items"]] == ["02", "04"]


def test_progress_is_derived_from_non_sold_assets_and_counts_once(client):
    collection = make_collection(client, "RG 扎古全制霸")
    first = make_product(client, "夏亚专用扎古II", code="02")
    second = make_product(client, "量产型扎古II", code="04")
    third = make_product(client, "强尼莱登专用扎古II", code="26")
    add_items(client, collection["id"], [first, second, third])

    stats = get_collection(client, collection["id"])["stats"]
    assert stats["total"] == 3
    assert stats["owned"] == 0
    assert stats["missing"] == 3
    assert stats["percent"] == 0

    make_asset(client, first, "pending")
    stats = get_collection(client, collection["id"])["stats"]
    assert (stats["owned"], stats["built"], stats["unbuilt"], stats["missing"]) == (1, 0, 1, 2)
    assert stats["percent"] == 33.3

    make_asset(client, second, "displayed")
    stats = get_collection(client, collection["id"])["stats"]
    assert (stats["owned"], stats["built"], stats["unbuilt"], stats["missing"]) == (2, 1, 1, 1)
    assert stats["percent"] == 66.7

    # A second copy is a duplicate, not extra progress.
    make_asset(client, first, "pending")
    stats = get_collection(client, collection["id"])["stats"]
    assert (stats["owned"], stats["extra_copies"]) == (2, 1)

    # Selling both copies of the first product removes it from owned.
    first_assets = [
        asset for asset in client.get("/api/v1/assets").json()
        if asset["product"]["id"] == first["id"]
    ]
    for asset in first_assets:
        assert client.patch(
            f"/api/v1/assets/{asset['id']}", json={"state": "sold"}
        ).status_code == 200

    stats = get_collection(client, collection["id"])["stats"]
    assert (stats["owned"], stats["built"], stats["unbuilt"], stats["missing"]) == (1, 1, 0, 2)
    assert stats["sold_only"] == 1
    assert stats["extra_copies"] == 0
    assert stats["percent"] == 33.3

    owned = client.get(f"/api/v1/collections/{collection['id']}/items?state=owned").json()
    missing = client.get(f"/api/v1/collections/{collection['id']}/items?state=missing").json()
    assert owned["total"] == 1
    assert owned["items"][0]["product_code"] == "04"
    assert owned["items"][0]["built"] is True
    assert missing["total"] == 2


def test_completed_only_when_every_target_is_owned(client):
    product = make_product(client, "唯一目标")
    collection = make_collection(client)
    add_items(client, collection["id"], [product])

    assert get_collection(client, collection["id"])["stats"]["completed"] is False
    asset = make_asset(client, product, "pending")
    stats = get_collection(client, collection["id"])["stats"]
    assert stats["owned"] == stats["total"] == 1
    assert stats["percent"] == 100
    assert stats["completed"] is True

    client.patch(f"/api/v1/assets/{asset['id']}", json={"state": "sold"})
    assert get_collection(client, collection["id"])["stats"]["completed"] is False


def test_item_filters_search_and_note(client):
    collection = make_collection(client)
    first = make_product(client, "夏亚专用扎古II", manufacturer="测试厂", line="RG", code="02")
    second = make_product(client, "量产型扎古II", manufacturer="测试厂", line="RG", code="04")
    third = make_product(client, "神高达", manufacturer="测试厂", line="RG", code="43")
    add_items(client, collection["id"], [first, second, third])
    make_asset(client, first, "stored")

    assert client.get(f"/api/v1/collections/{collection['id']}/items?state=nope").status_code == 422

    search = client.get(f"/api/v1/collections/{collection['id']}/items?q=扎古").json()
    assert search["total"] == 2

    claimed = client.get(f"/api/v1/collections/{collection['id']}/items?q=02").json()
    assert claimed["total"] == 1
    assert claimed["items"][0]["name"] == "夏亚专用扎古II"

    item_id = claimed["items"][0]["id"]
    noted = client.patch(
        f"/api/v1/collections/{collection['id']}/items/{item_id}",
        json={"note": "等再版"},
    )
    assert noted.status_code == 200
    assert noted.json()["note"] == "等再版"

    cleared = client.patch(
        f"/api/v1/collections/{collection['id']}/items/{item_id}",
        json={"note": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["note"] is None


def test_bulk_remove_and_item_ownership(client):
    collection = make_collection(client)
    first = make_product(client, "A")
    second = make_product(client, "B")
    add_items(client, collection["id"], [first, second])
    listed = client.get(f"/api/v1/collections/{collection['id']}/items").json()["items"]

    removed = client.post(
        f"/api/v1/collections/{collection['id']}/items/bulk-remove",
        json={"item_ids": [listed[0]["id"]]},
    )
    assert removed.status_code == 200
    assert removed.json() == {"removed": 1}
    assert get_collection(client, collection["id"])["stats"]["total"] == 1

    remaining = client.get(f"/api/v1/collections/{collection['id']}/items").json()["items"][0]
    assert client.delete(
        f"/api/v1/collections/{collection['id']}/items/{remaining['id']}"
    ).status_code == 200
    assert get_collection(client, collection["id"])["stats"]["total"] == 0

    assert client.post(
        f"/api/v1/collections/{collection['id']}/items/bulk-remove",
        json={"item_ids": [str(uuid4())]},
    ).status_code == 404
    assert client.post(
        f"/api/v1/collections/{collection['id']}/items/bulk-remove",
        json={"item_ids": []},
    ).status_code == 422


def test_status_and_search_filters_on_collection_list(client):
    make_collection(client, "进行中的套", status="active", description="扎古主题")
    make_collection(client, "构想中的套", status="planning", description="夏亚主题")
    make_collection(client, "暂停的套", status="paused")

    active = client.get("/api/v1/collections?status=active").json()
    assert [row["title"] for row in active] == ["进行中的套"]

    searched = client.get("/api/v1/collections?q=夏亚").json()
    assert [row["title"] for row in searched] == ["构想中的套"]
    assert client.get("/api/v1/collections?status=nope").status_code == 422


def test_product_reverse_lookup_and_delete_cascades(client):
    first = make_product(client, "夏亚专用扎古II")
    second = make_product(client, "量产型扎古II")
    one = make_collection(client, "RG 扎古全制霸")
    two = make_collection(client, "夏亚全制霸")
    add_items(client, one["id"], [first])
    add_items(client, two["id"], [first, second])
    make_asset(client, first, "pending")

    reverse = client.get(f"/api/v1/products/{first['id']}/collections").json()
    assert {row["title"] for row in reverse} == {"RG 扎古全制霸", "夏亚全制霸"}
    assert all(row["owned"] is True for row in reverse)

    # A product without any asset can be deleted; its collection rows go too.
    assert client.delete(f"/api/v1/products/{second['id']}").status_code == 200
    assert get_collection(client, two["id"])["stats"]["total"] == 1

    # An asset still references the first product: deletion is refused and the
    # collection item stays.
    assert client.delete(f"/api/v1/products/{first['id']}").status_code == 409
    assert get_collection(client, one["id"])["stats"]["total"] == 1

    assert client.get(f"/api/v1/products/{uuid4()}/collections").status_code == 404


def test_deleting_a_collection_leaves_products_and_assets_alone(client):
    product = make_product(client, "夏亚专用扎古II")
    collection = make_collection(client)
    add_items(client, collection["id"], [product])
    make_asset(client, product, "pending")

    assert client.delete(f"/api/v1/collections/{collection['id']}").status_code == 200
    assert client.get(f"/api/v1/products/{product['id']}").status_code == 200
    assert len(client.get("/api/v1/assets").json()) == 1
