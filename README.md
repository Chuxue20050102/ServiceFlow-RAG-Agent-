# ServiceFlow RAG Agent

ServiceFlow RAG Agent 是一个面向客服与售后场景的 AI 工单分析系统。系统支持上传售后规则、FAQ、客服处理流程等知识文档，并上传 Excel / CSV 工单批次；后端会基于 RAG 检索相关规则，再调用大模型完成工单分类、严重程度判断、责任团队分流、处理建议、客服回复模板和日报生成。

当前项目采用前后端分离架构：

- `frontend_vue/`：Vue 3 + Vite 前端工作台
- `backend_fastapi/`：FastAPI 后端 API 服务
- MySQL：存储知识文档、工单批次、工单明细、AI 分析结果和日报
- FAISS：存储售后规则切片向量，用于本地语义检索
- OpenAI-compatible API：用于文本 embedding 和工单分析生成

## 1. 架构说明

### 业务流程

1. 客服或运营人员在前端上传售后规则、FAQ、服务流程等知识文档。
2. 后端解析文档文本，将内容切分为规则片段，并调用 embedding 模型生成向量。
3. 向量写入本地 FAISS 索引，同时保存规则片段元数据。
4. 用户上传客服工单 Excel / CSV 文件，系统将工单批次与明细写入 MySQL。
5. 点击分析后，后端逐条读取工单内容。
6. 每条工单先通过 FAISS 检索最相关的售后规则片段。
7. 后端将“工单内容 + 命中的规则上下文”拼接为 Prompt，调用大模型生成结构化 JSON。
8. 后端校验 JSON 结构，并将分析结果保存到 MySQL。
9. 前端展示统计概览、工单分析详情、Agent Trace 和日报预览。

### 模块职责

后端核心目录：

- `app/main.py`：FastAPI 应用入口、CORS、路由注册、启动时建表
- `app/api/routes/serviceflow.py`：知识库、工单上传、分析、统计、日报 API
- `app/services/knowledge_service.py`：知识文档上传、文本切分、向量化入口
- `app/services/vector_service.py`：FAISS 索引读写、相似规则检索
- `app/services/ticket_service.py`：工单文件上传和批次入库
- `app/services/rag_service.py`：RAG 分析主流程、Prompt 构造、结果解析、日报生成
- `app/services/ai_client.py`：OpenAI-compatible Chat Completions 和 Embeddings 调用
- `app/models/serviceflow.py`：SQLAlchemy 数据模型
- `app/schemas/serviceflow.py`：API 响应和 AI 输出校验 Schema

前端核心目录：

- `src/api/serviceflow.ts`：ServiceFlow API 封装
- `src/pages/KnowledgePage.vue`：知识库上传与列表
- `src/pages/TicketUploadPage.vue`：工单批次上传
- `src/pages/TicketResultPage.vue`：分析结果、统计图表、Trace 展示
- `src/pages/TicketReportPage.vue`：日报生成与预览

### 当前本地端口规划

- EmoChat 后端：`8000`
- ServiceFlow 后端：`8010`
- ServiceFlow 前端：`5173`
- ServiceFlow MySQL：`3307`

ServiceFlow 前端 API 地址通过 `frontend_vue/.env.local` 指向：

```env
VITE_API_BASE_URL=http://127.0.0.1:8010/api/serviceflow
```

## 2. 关键 Prompt 与 Vibe 思路

### Prompt 目标

本项目的 Prompt 不是开放聊天式问答，而是面向客服工单处理的“结构化业务决策 Prompt”。它的目标是让模型在售后规则约束下输出稳定、可落库、可统计、可复核的 JSON。

核心设计思路：

- 先检索规则，再生成结论，降低模型凭空判断的概率。
- 明确限定 `ticket_type`、`severity`、`responsible_team` 的候选范围，减少分类漂移。
- 要求只返回 JSON，不返回 Markdown 或解释文字，方便后端直接解析。
- 同时保留 `raw_ai_result`、`matched_rules`、`parse_success` 和 `parse_error`，便于人工复核 Agent Trace。
- 失败时不阻断整批任务，而是生成兜底分析结果，并标记需要人工处理。

### 当前分析 Prompt 摘要

Prompt 构造位置：

```text
backend_fastapi/app/services/rag_service.py
```

核心输入：

- `matched_rules`：FAISS 检索出的售后规则片段
- `content`：当前用户工单内容

模型需要输出字段：

```json
{
  "ticket_type": "支付/到账异常",
  "severity": "高",
  "responsible_team": "技术团队 / 客服团队",
  "summary": "用户反馈付款后会员未到账",
  "suggestion": "建议先核查支付记录，再检查会员状态同步",
  "reply_template": "您好，我们已收到您的问题，会优先为您核查付款记录和会员状态，请您稍等。"
}
```

### Vibe 思路

ServiceFlow 的产品气质不是“聊天机器人”，而是“客服团队的工单副驾驶”。因此交互和 AI 输出都围绕下面几个关键词设计：

- 克制：不强调炫技，优先给客服可执行的判断和建议。
- 可追溯：每条结论都展示命中的规则和模型原始输出。
- 可复核：解析失败不会伪装成功，而是明确标记人工复核。
- 面向批处理：系统按批次上传、批次分析、批次统计，适合客服主管做日常运营复盘。
- 低打扰：AI 先完成分类、分流、摘要、回复模板等重复劳动，最终处理权仍交给客服人员。

## 3. AI 调用逻辑

### Embedding 调用

知识文档上传后，后端会：

1. 解析上传文件文本。
2. 将文本切分为多个规则片段。
3. 调用 `client.embeddings.create(...)` 生成向量。
4. 使用 FAISS `IndexFlatIP` 保存向量。
5. 查询时对 query 向量做 L2 normalize，并检索 Top 3 规则片段。

相关文件：

```text
backend_fastapi/app/services/ai_client.py
backend_fastapi/app/services/vector_service.py
backend_fastapi/app/services/knowledge_service.py
```

### Chat Completions 调用

每条工单分析时，后端会：

1. 调用 `search_rule_chunks(content)` 检索相关规则。
2. 调用 `build_analysis_prompt(content, matched_rules)` 生成 Prompt。
3. 使用 OpenAI SDK 的 `client.chat.completions.create(...)` 调用模型。
4. 设置 `temperature=0.2`，让输出更稳定。
5. 提取模型回复中的 JSON。
6. 使用 Pydantic Schema 校验并落库。

当前调用方式：

- 使用 Chat Completions
- 非流式调用
- 未使用 function calling / tool calling
- 未使用多 Agent 编排
- 使用 RAG + JSON Schema 校验来保证业务结果稳定性

### 为什么暂未使用流式输出

当前任务是批量工单分析，前端更关心“整批任务完成后查看统计与明细”，而不是逐 token 展示模型生成过程。因此当前使用非流式调用，逻辑更简单，也更利于失败重试、结果校验和数据库一致性。

后续如果要优化体验，可以将 `/tickets/{batch_id}/analyze` 改为异步任务，并通过 WebSocket、SSE 或轮询返回每条工单的处理进度。

### 为什么暂未使用 function calling

当前模型输出目标非常固定，只需要生成一个结构化 JSON，后端再用 Pydantic 校验即可。function calling 更适合模型需要主动选择工具、查询外部系统或执行多步骤动作的场景。

后续可以扩展的 function calling 工具包括：

- 查询订单状态
- 查询支付流水
- 查询用户会员状态
- 创建客服转派任务
- 写入 CRM 跟进记录

## 4. 部署步骤说明

### 环境要求

- Python 3.11+，当前本地使用 Python 3.13 虚拟环境
- Node.js `^20.19.0 || >=22.12.0`
- MySQL 8.0
- Windows / Linux / macOS 均可部署

### 后端配置

进入后端目录：

```powershell
cd C:\HomeWork\agent\insightflow-agent\backend_fastapi
```

创建并激活虚拟环境：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

创建 `.env`：

```env
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3307/serviceflow_agent
UPLOAD_DIR=uploads
VECTOR_STORE_DIR=vector_store

OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_MODEL=your-chat-model
OPENAI_EMBEDDING_MODEL=your-embedding-model
```

启动后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

健康检查：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8010/health
```

### 前端配置

进入前端目录：

```powershell
cd C:\HomeWork\agent\insightflow-agent\frontend_vue
```

安装依赖：

```powershell
npm install
```

创建 `.env.local`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8010/api/serviceflow
```

本地开发启动：

```powershell
npm run dev -- --host 0.0.0.0
```

生产构建：

```powershell
npm run build
```

构建产物在：

```text
frontend_vue/dist/
```

### MySQL 部署

本地可使用 Docker 运行 MySQL，并将宿主机 `3307` 映射到容器 `3306`：

```powershell
docker run -d --name serviceflow-mysql `
  -e MYSQL_ROOT_PASSWORD=password `
  -e MYSQL_DATABASE=serviceflow_agent `
  -p 3307:3306 `
  mysql:8.0
```

如果容器已存在但停止：

```powershell
docker start serviceflow-mysql
```

后端启动时会根据 SQLAlchemy 模型自动创建表。

### 生产部署建议

推荐部署方式：

- 前端：使用 Nginx 托管 `frontend_vue/dist`
- 后端：使用 Uvicorn / Gunicorn + Uvicorn Worker 运行 FastAPI
- 数据库：使用独立 MySQL 实例
- 静态上传文件和 `vector_store`：挂载持久化目录
- API 域名：建议使用 `api.example.com`
- 前端域名：建议使用 `serviceflow.example.com`

Nginx 反向代理示例：

```nginx
server {
    listen 80;
    server_name serviceflow.example.com;

    root /var/www/serviceflow/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

生产环境前端 `.env.production` 示例：

```env
VITE_API_BASE_URL=https://api.example.com/api/serviceflow
```

### DNS 说明

如果正式上线，需要在域名服务商处添加 DNS 解析：

- `serviceflow.example.com`：A 记录指向前端服务器公网 IP
- `api.example.com`：A 记录指向后端服务器公网 IP

如果前后端部署在同一台服务器，也可以两个域名都解析到同一个 IP，再由 Nginx 按 `server_name` 分发。

如果只是临时演示，可以使用 natapp、ngrok、Cloudflare Tunnel 等内网穿透工具。但要注意：

- EmoChat 当前使用 `8000` 给 natapp 转发。
- ServiceFlow 后端已调整为 `8010`，避免抢占 EmoChat 的 `8000`。
- 如果要公网访问 ServiceFlow API，需要将穿透目标指向 `127.0.0.1:8010`。

### HTTPS 说明

生产环境建议全站启用 HTTPS。常见方式：

1. DNS 解析生效后，在服务器安装 Nginx。
2. 使用 Certbot 申请 Let's Encrypt 证书。
3. 将 `http://` 自动重定向到 `https://`。
4. 前端 `VITE_API_BASE_URL` 使用 HTTPS API 地址。
5. 后端 CORS 需要加入正式前端域名，例如：

```python
allow_origins=[
    "https://serviceflow.example.com",
]
```

Certbot 示例：

```bash
sudo certbot --nginx -d serviceflow.example.com -d api.example.com
```

HTTPS 上线后，浏览器会阻止 HTTPS 页面请求 HTTP API，因此前端和后端都应使用 HTTPS。

## API 概览

基础路径：

```text
/api/serviceflow
```

主要接口：

- `GET /ping`：服务连通性检查
- `POST /knowledge/upload`：上传知识文档
- `GET /knowledge`：查看知识文档列表
- `POST /tickets/upload`：上传工单批次
- `POST /tickets/{batch_id}/analyze`：触发批量 AI 分析
- `GET /tickets/{batch_id}/summary`：获取统计汇总
- `GET /tickets/{batch_id}/items`：获取工单分析明细
- `POST /tickets/{batch_id}/report`：生成客服日报
- `GET /tickets/{batch_id}/report`：获取最新日报

## 开发备注

- 当前后端 CORS 已允许 `http://localhost:5173`、`http://127.0.0.1:5173`、`http://localhost:5174`、`http://127.0.0.1:5174`。
- 本地 ServiceFlow 后端建议固定使用 `8010`，避免和 EmoChat 的 `8000` 冲突。
- `uploads/`、`vector_store/`、`.env`、`.venv/` 不应提交到版本库。
- 前端生产构建已验证可通过 `npm run build` 完成。
