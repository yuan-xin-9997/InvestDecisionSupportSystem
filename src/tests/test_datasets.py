"""数据管理（数据集与记录）接口测试。"""


def _create_dataset(client, name="CPI 同比", **kw):
    payload = {"name": name, "category": "宏观", "unit": "%", "description": "消费者价格指数"}
    payload.update(kw)
    return client.post("/api/datasets", json=payload)


def test_dataset_crud(client):
    resp = _create_dataset(client)
    assert resp.status_code == 200
    d = resp.json()["dataset"]
    assert d["record_count"] == 0

    # 重名拒绝
    assert _create_dataset(client).status_code == 400

    # 更新
    resp = client.put(f"/api/datasets/{d['id']}", json={"unit": "百分点", "category": "微观"})
    assert resp.json()["dataset"]["unit"] == "百分点"

    # 删除
    assert client.delete(f"/api/datasets/{d['id']}").status_code == 200
    assert client.put(f"/api/datasets/{d['id']}", json={"unit": "x"}).status_code == 404


def test_dataset_category_validation(client):
    assert _create_dataset(client, name="坏分类", category="不存在").status_code == 400


def test_record_upsert_and_query(client):
    d = _create_dataset(client, name="黄金ETF持仓").json()["dataset"]

    resp = client.post(f"/api/datasets/{d['id']}/records",
                       json={"date": "2026-08-01", "value": 12.5, "note": "月初"})
    assert resp.status_code == 200
    # 同日期再次写入 -> 覆盖
    resp = client.post(f"/api/datasets/{d['id']}/records",
                       json={"date": "2026-08-01", "value": 13.0, "note": "修正"})
    assert resp.status_code == 200

    resp = client.get(f"/api/datasets/{d['id']}/records")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["value"] == 13.0

    for i in range(2, 6):
        client.post(f"/api/datasets/{d['id']}/records",
                    json={"date": f"2026-08-0{i}", "value": 10.0 + i})
    resp = client.get(f"/api/datasets/{d['id']}/records", params={"page_size": 3})
    assert resp.json()["total"] == 5 and len(resp.json()["items"]) == 3

    # 列表元信息（最新记录）
    resp = client.get("/api/datasets")
    row = [x for x in resp.json()["items"] if x["id"] == d["id"]][0]
    assert row["record_count"] == 5
    assert row["latest_date"] == "2026-08-05"
    assert row["latest_value"] == 15.0

    # 非法日期
    resp = client.post(f"/api/datasets/{d['id']}/records",
                       json={"date": "2026/08/09", "value": 1})
    assert resp.status_code == 400


def test_csv_import_export(client):
    d = _create_dataset(client, name="十年期国债收益率").json()["dataset"]
    csv_text = "date,value,note\n2026-01-05,1.8,年初\n2026-01-06,1.82,\n2026-01-07,1.79,回调\n"
    resp = client.post(f"/api/datasets/{d['id']}/import",
                       files={"file": ("data.csv", csv_text.encode("utf-8"), "text/csv")})
    assert resp.status_code == 200
    assert resp.json() == {"inserted": 3, "updated": 0, "skipped": 0}

    # 重复导入 -> 更新
    csv_text2 = "date,value,note\n2026-01-05,1.85,修正\n"
    resp = client.post(f"/api/datasets/{d['id']}/import",
                       files={"file": ("data.csv", csv_text2.encode("utf-8"), "text/csv")})
    assert resp.json() == {"inserted": 0, "updated": 1, "skipped": 0}

    # 坏行跳过
    csv_text3 = "date,value,note\n2026-01-08,abc,\n2026-01-09,1.7,\n"
    resp = client.post(f"/api/datasets/{d['id']}/import",
                       files={"file": ("data.csv", csv_text3.encode("utf-8"), "text/csv")})
    assert resp.json()["skipped"] == 1 and resp.json()["inserted"] == 1

    # 导出
    resp = client.get(f"/api/datasets/{d['id']}/export")
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("date,value,note")
    assert "2026-01-05,1.85" in body


def test_gbk_csv_import(client):
    d = _create_dataset(client, name="社融增量").json()["dataset"]
    csv_text = "date,value,note\n2026-02-01,5.2,人民币口径\n"
    resp = client.post(f"/api/datasets/{d['id']}/import",
                       files={"file": ("data.csv", csv_text.encode("gbk"), "text/csv")})
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 1
