# LangChain ChatBI

LangChain-based refactoring of ChatBI agents with LangGraph orchestration.

## 项目结构

```
langchain_chatbi/
├── agents/              # LangChain 代理实现
│   ├── base.py         # 基础代理类
│   ├── intent_agent.py # 意图分类
│   ├── schema_agent.py # 模式选择
│   ├── sql_agent.py    # SQL 生成（带错误纠正）
│   ├── reasoning_agent.py   # 推理生成（支持流式）
│   ├── chart_agent.py  # 图表配置生成
│   ├── answer_agent.py      # 答案摘要（支持流式）
│   └── diagnosis_agent.py   # 数据洞察
├── graph/               # LangGraph 工作流
│   ├── state.py        # 状态定义
│   ├── nodes.py        # 代理节点函数
│   ├── edges.py        # 条件路由
│   └── workflow.py     # 编译后的图
├── models/              # Pydantic 响应模型
├── llm/                 # LLM 集成
├── tests/               # 单元测试
└── demos/               # 交互式演示
```

## 安装

### 1. 创建虚拟环境

```bash
cd langchain_chatbi
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt

# 或使用 pip install -e .
```

### 3. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.openai.com/v1"  # 可选
export LLM_MODEL="gpt-3.5-turbo"  # 可选
```

支持 OpenAI 兼容的 API：
- OpenAI
- DeepSeek
- 通义千问 (Qwen)
- 其他兼容的 API

## 使用

### 运行演示脚本

```bash
# 1. 意图分类演示
python demos/demo_intent_agent.py

# 2. 流式代理演示
python demos/demo_streaming_agents.py

# 3. 完整工作流演示
python demos/demo_full_workflow.py
```

### 运行单元测试

```bash
# 使用 mock LLM（不需要 API key）
pytest tests/test_agents.py -v

# 使用真实 LLM（需要 API key）
LLM_API_KEY="your-key" pytest tests/test_agents.py -v
```

### 代码示例

```python
import asyncio
from langchain_chatbi.llm.langchain_llm import create_langchain_llm
from langchain_chatbi.agents.intent_agent import IntentClassificationAgent

async def main():
    llm = create_langchain_llm()
    agent = IntentClassificationAgent(llm=llm)

    result = await agent.classify("上个月销售额是多少？")
    print(f"Intent: {result.intent}")
    print(f"Reasoning: {result.reasoning}")

asyncio.run(main())
```

## 工作流流程

```
用户问题
    │
    ▼
[intent_node] → 意图分类
    │ (query)          (greeting/help → END)
    ▼
[schema_node] → 模式选择
    │
    ▼
[reasoning_node] → 推理生成（流式）
    │
    ▼
[sql_node] → SQL 生成
    │
    ▼
[execution_node] → SQL 执行
    │ (error)         (success)
    ▼                  │
[sql_node] ←───────────┘ (重试，最多3次)
    │
    ▼
[chart_node] → 图表生成
    │
    ▼
[diagnosis_node] → 数据洞察
    │
    ▼
[answer_node] → 答案摘要（流式）
    │
    ▼
END
```

## 特性

- ✅ **LangChain 集成** - 使用 LangChain 原生消息格式
- ✅ **LangGraph 编排** - 状态图工作流编排
- ✅ **流式输出** - 推理和答案代理支持流式响应
- ✅ **SQL 错误纠正** - 自动重试（最多3次）
- ✅ **结构化输出** - Pydantic 模型确保类型安全
- ✅ **独立单元测试** - 每个代理可独立测试
- ✅ **交互式演示** - 可视化查看各代理输出

## 依赖

- Python >= 3.9
- langchain >= 0.1.0
- langchain-openai >= 0.0.5
- langgraph >= 0.0.26
- pydantic >= 2.5.0
- loguru >= 0.7.0

## 许可证

MIT
