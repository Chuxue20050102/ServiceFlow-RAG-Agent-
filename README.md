# ServiceFlow RAG Agent

ServiceFlow RAG Agent 是一个面向客服 / 售后场景的 AI 工单分析系统。用户可以上传售后规则、FAQ、处理流程等知识文档，再上传 Excel / CSV 工单批次；系统会基于 RAG 检索相关规则，并调用大模型生成工单分类、严重程度、责任团队、处理建议和客服回复模板。

## 项目截图

![ServiceFlow 分析结果](docs/images/serviceflow-result.png)

## 1. 架构说明

- 前端：`frontend_vue/`，Vue 3 + Vite
- 后端：`backend_fastapi/`，FastAPI
- 数据库：MySQL，存储知识文档、工单、分析结果和日报
- 向量库：FAISS，本地保存规则片段向量
- AI：OpenAI-compatible API，用于 Embedding 和 Chat Completions

核心流程：

1. 上传知识文档，后端解析文本并切分规则片段。
2. 调用 Embedding 模型生成向量，写入 FAISS。
3. 上传工单批次，工单明细写入 MySQL。
4. 分析时先检索相关规则，再将规则和工单内容拼入 Prompt。
5. 大模型返回结构化 JSON，后端校验后保存分析结果。

## 2. 关键 Prompt 与 Vibe 思路

Prompt 位于：

```text
backend_fastapi/app/services/rag_service.py
```

设计思路：

- 先检索售后规则，再让模型分析工单，减少凭空判断。
- 限定 `ticket_type`、`severity`、`responsible_team` 的可选范围。
- 要求模型只返回 JSON，方便后端解析和入库。
- 保留 `matched_rules`、`raw_ai_result`、`parse_success`、`parse_error`，方便人工复核 Agent Trace。

产品 Vibe：不是聊天机器人，而是客服团队的“工单副驾驶”。它优先提供可执行、可追溯、可复核的处理建议，帮助客服减少重复判断。

## 3. AI 调用逻辑

相关文件：

```text
backend_fastapi/app/services/ai_client.py
backend_fastapi/app/services/vector_service.py
backend_fastapi/app/services/rag_service.py
```

当前实现：

- Embedding：知识片段和工单 query 调用 `client.embeddings.create(...)`
- RAG：FAISS 检索 Top 3 相关规则片段
- 生成：调用 `client.chat.completions.create(...)`
- 温度：`temperature=0.2`
- 输出：模型返回 JSON，后端用 Pydantic 校验

当前未使用：

- 流式输出：批量工单分析更关注完整结果，所以暂未逐 token 返回
- function calling：当前只需要固定 JSON 输出，后续可扩展为查询订单、支付流水、用户状态等工具调用

## 4. 部署步骤说明

### 后端

```powershell
cd C:\HomeWork\agent\insightflow-agent\backend_fastapi
py -m venv .venv
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

启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

### 前端

```powershell
cd C:\HomeWork\agent\insightflow-agent\frontend_vue
npm install
```

创建 `.env.local`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8010/api/serviceflow
```

启动开发服务：

```powershell
npm run dev -- --host 0.0.0.0
```

生产构建：

```powershell
npm run build
```

### 端口

- EmoChat 后端：`8000`
- ServiceFlow 后端：`8010`
- ServiceFlow 前端：`5173`
- ServiceFlow MySQL：`3307`

### DNS / HTTPS

生产环境建议：

- 前端域名：`serviceflow.example.com`
- 后端 API 域名：`api.example.com`
- DNS 中分别添加 A 记录，指向服务器公网 IP
- 使用 Nginx 托管前端 `dist/`，并反向代理后端 `127.0.0.1:8010`
- 使用 Certbot / Let's Encrypt 开启 HTTPS
- HTTPS 上线后，前端 `VITE_API_BASE_URL` 应改为：

```env
VITE_API_BASE_URL=https://api.example.com/api/serviceflow
```

后端 CORS 也需要加入正式前端域名。

## API 概览

基础路径：

```text
/api/serviceflow
```

主要接口：

- `POST /knowledge/upload`：上传知识文档
- `GET /knowledge`：知识文档列表
- `POST /tickets/upload`：上传工单批次
- `POST /tickets/{batch_id}/analyze`：批量 AI 分析
- `GET /tickets/{batch_id}/summary`：统计汇总
- `GET /tickets/{batch_id}/items`：工单分析明细
- `POST /tickets/{batch_id}/report`：生成日报
- `GET /tickets/{batch_id}/report`：获取日报
