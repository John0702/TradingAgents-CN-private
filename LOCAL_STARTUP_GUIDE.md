# TradingAgents-CN 本地启动指南

> 本文档记录本地开发环境的完整启动流程、首次初始化步骤，以及历史踩坑记录。
> **新接手的同学：请严格按"快速开始（Docker 一键启动）"流程走完，包括"首次启动后初始化"，否则前端分析功能会跑不通。**

---

## 📋 系统架构

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API (FastAPI) | 8000 | 容器名 `tradingagents-backend` |
| 前端 (Nginx 静态 + 反代) | 3000 | 容器名 `tradingagents-frontend` |
| MongoDB 4.4 | 27017 | 容器名 `tradingagents-mongodb` |
| Redis 7 | 6379 | 容器名 `tradingagents-redis` |
| Redis Commander（可选） | 8081 | `--profile management` 才会起 |
| Mongo Express（可选） | 8082 | `--profile management` 才会起 |

> 编排文件使用项目根目录的 `docker-compose.yml`。

---

## 🚀 快速开始（Docker 一键启动）

### 0. 前置环境

- Docker Desktop 4.x（自带 `docker compose` 插件）
- 项目克隆到本地，已切到正确分支

### 1. 配置环境变量

```bash
cp .env.example .env
```

**必须修改 `.env` 里以下几项**，否则容器之间互相连不上：

```bash
# ⚠️ Docker 网络里要用容器名做主机，不要写 localhost
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=tradingagents123
MONGODB_DATABASE=tradingagentscn
MONGODB_CONNECTION_STRING=mongodb://admin:tradingagents123@mongodb:27017/

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=tradingagents123

# 生产环境务必改成强随机串
JWT_SECRET=请改成长随机串
CSRF_SECRET=请改成长随机串
```

> 大模型 / 数据源的 API Key 这里**先不用填**，下面第 3 步用前端「系统设置 → 大模型配置」配进 MongoDB 更稳。

### 2. 启动所有服务

```bash
docker compose up -d --build
```

第一次会拉镜像 + 装依赖 + 构建前端，耗时 5–15 分钟。

检查健康状态：

```bash
docker compose ps
```

四个核心容器都应该是 `running (healthy)`。

访问入口：

- 前端：http://localhost:3000
- 后端 API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

### 3. 🔑 首次启动后初始化（必做，否则用不起来）

#### 3.1 创建默认账号

```bash
docker exec tradingagents-backend python /app/scripts/init_admin_user.py
```

成功输出会列出：
- `admin / admin123` （管理员）
- `user / user123` （普通用户）

#### 3.2 在 MongoDB 里激活一个 LLM Provider

**这一步不做的话，前端「分析」页面的模型下拉框会是空的。**

后端 `app/routers/config.py:1011` 会过滤模型，只展示满足 `enabled=true AND provider IN 已激活供应商` 的模型。`llm_providers` 集合默认是**空的**，所以必须先插一条记录把供应商激活。

下面以"OpenAI 兼容"供应商（指向你自己的 OpenAI 兼容网关）为例：

```bash
docker exec tradingagents-mongodb mongo \
  -u admin -p tradingagents123 --authenticationDatabase admin tradingagentscn --eval '
db.llm_providers.insertOne({
  "name": "openai",
  "display_name": "OpenAI兼容",
  "is_active": true,
  "default_base_url": "https://你的网关/v1",
  "api_key": "sk-你的key",
  "created_at": new Date(),
  "updated_at": new Date()
})'
```

#### 3.3 在前端「系统设置 → 大模型配置」里新增一个模型

打开 http://localhost:3000，用 admin 登录后到「系统设置 → 大模型配置」，**新增**一条模型，关键字段：

- `model_name`：例如 `glm-5.1` （注意是 `model_name`，不是 `model`）
- `provider`：选 `openai`（必须和上一步插入的 `llm_providers.name` 一致）
- `base_url`：`https://你的网关/v1`
- `api_key`：与上一步一致
- `enabled`：勾选

#### 3.4 把"默认快速 / 深度模型"指向已配置好的那个模型

**这一步极其关键**——系统默认深度模型是 `qwen-max`，如果你没单独配置 `qwen-max`，分析进入"研究辩论"阶段时会按"模型名以 qwen 开头"映射到阿里百炼 `dashscope.aliyuncs.com`，用你的 key 请求返回 401。

```bash
docker exec tradingagents-mongodb mongo \
  -u admin -p tradingagents123 --authenticationDatabase admin tradingagentscn --eval '
db.system_configs.updateOne(
  {"is_active": true},
  {"$set": {
    "settings.quick_analysis_model": "glm-5.1",
    "settings.deep_analysis_model": "glm-5.1",
    "settings.quick_think_llm": "glm-5.1",
    "settings.deep_think_llm": "glm-5.1",
    "updated_at": new Date()
  }}
)'
```

把 `glm-5.1` 换成你 3.3 里配置的模型名即可。

#### 3.5 配置数据源（A 股推荐 Tushare）

1. 到 https://tushare.pro/ 注册账号、拿到 token
2. 编辑 `.env`：
   ```bash
   TUSHARE_TOKEN=你的token
   TUSHARE_ENABLED=true
   ```
3. 重启后端：`docker compose restart backend`

> AKShare 不需要 token，但稳定性差；BaoStock 免费但数据较少；Tushare 是 A 股最推荐的主源。

### 4. 验证

用 admin 登录前端 → 进入"股票分析"页 → 选 600519 / glm-5.1 → 点开始。

后端日志：

```bash
docker compose logs -f backend
```

应能看到：
- `📊 [数据来源: tushare] 获取数据成功`
- 各 Agent 流轮转，最终生成分析报告
- 没有 `event loop is already running` 或 `401 Unauthorized`

---

## 🛠 常用运维命令

```bash
# 全部停（保留数据卷）
docker compose down

# 停 + 删卷（⚠️ 会清掉所有数据，包括用户、LLM 配置）
docker compose down -v

# 重启单服务
docker compose restart backend

# 看日志
docker compose logs -f backend
docker compose logs -f frontend

# 重建某服务（改了 Dockerfile 或代码必须 --build）
docker compose up -d --build backend

# 启用管理面板（Redis Commander / Mongo Express）
docker compose --profile management up -d
```

进数据库：

```bash
# MongoDB shell
docker exec -it tradingagents-mongodb mongo \
  -u admin -p tradingagents123 --authenticationDatabase admin tradingagentscn

# Redis CLI
docker exec -it tradingagents-redis redis-cli -a tradingagents123
```

---

## 🧑‍💻 本地源码开发模式（可选）

只有调试后端代码、要热重载时才用。生产/演示走 Docker 即可。

```bash
# 1. 起依赖
docker compose up -d mongodb redis

# 2. Python 虚拟环境 + 依赖
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. 跑后端（使用项目根目录的 run_server.py，里面会先 apply nest_asyncio 再起 uvicorn）
HOST=0.0.0.0 PORT=8000 python run_server.py
# 或者用 uvicorn 直接跑：python -m uvicorn app.main:app --reload --port 8000

# 4. 前端
cd frontend && npm install && npm run dev
# 访问 http://localhost:5173
```

本地跑后端时，`.env` 里的 `MONGODB_HOST` / `REDIS_HOST` 要改回 `localhost`。

---

## ❌ 历史踩坑记录

> 已修复的都列在这里，方便后续再碰到同类问题对照排查。

### ✅ 问题 1：容器之间连不上数据库

`localhost` 在容器里指向容器自己。`.env` 必须把 host 改成 compose 里的 service 名（`mongodb` / `redis`）。

### ✅ 问题 2：`docker-compose` 命令不存在

新版本 Docker Desktop 用 `docker compose`（空格），不是 `docker-compose`（连字符）。

### ✅ 问题 3：登录返回 405 Not Allowed

Nginx 缺 `/api` 反代规则，本次提交已在 `docker/nginx.conf` 补齐 `/api` 和 `/api/ws`（WebSocket）两段 location。

### ✅ 问题 4：登录提示"用户名或密码错误"

数据库里没用户。跑 `init_admin_user.py`（第 3.1 步）即可。

### ✅ 问题 5：分析时 `RuntimeError: this event loop is already running`

数据源代码（akshare、tushare 包装层）在 FastAPI 异步上下文里用 `loop.run_until_complete()` 套了一层同步调用，触发了嵌套事件循环。

修法：
1. `requirements.txt` 加上 `nest_asyncio>=1.5.0`
2. 新建 `run_server.py`，**必须先 `nest_asyncio.apply()` 再 `import uvicorn`**（uvicorn 在 import 阶段就会准备 event loop policy，迟了就来不及）
3. `Dockerfile.backend` 把 `CMD` 改成 `python run_server.py`
4. `app/main.py` 顶部 + `tradingagents/dataflows/data_source_manager.py` 顶部冗余加 `nest_asyncio.apply()`，给本地裸跑场景兜底

### ✅ 问题 6：数据源 fallback 返回 tuple 导致 `'tuple' object has no attribute 'split'`

`_try_fallback_sources` 在用备用源时会返回 `(result, source)` 元组，但调用方按字符串处理。已在 `data_source_manager.py` 的三处出口加 `isinstance(result, tuple)` 兜底拆包。

### ✅ 问题 7：前端模型下拉框是空的

后端按 `enabled=True AND provider IN 已激活供应商` 过滤模型。`llm_providers` 集合默认为空，所以即使在「系统设置 → 大模型配置」里加了模型，前端也看不到。

修法：手动在 MongoDB 里 `db.llm_providers.insertOne(...)` 把对应供应商激活（见第 3.2 步）。

### ✅ 问题 8：分析跑到"研究辩论"阶段 401 / "大模型 API Key 无效"

系统默认深度模型是 `qwen-max`，但很多人没配置这个模型，于是按"模型名以 qwen 开头"映射到阿里百炼 endpoint，用你自己的 OpenAI key 当然 401。

修法：把 `system_configs.settings.deep_analysis_model` / `deep_think_llm` 改成你已配置好的模型名（见第 3.4 步）。

### ⚠️ 已知次要问题：embedding 503

如果你的 OpenAI 兼容网关没配 `text-embedding-3-small` 渠道，日志会出现：

```
503 ... 分组 RD 下模型 text-embedding-3-small 无可用渠道
⚠️ 记忆功能降级，返回空向量
```

**不影响分析主流程**，只是 Agent 间的 memory 功能降级。要彻底解决就在网关侧给 `text-embedding-3-small` 配个渠道。

---

## ✅ 首次启动检查清单

环境：
- [ ] Docker Desktop 已启动
- [ ] `.env` 中所有 `*_HOST` 已改为容器名（不是 `localhost`）
- [ ] `JWT_SECRET` / `CSRF_SECRET` 已替换为强随机串

启动：
- [ ] `docker compose ps` 四个容器都 `healthy`
- [ ] `curl http://localhost:8000/api/health` 返回 200
- [ ] 前端 http://localhost:3000 可打开

初始化（**最容易漏，跑不通基本都是少了这几步**）：
- [ ] 跑过 `init_admin_user.py`，admin 能登录
- [ ] `llm_providers` 集合里至少有一条 `is_active: true` 的记录
- [ ] 「系统设置 → 大模型配置」里至少有一条 `enabled` 的模型
- [ ] `system_configs.settings.deep_analysis_model` 改成实际可用的模型名
- [ ] `.env` 至少配了一个数据源（推荐 Tushare）并重启过 backend

冒烟测试：
- [ ] 用 admin 登录前端
- [ ] 「股票分析」页面模型下拉框有内容
- [ ] 跑一只测试票（建议 600519）能完整出报告

---

## 📝 更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-06-11 | 初版文档；记录数据库连接、Docker 权限、`docker-compose` 命令等问题 |
| 2026-06-12 | 修复 event loop / 数据源 tuple / Nginx 反代问题；新增首次初始化全流程（账号、LLM Provider、默认模型、数据源）；补充问题 5-8 的根因和修法 |
