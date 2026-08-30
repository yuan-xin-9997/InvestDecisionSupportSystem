# 投资决策支持系统（InvestDecisionSupportSystem）

为个人投资股票、黄金、基金提供数据参考的一站式决策支持系统。基于 **FastAPI + Vue 3 + SQLite**，行情数据直连本机 PostgreSQL（vnpy 行情库）。

## 系统介绍

| 模块 | 说明 |
| ---- | ---- |
| 系统概览 | 系统版本、运行状态、行情库连接状态、快捷入口 |
| 行情展示 | 连接 PostgreSQL 行情库（vnpy 格式 `dbbardata`），支持 K 线图（ECharts 蜡烛图 + MA5/10/20 + 成交量）与表格两种形式，支持品种/周期（日/1小时/1分钟）/日期范围/根数筛选 |
| 投资日志 | 图文日志：上传图片与文字记录投资笔记；按时间线倒序展示，支持日期范围与关键词筛选、编辑、删除 |
| 数据管理 | 自定义跟踪数据集（宏观/微观/其他），记录"日期-数值-备注"数据，支持折线图、CSV 导入导出 |
| 任务中心 | 内置任务（行情库连通性检查、历史日志清理、日志附件一致性检查）的列表、状态、立即运行与运行日志 |
| 权限管理 | 维护可登录用户的角色（管理员/普通用户）与可见页面（管理员专用） |
| 系统配置 | 展示运行信息与脱敏后的主配置（管理员专用） |

基础能力：

- **登录认证**：用户名密码维护在 `src/data/password.txt`（格式 `username:password:role`），新用户登录时自动同步进数据库；会话 token 有效期可配置。
- **页面权限**：admin 拥有全部页面；普通用户的可见页面由管理员在权限管理页配置。
- **UI 要求**：左侧边栏底部显示当前登录用户、退出按钮与系统版本号（版本号 = GitHub 提交数量）；浏览器 TAB 页有专属图标。
- **北京时间**：系统展示的所有时间统一为北京时间（UTC+8）。

## 页面介绍

访问 `http://<服务器IP>:8620`（端口可在 `src/config/app.json` 配置），默认账号 `admin / admin123`（首次登录后请在 password.txt 中修改）。

- `/login` 登录页
- `/` 系统概览：统计卡片、系统信息、行情库状态
- `/market` 行情展示：K 线图/表格切换、品种周期筛选
- `/journal` 投资日志：时间线、写日志（图文）、筛选
- `/datasets` 数据管理：数据集列表、记录录入、折线图、CSV 导入导出
- `/tasks` 任务中心：任务列表、立即运行、运行历史
- `/users` 权限管理（管理员）：角色与页面权限维护
- `/config` 系统配置（管理员）：运行信息与脱敏配置

## 目录结构

```
├── README.md / 需求规格说明书.md / 设计说明书.md
├── start.ps1|sh  status.ps1|sh  stop.ps1|sh     # 启停/状态脚本（Windows/Linux）
└── src/
    ├── app/
    │   ├── backend/          # FastAPI 后端（core/config/db/models/routers）
    │   └── frontend/         # Vue 3 前端（构建产物 dist 一并提交，部署无需 Node）
    ├── config/app.json       # 主配置文件（端口、PostgreSQL、日志、上传等）
    ├── data/                 # SQLite 数据、password.txt、日志图片（按年/月/日存放）
    ├── JenkinsConfig/        # Jenkinsfile 与 systemd 服务单元
    ├── tests/                # 单元测试与冒烟测试（pytest）
    └── logs/                 # app.log（当天）+ app.日期.log（历史，自动切割）
```

## 配置文件说明（src/config/app.json）

| 配置项 | 说明 |
| ------ | ---- |
| `server.host/port` | 服务监听地址与端口（默认 0.0.0.0:8620） |
| `database.sqlite_file` | 本地 SQLite 文件路径（相对 src 目录） |
| `postgres.*` | 行情数据库连接（host/port/user/password/dbname/connect_timeout/query_limit_max），对应 vnpy 库的 `dbbardata`/`dbbaroverview`/`dbtickoverview` |
| `auth.token_expire_days` | 登录 token 有效天数（默认 7） |
| `log.level/dir/retention_days` | 日志级别、目录与历史日志保留天数 |
| `upload.journal_dir/max_image_mb/max_long_edge` | 日志图片目录、单图大小上限、长边压缩阈值 |

> 注意：所有环境信息（IP、端口、密码等）只出现在配置文件中，代码不硬编码。仓库同时提供 `config/app.json.example` 模板：**首次部署**时由 Jenkins 流水线（或手工复制）引导生成 `app.json`，**后续部署不会覆盖**已存在的 `app.json`（本地化修改得到保留）。

## 部署方式

### Linux（推荐，配合 Jenkins）

```bash
cd /opt/InvestDecisionSupportSystem/src
bash start.sh      # 自动创建 venv、安装依赖、初始化 data 目录、后台启动
bash status.sh     # 状态检查（PID + 健康检查）
bash stop.sh       # 停止服务
```

Jenkins 流水线（`src/JenkinsConfig/Jenkinsfile`）：每 30 分钟轮询 GitHub 提交，自动执行停服 → rsync 同步代码（排除 `data/`、`logs/`、`config/app.json`、`.venv/`）→ 安装依赖 → 运行测试 → 启动服务。部署路径为 `/opt/InvestDecisionSupportSystem`。

### systemd 方式（Linux）

```bash
sudo cp src/JenkinsConfig/invest-dss.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now invest-dss.service
systemctl status invest-dss.service
```

### Windows

```powershell
powershell -File src\start.ps1    # 启动
powershell -File src\status.ps1   # 状态
powershell -File src\stop.ps1     # 停止
```

### 前端开发模式

```bash
cd src/app/frontend
npm install
npm run dev        # Vite 开发服务器（5173），API 代理到 127.0.0.1:8620
npm run build      # 构建产物输出到 dist/（由 FastAPI 托管）
```

## 运维方式

- **日志**：`src/logs/app.log` 为当天日志，按天自动切割为 `app.YYYY-MM-DD.log`，超过保留天数可在任务中心运行"历史日志清理"。
- **健康检查**：`GET /api/health` 返回状态与版本号。
- **接口文档**：`/api/docs`（Swagger UI）。
- **用户管理**：编辑 `src/data/password.txt` 后，新用户下次登录自动同步；也可在权限管理页点击"从 password.txt 同步"。
- **数据备份**：定期备份 `src/data/`（SQLite 库 + 日志图片）与 `src/config/app.json`。

## 测试

```bash
cd src
../.venv/bin/python -m pytest tests -v   # 42 个单元/接口/冒烟测试（使用临时目录，不污染生产数据）
```

## 访问方式

- 本机：http://127.0.0.1:8620
- 局域网：http://<部署机IP>:8620
