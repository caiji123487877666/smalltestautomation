# AI 自动化测试平台

前后端分离的测试管理平台，覆盖**用户与 RBAC 权限、项目管理、模块树、测试用例、接口在线调试、缺陷管理**等能力，并为 AI 用例生成与自动化执行预留了扩展点。

## 技术栈

| 端 | 技术 |
|---|---|
| 后端 | Python 3.11+ / Django 5 / DRF / SimpleJWT / Celery / Redis / Playwright / OpenAI SDK |
| 前端 | Vue 3 (`<script setup lang="ts">`) / Vite / Pinia / Vue Router / Element Plus / Axios |
| 数据库 | 开发 SQLite，生产 MySQL 8.0（全部使用 Django ORM，无原生 SQL） |

## 目录结构

```
testautomation/
├── backend/                 # Django 后端
│   ├── apps/
│   │   ├── users/           # 用户、角色、菜单/按钮权限
│   │   ├── projects/        # 项目、模块树、环境
│   │   ├── testcases/       # 测试用例、Excel/Swagger 导入、接口调试
│   │   ├── bugs/            # 缺陷与流转历史
│   │   └── notifications/   # 通知信号（预留飞书/钉钉）
│   ├── config/              # settings / urls / celery
│   ├── utils/               # 统一渲染、异常、限流
│   ├── tests/               # pytest 测试
│   └── pyproject.toml       # pytest + ruff 配置
├── frontend/                # Vue 3 前端
│   └── src/{api,views,stores,router,utils}
└── .github/workflows/ci.yml # CI: ruff + pytest + 前端类型检查与构建
```

## 快速开始

### 1. 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt

# 环境变量（没有 .env 时默认 DEBUG=True + SQLite，可直接启动）
copy .env.example .env

python manage.py migrate
python manage.py init_rbac          # 初始化内置角色与菜单权限
python manage.py createsuperuser    # 创建管理员
python manage.py runserver 0.0.0.0:8000
```

接口文档：`http://127.0.0.1:8000/api/docs/`（Swagger）、`/api/redoc/`（Redoc）。

### 2. 前端

```powershell
cd frontend
npm install
copy .env.example .env.development   # 按需修改 VITE_API_BASE
npm run dev                          # http://127.0.0.1:5173
```

前端请求统一走 `/api`，开发环境由 Vite 代理转发到后端 `http://127.0.0.1:8000`。

## 测试与代码检查

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -v     # 单元/接口测试
.venv\Scripts\python.exe -m ruff check .  # 静态检查

cd ..\frontend
npm run type-check                        # TypeScript 类型检查
npm run build                             # 生产构建
```

CI（`.github/workflows/ci.yml`）会在 push / PR 时自动执行以上检查。

## 环境变量

后端变量见 [backend/.env.example](backend/.env.example)，前端变量见 [frontend/.env.example](frontend/.env.example)。所有 `.env*` 文件均不进版本库，只提交 `.env.example` 模板。

## 安全说明

- **接口调试 SSRF 防护**：在线调试出站请求只允许 `http/https`，默认拦截内网、回环、链路本地（含云厂商 metadata）地址，并逐跳校验重定向。开发环境可通过 `API_DEBUG_ALLOW_PRIVATE_NETWORK=True` 允许访问本地/内网服务；**生产环境请保持 `False`**。
- **生产配置强校验**：`DEBUG=False` 时必须显式提供 `SECRET_KEY`，且 `ALLOWED_HOSTS` 不允许为 `*`，否则启动直接报错；CORS 默认仅允许 `CORS_ALLOWED_ORIGINS` 白名单。
- **认证限流**：登录 / 注册默认限流（`LOGIN_THROTTLE_RATE`、`REGISTER_THROTTLE_RATE`），缓解暴力破解与批量注册。
- **密码重置**：管理员重置密码必须输入新密码，并经过 Django 密码强度校验，不再使用默认弱口令，也不会在响应中回显密码。

## 能力边界

已实现：用户认证与 RBAC、项目/模块管理、测试用例（API/WEB）与导入导出、接口在线调试与 cURL 解析、缺陷管理与流转历史。

尚未实现（预留扩展点）：Celery 异步执行引擎、Playwright 用例执行、`ExecutionRecord` 执行记录、`ai_engine` 大模型用例生成/Bug 总结、飞书/钉钉通知推送。
