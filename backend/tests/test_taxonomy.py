"""Manufacturer / product-line taxonomy tests."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.models import ReviewItem


def make_manufacturer(client, name, **fields):
    response = client.post("/api/v1/manufacturers", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def make_line(client, manufacturer_id, name, **fields):
    response = client.post(
        "/api/v1/product-lines",
        json={"manufacturer_id": manufacturer_id, "name": name, **fields},
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_product(client, manufacturer_id, name, line_id=None, **fields):
    payload = {
        "kit_name": name,
        "manufacturer_id": manufacturer_id,
        "product_line_id": line_id,
        "source": "pytest",
        **fields,
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_manufacturer_crud_category_tier_and_order(client):
    guomo = make_manufacturer(client, "国模一号", category="guomo", tier=1)
    ko = make_manufacturer(client, "KO 一号", category="ko", tier=1)
    unclassified = make_manufacturer(client, "未分类厂")
    assert unclassified["tier"] == 3
    assert unclassified["category"] is None

    listed = client.get("/api/v1/manufacturers", params={"q": "一号"}).json()
    assert [row["id"] for row in listed[:2]] == [guomo["id"], ko["id"]]

    filtered = client.get("/api/v1/manufacturers", params={"category": "ko", "q": "一号"}).json()
    assert [row["name"] for row in filtered] == ["KO 一号"]

    updated = client.patch(
        f"/api/v1/manufacturers/{unclassified['id']}",
        json={"category": "guomo", "tier": 2, "sort_order": 5, "description": "测试"},
    )
    assert updated.status_code == 200
    assert updated.json()["category"] == "guomo"
    assert updated.json()["tier"] == 2
    assert updated.json()["sort_order"] == 5

    assert client.post("/api/v1/manufacturers", json={"name": "国模一号"}).status_code == 409
    assert client.post(
        "/api/v1/manufacturers", json={"name": "坏分类", "category": "other"}
    ).status_code == 422
    assert client.post(
        "/api/v1/manufacturers", json={"name": "坏等级", "tier": 4}
    ).status_code == 422


def test_product_lines_are_flat_and_deletion_resets_products_to_unknown(client):
    maker = make_manufacturer(client, "系列厂")
    hg = make_line(client, maker["id"], "HG")
    hguc = make_line(client, maker["id"], "HGUC")
    assert hg["id"] != hguc["id"]

    product = make_product(client, maker["id"], "测试机体", hg["id"])
    assert product["product_line_id"] == hg["id"]
    assert product["product_line"] == "HG"

    assert client.post(
        "/api/v1/product-lines",
        json={"manufacturer_id": maker["id"], "name": "HG"},
    ).status_code == 409

    renamed = client.patch(f"/api/v1/product-lines/{hg['id']}", json={"name": "HG 改"})
    assert renamed.status_code == 200
    assert client.get(f"/api/v1/products/{product['id']}").json()["product_line"] == "HG 改"

    deleted = client.delete(f"/api/v1/product-lines/{hg['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["products_reset"] == 1
    refreshed = client.get(f"/api/v1/products/{product['id']}").json()
    assert refreshed["product_line_id"] is None
    assert refreshed["product_line"] is None


def test_product_requires_matching_manufacturer_and_line(client):
    first = make_manufacturer(client, "厂商甲")
    second = make_manufacturer(client, "厂商乙")
    second_line = make_line(client, second["id"], "RG")

    wrong = client.post(
        "/api/v1/products",
        json={
            "kit_name": "错线机体",
            "manufacturer_id": first["id"],
            "product_line_id": second_line["id"],
            "source": "pytest",
        },
    )
    assert wrong.status_code == 422

    assert client.post(
        "/api/v1/products",
        json={
            "kit_name": "无厂商机体",
            "manufacturer_id": str(uuid4()),
            "source": "pytest",
        },
    ).status_code == 404

    make_product(client, first["id"], "同名机体")
    duplicate = client.post(
        "/api/v1/products",
        json={"kit_name": "同名机体", "manufacturer_id": first["id"], "source": "pytest"},
    )
    assert duplicate.status_code == 409


def test_merge_manufacturer_moves_products_and_lines(client):
    source = make_manufacturer(client, "待合并厂")
    target = make_manufacturer(client, "目标厂")
    line = make_line(client, source["id"], "MG")
    product = make_product(client, source["id"], "待移动机体", line["id"])

    response = client.post(
        f"/api/v1/manufacturers/{source['id']}/merge",
        json={"target_id": target["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == target["id"]

    assert client.get(f"/api/v1/manufacturers/{source['id']}").status_code == 404
    moved = client.get(f"/api/v1/products/{product['id']}").json()
    assert moved["manufacturer_id"] == target["id"]
    assert moved["manufacturer"] == "目标厂"
    assert moved["product_line_id"] == line["id"]

    target_lines = client.get(
        "/api/v1/product-lines", params={"manufacturer_id": target["id"]}
    ).json()
    assert [row["name"] for row in target_lines] == ["MG"]


def test_merge_reuses_same_named_line_and_moves_products(client):
    source = make_manufacturer(client, "源厂")
    target = make_manufacturer(client, "宿厂")
    source_line = make_line(client, source["id"], "HG")
    target_line = make_line(client, target["id"], "HG")
    product = make_product(client, source["id"], "同线机体", source_line["id"])

    assert client.post(
        f"/api/v1/manufacturers/{source['id']}/merge",
        json={"target_id": target["id"]},
    ).status_code == 200
    moved = client.get(f"/api/v1/products/{product['id']}").json()
    assert moved["manufacturer_id"] == target["id"]
    assert moved["product_line_id"] == target_line["id"]
    lines = client.get("/api/v1/product-lines", params={"manufacturer_id": target["id"]}).json()
    assert len(lines) == 1


def test_product_update_to_another_manufacturer_resets_foreign_line(client):
    first = make_manufacturer(client, "旧厂商")
    second = make_manufacturer(client, "新厂商")
    first_line = make_line(client, first["id"], "HG")
    second_line = make_line(client, second["id"], "RG")
    product = make_product(client, first["id"], "换厂机体", first_line["id"])

    moved = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"manufacturer_id": second["id"]},
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["manufacturer_id"] == second["id"]
    assert body["product_line_id"] is None

    relined = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"product_line_id": second_line["id"]},
    )
    assert relined.status_code == 200
    assert relined.json()["product_line_id"] == second_line["id"]

    wrong = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"product_line_id": first_line["id"]},
    )
    assert wrong.status_code == 422


def test_merge_manufacturer_rejects_product_name_collisions(client):
    source = make_manufacturer(client, "碰撞源厂")
    target = make_manufacturer(client, "碰撞目标厂")
    make_product(client, source["id"], "同名碰撞机体")
    make_product(client, target["id"], "同名碰撞机体")

    response = client.post(
        f"/api/v1/manufacturers/{source['id']}/merge",
        json={"target_id": target["id"]},
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/manufacturers/{source['id']}").status_code == 200


def test_delete_product_resets_linked_review_match(client, product, db):
    item = ReviewItem(
        source_key=f"delete-{uuid4()}",
        event_date=date.today(),
        brand="测试厂",
        product=product["kit_name"],
        state="mapped",
        product_id=product["id"],
        manufacturer_id=product["manufacturer_id"],
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    response = client.delete(f"/api/v1/products/{product['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["review_items_reset"] == 1

    db.refresh(item)
    assert item.state == "pending"
    assert item.product_id is None
    assert item.manufacturer_id is None
    assert item.product_line_id is None


def test_same_name_in_different_series_is_a_different_product(client):
    maker = make_manufacturer(client, "多系列厂")
    first_line = make_line(client, maker["id"], "HG")
    second_line = make_line(client, maker["id"], "RG")

    first = make_product(client, maker["id"], "同名不同线机体", first_line["id"])
    second = make_product(client, maker["id"], "同名不同线机体", second_line["id"])
    assert first["id"] != second["id"]

    duplicate = client.post(
        "/api/v1/products",
        json={
            "kit_name": "同名不同线机体",
            "manufacturer_id": maker["id"],
            "product_line_id": first_line["id"],
            "source": "pytest",
        },
    )
    assert duplicate.status_code == 409

    moved = client.patch(
        f"/api/v1/products/{second['id']}",
        json={"product_line_id": first_line["id"]},
    )
    assert moved.status_code == 409


def test_same_name_unknown_line_is_its_own_bucket(client):
    maker = make_manufacturer(client, "未知线厂")
    line = make_line(client, maker["id"], "HG")
    named = make_product(client, maker["id"], "未知线同名机体", line["id"])
    unknown = make_product(client, maker["id"], "未知线同名机体")
    assert named["id"] != unknown["id"]


def test_manufacturer_deletion_is_blocked_while_products_exist(client):
    maker = make_manufacturer(client, "有产品厂")
    make_product(client, maker["id"], "产品一")
    assert client.delete(f"/api/v1/manufacturers/{maker['id']}").status_code == 409

    empty = make_manufacturer(client, "空厂")
    assert client.delete(f"/api/v1/manufacturers/{empty['id']}").status_code == 200
    assert client.get(f"/api/v1/manufacturers/{empty['id']}").status_code == 404


def test_release_channel_is_closed_validated_and_filterable(client):
    maker = make_manufacturer(client, "渠道厂")
    regular = make_product(client, maker["id"], "通贩机体", release_channel="regular")
    pb = make_product(client, maker["id"], "PB机体", release_channel="pb")
    assert regular["release_channel"] == "regular"
    assert pb["release_channel"] == "pb"

    invalid = client.post(
        "/api/v1/products",
        json={
            "kit_name": "坏渠道机体",
            "manufacturer_id": maker["id"],
            "release_channel": "not-a-channel",
            "source": "pytest",
        },
    )
    assert invalid.status_code == 422

    filtered = client.get(
        "/api/v1/products",
        params={"release_channel": "pb", "search": "PB机体"},
    )
    assert filtered.status_code == 200
    rows = filtered.json()
    assert [row["id"] for row in rows] == [pb["id"]]

    assert client.get(
        "/api/v1/products", params={"release_channel": "not-a-channel"}
    ).status_code == 422

    cleared = client.patch(
        f"/api/v1/products/{pb['id']}",
        json={"release_channel": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["release_channel"] is None


def test_bulk_channel_update(client):
    maker = make_manufacturer(client, "批量渠道厂")
    first = make_product(client, maker["id"], "批量渠道一")
    second = make_product(client, maker["id"], "批量渠道二")

    response = client.patch(
        "/api/v1/products/bulk-channel",
        json={"product_ids": [first["id"], second["id"]], "release_channel": "pb"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["updated"] == 2
    assert client.get(f"/api/v1/products/{first['id']}").json()["release_channel"] == "pb"
    assert client.get(f"/api/v1/products/{second['id']}").json()["release_channel"] == "pb"

    invalid = client.patch(
        "/api/v1/products/bulk-channel",
        json={"product_ids": [first["id"]], "release_channel": "bad"},
    )
    assert invalid.status_code == 422
    assert client.patch(
        "/api/v1/products/bulk-channel",
        json={"product_ids": [], "release_channel": "pb"},
    ).status_code == 422


def test_review_create_uses_selected_manufacturer_and_line(client, db):
    maker = make_manufacturer(client, "审核厂")
    line = make_line(client, maker["id"], "RG")
    item = ReviewItem(
        source_key=f"taxonomy-{uuid4()}",
        event_date=date.today(),
        brand="抽取里的旧厂商名",
        line="RG",
        product="审核机体",
        state="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    response = client.post(
        f"/api/v1/review/{item.id}/create",
        json={
            "manufacturer_id": maker["id"],
            "product_line_id": line["id"],
            "kit_name": "审核机体",
            "release_channel": "pb",
        },
    )
    assert response.status_code == 200, response.text
    product = response.json()
    assert product["manufacturer_id"] == maker["id"]
    assert product["product_line_id"] == line["id"]
    assert product["release_channel"] == "pb"

    db.refresh(item)
    assert item.state == "created"
    assert str(item.product_id) == product["id"]
    assert str(item.manufacturer_id) == maker["id"]
    assert str(item.product_line_id) == line["id"]
    # The raw extraction is still kept for audit.
    assert item.brand == "抽取里的旧厂商名"

