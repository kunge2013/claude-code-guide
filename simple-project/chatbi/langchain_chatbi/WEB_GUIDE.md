# LangChain ChatBI Web Interface Guide

## Web 界面使用指南

### 目录
- [环境配置](#环境配置)
- [启动步骤](#启动步骤)
- [功能说明](#功能说明)
- [API 接口](#api-接口)
- [故障排查](#故障排查)

---

## 环境配置

### 1. 系统要求

- Python 3.9+
- pip 包管理器
- 至少 2GB 可用内存

### 2. 安装依赖

```bash
cd /home/fk/workspace/github/claude_guide/simple-project/chatbi/langchain_chatbi
pip install -r requirements.txt
```

**核心依赖包：**
- `langchain>=0.1.0` - LangChain 核心库
- `langchain-openai>=0.0.5` - OpenAI 集成
- `langgraph>=0.0.26` - LangGraph 工作流编排
- `langchain-core>=0.1.0` - LangChain 核心组件
- `flask>=3.0.0` - Web 框架
- `pydantic>=2.5.0` - 数据验证
- `loguru>=0.7.0` - 日志记录

### 3. 环境变量配置

创建 `.env` 文件或设置环境变量：

```bash
# OpenAI API 配置
export LLM_API_KEY="your-openai-api-key-here"
export LLM_BASE_URL="https://api.openai.com/v1"  # 可选，默认为 OpenAI
export LLM_MODEL="gpt-3.5-turbo"                  # 可选，默认为 gpt-3.5-turbo

# 代理设置（可选）
export HTTP_PROXY="http://your-proxy:port"
export HTTPS_PROXY="http://your-proxy:port"

# 或者使用国内镜像
export HF_ENDPOINT="https://hf-mirror.com"
```

**注意：** 如果没有设置 `LLM_API_KEY`，系统将使用模拟模式，但无法进行真实的 LLM 调用。

---

## 启动步骤

### 方法 1: 使用启动脚本（推荐）

```bash
cd /home/fk/workspace/github/claude_guide/simple-project/chatbi/langchain_chatbi
bash start_web.sh
```

### 方法 2: 直接运行 Python

```bash
cd /home/fk/workspace/github/claude_guide/simple-project/chatbi/langchain_chatbi
python web/app.py
```

### 方法 3: 开发模式启动

```bash
export FLASK_APP=web/app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### 启动成功标志

看到以下输出表示启动成功：

```
* Serving Flask app 'app'
* Debug mode: on
* Running on all addresses (0.0.0.0)
* Running on http://127.0.0.1:5000
* Running on http://192.168.x.x:5000
```

---

## 功能说明

### Web 界面访问

启动成功后，在浏览器中打开：

```
http://localhost:5000
```

### 主要功能

1. **实时 Agent 状态监控**
   - 可视化工作流执行过程
   - 实时显示每个 Agent 的运行状态
   - 彩色标识：待执行(灰色) → 执行中(蓝色) → 完成(绿色) → 失败(红色)

2. **Agent 执行详情**
   - Intent: 意图分类结果
   - Reasoning: 查询推理过程
   - SQL: 生成的 SQL 语句
   - Execution: SQL 执行结果
   - Chart: 图表配置
   - Diagnosis: 数据洞察
   - Answer: 自然语言答案

3. **示例查询**
   - "Show me the top 5 products by sales"
   - "What is the total revenue by month?"
   - "List all customers who made purchases over $1000"

### 工作流流程图

```
用户问题
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                     LangGraph 工作流                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐                                           │
│  │ Intent Node │ → 意图分类                                 │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ Schema Node │ → 表结构选择                               │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │ Reasoning    │ → 查询推理                                │
│  │    Node      │                                          │
│  └──────┬───────┘                                          │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │   SQL Node  │ → SQL 生成                                │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐         ┌──────────────┐                │
│  │ Execution    │────────→│    SQL Node  │ (重试)         │
│  │    Node      │  错误   │   (最多3次)   │                │
│  └──────┬───────┘         └──────────────┘                │
│         │ 成功                                              │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ Chart Node  │ → 图表配置生成                             │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │ Diagnosis    │ → 数据洞察                                │
│  │    Node      │                                          │
│  └──────┬───────┘                                          │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ Answer Node │ → 答案生成                                │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│     END                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API 接口

### 1. 执行查询

**POST** `/api/execute`

请求体：
```json
{
  "question": "Show me the top 5 products by sales",
  "language": "zh-CN"
}
```

响应：
```json
{
  "status": "started"
}
```

### 2. 获取状态

**GET** `/api/status`

响应：
```json
{
  "status": "completed",
  "current_node": null,
  "nodes_completed": [...],
  "nodes_failed": [],
  "results": {...},
  "start_time": "2026-01-19T18:16:45.123456",
  "end_time": "2026-01-19T18:16:50.123456",
  "total_events": 8
}
```

### 3. 实时状态流（SSE）

**GET** `/api/stream`

Server-Sent Events 流，用于实时更新状态。

### 4. 重置执行

**POST** `/api/reset`

重置执行状态。

---

## 故障排查

### 问题 1: 端口被占用

**错误信息：**
```
Address already in use
Port 5000 is in use by another program.
```

**解决方案：**

1. 查找占用端口的进程：
```bash
lsof -i :5000
# 或
netstat -tlnp | grep 5000
```

2. 杀死占用进程：
```bash
kill -9 <PID>
```

3. 或使用其他端口：
```bash
python web/app.py --port 5001
```

### 问题 2: API Key 未设置

**错误信息：**
```
LLM_API_KEY not set. Using mock mode.
```

**解决方案：**

```bash
export LLM_API_KEY="sk-your-actual-api-key"
# 然后重启服务器
```

### 问题 3: 依赖包缺失

**错误信息：**
```
ModuleNotFoundError: No module named 'langchain'
```

**解决方案：**

```bash
pip install -r requirements.txt
```

### 问题 4: 权限错误

**错误信息：**
```
Permission denied
```

**解决方案：**

```bash
chmod +x start_web.sh
```

### 问题 5: 工作流卡住不动

**可能原因：**
- LLM API 调用超时
- 网络连接问题
- 异步处理问题

**解决方案：**

1. 检查网络连接
2. 检查 API Key 是否有效
3. 增加超时时间（修改代码中的 timeout 参数）
4. 查看日志输出定位具体卡住的节点

---

## 开发模式

### 启用调试模式

```bash
export FLASK_ENV=development
python web/app.py
```

调试模式特性：
- 自动重载代码变更
- 详细的错误堆栈
- 调试器支持

### 日志级别设置

在 `web/app.py` 中设置：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 性能优化

### 1. 使用连接池

修改 `langchain_chatbi/llm/langchain_llm.py`：

```python
# 增加 max_connections
llm = ChatOpenAI(
    model=model,
    base_url=base_url,
    temperature=temperature,
    max_connections=20
)
```

### 2. 启用缓存

在 agent 中添加缓存层：

```python
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

set_llm_cache(InMemoryCache())
```

### 3. 并发处理

使用 `threading` 或 `asyncio` 处理多个并发请求。

---

## 安全建议

1. **不要在生产环境使用 Debug 模式**
2. **使用环境变量管理敏感信息**
3. **添加 API 认证**
4. **设置 CORS 策略**
5. **使用 HTTPS**
6. **添加请求频率限制**

---

## 生产部署

### 使用 Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web.app:app
```

### 使用 uWSGI

```bash
pip install uwsgi
uwsgi --http :5000 --wsgi-file app.py --callable app --processes 4
```

### Docker 部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "web.app:app"]
```

---

## 联系支持

- 问题反馈: [GitHub Issues](https://github.com/your-repo/issues)
- 文档: [项目 Wiki](https://github.com/your-repo/wiki)
