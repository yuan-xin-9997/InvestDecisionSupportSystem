"""投资日志接口测试。"""

from conftest import make_png


def _create(client, content="测试日志", n_images=0, trade_date=None):
    files = [("files", (f"img{i}.png", make_png(120, 90), "image/png")) for i in range(n_images)]
    data = {"content": content}
    if trade_date:
        data["trade_date"] = trade_date
    return client.post("/api/journal", data=data, files=files)


def test_create_journal_text_only(client):
    resp = _create(client, "今天买入了一些黄金ETF")
    assert resp.status_code == 200
    j = resp.json()["journal"]
    assert j["content"] == "今天买入了一些黄金ETF"
    assert j["images"] == []
    assert len(j["trade_date"]) == 10


def test_create_journal_with_images(client):
    resp = _create(client, "带图日志", n_images=2)
    assert resp.status_code == 200
    j = resp.json()["journal"]
    assert len(j["images"]) == 2
    img_id = j["images"][0]["id"]
    got = client.get(f"/api/journal/images/{img_id}")
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/png"


def test_create_journal_empty_rejected(client):
    resp = client.post("/api/journal", data={"content": "   "}, files=[])
    assert resp.status_code == 400


def test_create_journal_bad_image_rejected(client):
    resp = client.post(
        "/api/journal",
        data={"content": "坏图"},
        files=[("files", ("x.png", b"not-an-image", "image/png"))],
    )
    assert resp.status_code == 400


def test_journal_timeline_query_and_filter(client):
    _create(client, "2026年8月末的操作", trade_date="2026-08-20")
    _create(client, "9月的记录", trade_date="2026-09-01")
    _create(client, "9月又一条", trade_date="2026-09-05")

    # 时间线倒序
    resp = client.get("/api/journal")
    dates = [j["trade_date"] for j in resp.json()["items"]]
    assert dates == sorted(dates, reverse=True)
    assert resp.json()["total"] >= 3

    # 日期范围
    resp = client.get("/api/journal", params={
        "start_date": "2026-09-01", "end_date": "2026-09-30"})
    assert all("2026-09" in j["trade_date"] for j in resp.json()["items"])

    # 关键词
    resp = client.get("/api/journal", params={"keyword": "黄金ETF"})
    assert resp.json()["total"] >= 1


def test_update_and_delete_journal(client):
    j = _create(client, "原始内容").json()["journal"]
    jid = j["id"]

    resp = client.put(f"/api/journal/{jid}", json={"content": "修改后的内容", "trade_date": "2026-08-15"})
    assert resp.status_code == 200
    assert resp.json()["journal"]["content"] == "修改后的内容"

    resp = client.delete(f"/api/journal/{jid}")
    assert resp.status_code == 200
    assert client.get(f"/api/journal/{jid}").status_code == 404


def test_append_and_delete_image(client):
    j = _create(client, "追加图片测试").json()["journal"]
    jid = j["id"]
    resp = client.post(
        f"/api/journal/{jid}/images",
        files=[("files", ("add.png", make_png(50, 50), "image/png"))],
    )
    assert resp.status_code == 200
    assert len(resp.json()["journal"]["images"]) == 1
    img_id = resp.json()["journal"]["images"][0]["id"]

    assert client.delete(f"/api/journal/{jid}/images/{img_id}").status_code == 200
    assert client.get(f"/api/journal/images/{img_id}").status_code == 404


def test_large_image_is_compressed(client):
    # 生成超过 max_long_edge(2000) 的图片，保存后应被等比压缩
    big = make_png(2600, 1000)
    resp = client.post(
        "/api/journal",
        data={"content": "大图压缩"},
        files=[("files", ("big.png", big, "image/png"))],
    )
    assert resp.status_code == 200
    url = resp.json()["journal"]["images"][0]["url"]
    got = client.get(url)
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(got.content))
    assert max(img.size) == 2000


def test_oversized_file_rejected(client):
    big_bytes = b"\x89PNG" + b"0" * (6 * 1024 * 1024)  # 6MB > 限制 5MB
    resp = client.post(
        "/api/journal",
        data={"content": "超大文件"},
        files=[("files", ("huge.png", big_bytes, "image/png"))],
    )
    assert resp.status_code == 400
