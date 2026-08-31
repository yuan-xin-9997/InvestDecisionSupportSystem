"""投资决策支持系统 - 后端入口。

启动方式（在 src 目录下）:
    .venv/bin/python -m app.backend.main
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import get_config
from .core.logger import setup_logging
from .db.sqlite import init_db
from .routers import auth, datasets, journal, market, system, tasks, users

logger = logging.getLogger("app")

SPA_DIST_DIR_NAME = "app/frontend/dist"


def create_app() -> FastAPI:
    cfg = get_config()
    setup_logging()
    init_db(cfg)

    app = FastAPI(title=str(cfg.get("app.name", "投资决策支持系统")),
                  version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(system.router)
    app.include_router(tasks.router)
    app.include_router(market.router)
    app.include_router(journal.router)
    app.include_router(datasets.router)

    @app.get("/api/health")
    def health():
        from .routers.system import get_version
        return {"status": "ok", "version": get_version()}

    _mount_spa(app, cfg)
    return app


class SPAStaticFiles(StaticFiles):
    """前端 SPA 静态文件：未命中的路径回退到 index.html（支持 history 路由刷新）。"""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def _mount_spa(app: FastAPI, cfg) -> None:
    dist_dir = cfg.base_dir / "app" / "frontend" / "dist"
    if dist_dir.is_dir() and (dist_dir / "index.html").is_file():
        app.mount("/", SPAStaticFiles(directory=dist_dir, html=True), name="spa")
        logger.info("前端静态资源已挂载: %s", dist_dir)
    else:
        logger.warning("未找到前端构建产物 %s，仅提供 API 服务", dist_dir)


app = create_app()


if __name__ == "__main__":
    import uvicorn

    cfg = get_config()
    uvicorn.run(
        "app.backend.main:app",
        host=str(cfg.get("server.host", "0.0.0.0")),
        port=int(cfg.get("server.port", 32080)),
        log_level="info",
    )
