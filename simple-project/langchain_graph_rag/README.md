# MySQL 表关系知识图谱

一个基于 LangChain、Neo4j 和 Flask 的知识图谱系统，用于可视化和管理 MySQL 数据库表之间的关系。

## 功能特性

- 📊 **可视化图谱**: 使用 Cytoscape.js 交互式展示表关系
- 🔍 **路径查询**: 查找两个表之间的最短连接路径
- 🤝 **邻居查询**: 查找与指定表相关的所有表
- 🤖 **AI 解释**: 使用 LangChain LLM 生成自然语言解释
- 💾 **多数据源**: 支持 MySQL 数据库和静态配置文件
- 🎨 **语义标注**: 自动识别表类型（事实表、维度表等）

## 技术栈

- **后端**: Python 3.9+, Flask, LangChain
- **图数据库**: Neo4j
- **前端**: Cytoscape.js, HTML5, CSS3
- **数据提取**: PyMySQL, PyYAML
- **LLM**: OpenAI GPT / 智谱 AI GLM

## 项目结构

```
langchain_graph_rag/
├── src/langchain_graph_rag/
│   ├── models/          # Pydantic 数据模型
│   ├── extractors/      # 数据提取层
│   ├── graph/           # 图谱构建层
│   ├── agents/          # LangChain Agents
│   ├── services/        # 查询服务
│   ├── web/             # Flask Web 应用
│   ├── llm/             # LLM 配置
│   └── utils/           # 工具模块
├── config/              # 配置文件
├── tests/               # 测试文件
├── scripts/             # 脚本工具
└── requirements.txt     # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name

# LLM 配置 (可选)
OPENAI_API_KEY=your_openai_api_key
# 或使用智谱 AI
ZHIPUAI_API_KEY=your_zhipuai_api_key
```

### 3. 启动 Neo4j

确保 Neo4j 正在运行：

```bash
# 使用 Docker
docker run -d \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    neo4j:latest
```

### 4. 初始化图谱

```bash
python scripts/init_graph.py
```

### 5. 启动 Web 服务

```bash
python scripts/run_server.py
```

访问 `http://localhost:5001` 查看图谱可视化。

## 使用说明

### 图谱可视化

主页显示完整的表关系图谱：
- 拖动节点可以重新布局
- 点击节点查看详细信息
- 使用控制栏按钮进行操作

### 路径查询

在"关系查询"页面：
1. 输入起始表和目标表名称
2. 选择最大跳数
3. 点击"查找路径"
4. 查看路径说明和 SQL JOIN 提示

### 邻居查询

1. 输入表名
2. 选择搜索深度
3. 点击"查找邻居"
4. 查看所有相关表及其关系

## 配置文件

### config/graph_config.yaml

图谱构建和可视化配置：

```yaml
graph:
  storage:
    type: neo4j  # neo4j 或 networkx

  build:
    auto_enrich: true  # 自动推断语义关系
    infer_relations: true  # 推断隐藏关系

entities:
  table_mappings:
    orders: "订单"
    customers: "客户"
```

### config/data_sources.yaml

数据源配置，支持 MySQL 和静态配置：

```yaml
mysql_sources:
  - name: "primary_db"
    host: ${MYSQL_HOST}
    port: ${MYSQL_PORT}
    # ...

static_schema:
  tables:
    - name: "orders"
      columns: [...]
  relations:
    - from_table: "orders"
      # ...
```

## API 文档

### REST API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/graph/nodes` | GET | 获取所有节点 |
| `/api/graph/edges` | GET | 获取所有边 |
| `/api/graph/path` | POST | 查找路径 |
| `/api/graph/neighbors` | POST | 查找邻居 |
| `/api/graph/statistics` | GET | 获取统计信息 |
| `/api/graph/relations/<table>` | GET | 获取表关系 |
| `/api/graph/search` | GET | 搜索表 |

### 请求示例

**路径查询:**

```bash
curl -X POST http://localhost:5001/api/graph/path \
  -H "Content-Type: application/json" \
  -d '{
    "start_table": "orders",
    "end_table": "products",
    "max_hops": 5
  }'
```

**邻居查询:**

```bash
curl -X POST http://localhost:5001/api/graph/neighbors \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "customers",
    "depth": 1
  }'
```

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_extractors/

# 生成覆盖率报告
pytest --cov=src/langchain_graph_rag --cov-report=html
```

### 代码结构

- **models/**: Pydantic 数据模型定义
- **extractors/**: 数据提取抽象层
- **graph/**: Neo4j 图谱存储和构建
- **agents/**: LangChain Agent 实现
- **services/**: 查询服务封装
- **web/**: Flask Web 应用

## 参考项目

本项目参考了以下设计：

- `chatbi/langchain_chatbi`: LangChain Agent 基类设计模式
- `graph_rag_tab`: GraphRAG 配置参考

## 许可证

MIT License
