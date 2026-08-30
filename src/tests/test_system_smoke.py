"""任务中心、系统信息与冒烟测试。"""


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "version" in resp.json()


def test_system_info(client):
    resp = client.get("/api/system/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"].startswith("UTC+8")
    assert "version" in data and "server_time" in data


def test_system_config_requires_admin(client, test_env):
    token = client.post("/api/auth/login", json={"username": "tester", "password": "testpw"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/system/config", headers=h).status_code == 403

    resp = client.get("/api/system/config")
    assert resp.status_code == 200
    assert resp.json()["config"]["postgres"]["password"] == "******"
    assert resp.json()["config"]["postgres"]["host"] == "127.0.0.1"


def test_task_list(client):
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    ids = {t["task_id"] for t in resp.json()["items"]}
    assert {"postgres_check", "log_cleanup", "journal_orphan_scan"} <= ids


def test_log_cleanup_task_runs(client, test_env):
    # 造一个过期历史日志
    old_log = test_env.root / "logs" / "app.2020-01-01.log"
    old_log.write_text("old", encoding="utf-8")

    resp = client.post("/api/tasks/log_cleanup/run")
    assert resp.status_code == 200
    run = resp.json()["run"]
    assert run["status"] == "success"
    assert "1 个" in run["message"]
    assert not old_log.exists()


def test_postgres_check_task_reports_failure(client):
    """测试环境无行情库，任务应标记失败且信息可读（验证失败分支）。"""
    resp = client.post("/api/tasks/postgres_check/run")
    assert resp.status_code == 200
    run = resp.json()["run"]
    assert run["status"] == "failed"
    assert "行情数据库" in run["message"]


def test_task_run_history(client):
    client.post("/api/tasks/log_cleanup/run")
    resp = client.get("/api/tasks/log_cleanup/runs")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert resp.json()["items"][0]["task_id"] == "log_cleanup"


def test_unknown_task_404(client):
    assert client.post("/api/tasks/no_such_task/run").status_code == 404


def test_market_overview_without_db(client):
    """行情库不可达时返回 503 与可读错误（权限校验已通过）。"""
    resp = client.get("/api/market/overview")
    assert resp.status_code == 503


def test_market_kline_param_error(client):
    resp = client.get("/api/market/kline", params={
        "symbol": "600519", "exchange": "SSE", "interval": "7m"})
    assert resp.status_code == 400


def test_unauthorized_access_blocked(anon_client):
    """冒烟：所有业务接口未登录必须 401。"""
    for path in ["/api/market/overview", "/api/journal", "/api/datasets", "/api/tasks",
                 "/api/users", "/api/system/config"]:
        resp = anon_client.get(path)
        assert resp.status_code == 401, f"{path} 未拦截未登录访问"
