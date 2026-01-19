# LangChain ChatBI - 智能数据分析系统

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)](https://langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0+-orange.svg)](https://github.com/langchain-ai/langgraph)

基于 LangChain 和 LangGraph 的智能商业智能（BI）系统，支持自然语言查询数据库并生成可视化图表。

## ✨ 特性

- 🤖 **多 Agent 协作**: 7 个专用 Agent 协同工作完成复杂查询
- 🔄 **工作流编排**: 使用 LangGraph 实现状态驱动的 Agent 工作流
- 📊 **可视化配置**: 自动生成 ECharts 图表配置
- 🌐 **Web 界面**: 实时监控 Agent 执行状态
- 🔧 **SQL 错误自动纠正**: 最多 3 次重试机制
- 🌍 **多语言支持**: 中文/英文切换
- 📡 **流式输出**: 支持实时流式响应

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入 (自然语言)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph 工作流                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Intent Agent        → 意图分类 (查询/问候/帮助)              │
│  2. Schema Agent        → 选择相关数据表                         │
│  3. Reasoning Agent     → 生成查询推理计划                       │
│  4. SQL Agent           → 生成 SQL 查询                          │
│  5. Execution Node      → 执行 SQL (错误重试机制)                │
│  6. Chart Agent         → 生成图表配置                           │
│  7. Diagnosis Agent     → 提取数据洞察                           │
│  8. Answer Agent        → 生成自然语言答案                       │
│                                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        输出结果                                   │
│  • SQL 查询                                                     │
│  • 查询结果数据                                                  │
│  • ECharts 图表配置                                              │
│  • 数据洞察分析                                                  │
│  • 自然语言答案                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 目录结构

```
langchain_chatbi/
├── agents/                    # Agent 实现
│   ├── __init__.py
│   ├── base.py               # 基础 Agent 类
│   ├── intent_agent.py       # 意图分类 Agent
│   ├── schema_agent.py       # 表结构选择 Agent
│   ├── sql_agent.py          # SQL 生成 Agent
│   ├── reasoning_agent.py    # 查询推理 Agent
│   ├── chart_agent.py        # 图表生成 Agent
│   ├── diagnosis_agent.py    # 数据洞察 Agent
│   └── answer_agent.py       # 答案生成 Agent
├── chains/                    # LangChain 链定义
├── graph/                     # LangGraph 工作流
│   ├── state.py              # 状态定义
│   ├── nodes.py              # 节点函数
│   ├── edges.py              # 条件路由
│   └── workflow.py           # 编译后的工作流
├── prompts/                   # 提示词模板
├── models/                    # Pydantic 数据模型
├── llm/                       # LLM 集成
│   └── langchain_llm.py      # LangChain LLM 包装器
├── observability/             # 可观测性集成
├── tests/                     # 单元测试
│   ├── conftest.py           # Pytest 配置
│   └── test_agents.py        # Agent 测试
├── demos/                     # 交互式演示脚本
├── web/                       # Web 界面
│   ├── app.py                # Flask 应用
│   └── templates/
│       └── index.html        # 监控面板
├── config/                    # 配置文件
├── utils/                     # 工具函数
├── requirements.txt           # Python 依赖
├── setup.py                   # 包安装配置
├── start_web.sh              # Web 启动脚本
├── WEB_GUIDE.md             # Web 使用指南
└── README_CN.md             # 本文档
```

## 🚀 快速开始

### 1. 安装

```bash
cd langchain_chatbi
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export LLM_API_KEY="your-openai-api-key"
export LLM_BASE_URL="https://api.openai.com/v1"  # 可选
export LLM_MODEL="gpt-3.5-turbo"                 # 可选
```

### 3. 运行单元测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_agents.py -v

# 查看测试覆盖率
pytest --cov=langchain_chatbi tests/
```

### 4. 运行演示脚本

```bash
# Intent 分类演示
python demos/demo_intent_agent.py

# SQL 生成演示
python demos/demo_sql_agent.py

# 流式 Agent 演示
python demos/demo_streaming_agents.py

# 完整工作流演示
python demos/demo_full_workflow.py
```

### 5. 启动 Web 界面

```bash
# 使用启动脚本
bash start_web.sh

# 或直接运行
python web/app.py
```

然后访问 http://localhost:5000

## 📖 使用示例

### Python API

```python
from langchain_chatbi import create_chatbi_graph
from langchain_chatbi.llm import create_langchain_llm

# 创建 LLM 和工作流
llm = create_langchain_llm()
graph = create_chatbi_graph()

# 配置
config = {
    "configurable": {
        "thread_id": "session-123"
    }
}

# 初始状态
initial_state = {
    "question": "显示销售额前5的产品",
    "session_id": "session-123",
    "language": "zh-CN",
    "messages": [],
    "table_schemas": [
        {
            "name": "products",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "VARCHAR"},
                {"name": "sales", "type": "REAL"}
            ]
        }
    ],
    "db": None,  # 或传入数据库连接
    "sql_retry_count": 0,
    "should_stop": False
}

# 执行工作流
for event in graph.stream(initial_state, config=config):
    for node_name, node_output in event.items():
        print(f"Node: {node_name}")
        print(f"Output: {node_output}")
```

### Web 界面查询

在浏览器中打开 http://localhost:5000，输入问题：

- "显示销售额前5的产品"
- "按月统计总收入"
- "列出消费超过1000元的客户"

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_agents.py::test_intent_agent -v

# 查看详细输出
pytest tests/ -v -s

# 并行运行测试
pytest tests/ -n auto
```

## 🔧 配置说明

### LLM 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `LLM_API_KEY` | OpenAI API 密钥 | 必填 |
| `LLM_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-3.5-turbo` |
| `LLM_TEMPERATURE` | 温度参数 | `0.7` |

### 数据库配置

```python
db_config = {
    "type": "sqlite",  # 或 postgresql, mysql
    "connection": "sqlite:///database.db"
}
```

## 📊 Agent 详解

### 1. IntentClassificationAgent

**功能**: 分类用户意图

**输出**:
```python
{
    "intent": "query",  # query, greeting, help, unknown
    "reasoning": "用户询问数据查询",
    "confidence": 0.95
}
```

### 2. SchemaAgent

**功能**: 选择相关数据表

**输入**:
- 用户问题
- 可用表列表

**输出**: 相关表的子集

### 3. QueryReasoningAgent

**功能**: 生成查询推理计划

**特性**: 支持流式输出

### 4. SqlAgent

**功能**: 生成 SQL 查询

**特性**:
- 错误自动纠正
- 最多 3 次重试

### 5. ChartGenerationAgent

**功能**: 生成 ECharts 图表配置

**支持的图表类型**:
- bar (柱状图)
- line (折线图)
- pie (饼图)
- scatter (散点图)
- table (表格)

### 6. DiagnosisAgent

**功能**: 提取数据洞察

**输出**:
```python
{
    "summary": "销售额Top产品是...",
    "key_findings": [...],
    "recommendations": [...]
}
```

### 7. AnswerSummarizationAgent

**功能**: 生成自然语言答案

**特性**: 支持流式输出

## 🐛 故障排查

### 问题: 工作流卡住不动

**原因**: LLM API 调用超时或网络问题

**解决**:
1. 检查网络连接
2. 验证 API Key 是否有效
3. 检查 LLM_BASE_URL 配置

### 问题: SQL 执行失败

**原因**: 表结构不匹配或 SQL 语法错误

**解决**:
1. 确保 table_schemas 正确
2. 查看诊断日志
3. 系统会自动重试最多 3 次

### 问题: 单元测试失败

**原因**: 依赖版本不兼容

**解决**:
```bash
pip install -r requirements.txt --upgrade
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [OpenAI](https://openai.com/)

---

**更新日期**: 2026-01-19
**版本**: 1.0.0
