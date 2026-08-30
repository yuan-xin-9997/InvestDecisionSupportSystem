"""登录认证与权限管理接口测试。"""


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


def test_me_with_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "admin"
    assert resp.json()["user"]["role"] == "admin"


def test_me_without_token(anon_client):
    resp = anon_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_new_user_sync_on_login(client, test_env):
    """password.txt 中新增的用户首次登录自动同步进数据库。"""
    pf = test_env.root / "data" / "password.txt"
    pf.write_text(pf.read_text(encoding="utf-8") + "newbie:newpw:user\n", encoding="utf-8")

    resp = client.post("/api/auth/login", json={"username": "newbie", "password": "newpw"})
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "user"

    # 管理员可见该用户已同步
    resp = client.get("/api/users")
    names = [u["username"] for u in resp.json()["items"]]
    assert "newbie" in names


def test_users_list_requires_admin(client, test_env):
    resp = client.post("/api/auth/login", json={"username": "tester", "password": "testpw"})
    token = resp.json()["token"]
    resp = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_updates_user_pages(client, test_env):
    resp = client.get("/api/users")
    users = {u["username"]: u for u in resp.json()["items"]}
    assert "tester" in users

    resp = client.put("/api/users/tester", json={"pages": ["dashboard", "market"]})
    assert resp.status_code == 200
    assert resp.json()["user"]["pages"] == ["dashboard", "market"]

    # tester 访问 market 通过，访问 journal 被拒
    token = client.post("/api/auth/login", json={"username": "tester", "password": "testpw"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/market/overview", headers=h).status_code in (200, 503)  # 503=无行情库连接，权限已通过
    assert client.get("/api/journal", headers=h).status_code == 403


def test_cannot_remove_last_admin(client):
    resp = client.put("/api/users/admin", json={"role": "user"})
    assert resp.status_code == 400


def test_logout_invalidates_token(client):
    resp = client.post("/api/auth/login", json={"username": "tester", "password": "testpw"})
    token = resp.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200
    client.post("/api/auth/logout", headers=h)
    assert client.get("/api/auth/me", headers=h).status_code == 401
