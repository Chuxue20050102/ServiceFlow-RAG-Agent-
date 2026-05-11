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

## 4. 本地运行

首次使用时，先准备环境变量：

```powershell
copy backend_fastapi\.env.example backend_fastapi\.env
copy frontend_vue\.env.example frontend_vue\.env.local
```

填写 `backend_fastapi/.env` 里的模型 API 配置后，一键启动 MySQL、后端和前端：

```powershell
.\scripts\start-dev.ps1
```

本地端口：

- EmoChat 后端：`8000`
- ServiceFlow 后端：`8010`
- ServiceFlow 前端：`5173`
- ServiceFlow MySQL：`3307`

## 5. 演示流程

1. 打开前端页面 `http://127.0.0.1:5173`
2. 在规则知识库页面上传 `samples/after_sales_rules.md`
3. 在工单上传页面上传 `samples/tickets.csv`
4. 点击 AI 分析，等待任务完成
5. 查看统计图表、工单处理建议和 Agent Trace

## API 概览

基础路径：

```text
/api/serviceflow
```

主要接口：

- `POST /knowledge/upload`：上传知识文档
- `GET /knowledge`：知识文档列表
- `POST /tickets/upload`：上传工单批次
- `POST /tickets/{batch_id}/analyze`：提交后台 AI 分析任务
- `GET /tickets/{batch_id}/analyze/status`：查询 AI 分析进度
- `GET /tickets/{batch_id}/summary`：统计汇总
- `GET /tickets/{batch_id}/items`：工单分析明细
- `POST /tickets/{batch_id}/report`：生成日报
- `GET /tickets/{batch_id}/report`：获取日报
