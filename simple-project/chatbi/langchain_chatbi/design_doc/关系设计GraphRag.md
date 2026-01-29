# Graph RAG 设计文档

## 1. 需求概述

### 1.1 业务场景

在 Text-to-SQL 系统中，用户的问题往往隐含着复杂的业务语义。例如：

> "云总机产品上个月在华东地区的销售额"

这个问题包含：
- **实体**: 云总机（产品）
- **指标**: 销售额
- **维度**: 上个月（时间）、华东地区（地域）

系统需要：
1. 从问题中准确识别出实体、指标、维度
2. 基于这些信息智能选择相关的表和字段
3. 构建正确的查询条件（WHERE 子句）

### 1.2 核心需求

| 需求 | 说明 |
|------|------|
| 语义拆解 | 将用户问题拆解为实体、指标、维度 |
| 图谱构建 | 构建表与字段之间的语义关系图谱 |
| 智能路由 | 基于图谱信息智能选择表和字段 |
| 条件生成 | 自动生成 WHERE 条件中的值映射 |

### 1.3 问题示例

```sql
-- 产品表
products: prod_id, prod_name, category, ...

-- 销售表
sales: id, prod_id, region_id, date, amount, ...

-- 地区表
regions: region_id, region_name, city_name, ...

-- 用户问题
Q: "云总机在华东地区上个月的销售额"
```

**系统处理流程：**
```
1. 识别: 实体=云总机, 指标=销售额, 维度=华东地区, 上个月
2. 映射: 实体→prod_id=1001, 维度→region_id=IN('001','002',...)
3. 选表: products + sales + regions
4. 生成: SELECT sum(amount) FROM sales WHERE prod_id='1001' AND region_id IN (...)
```

---

## 2. 核心概念定义

### 2.1 实体 (Entity)

**定义**: 业务领域中的核心对象，具有唯一标识。

**特征**:
- 有唯一标识符（主键）
- 可以被独立查询
- 是业务分析的主体

**示例**:
| 实体类型 | 示例值 | 数据库表示 |
|----------|--------|------------|
| 产品 | 云总机、工作号 | `prod_id` |
| 客户 | 企业客户A、个人客户B | `customer_id` |
| 地区 | 华东、华北 | `region_id` |

### 2.2 指标 (Metric)

**定义**: 需要度量的业务数据，通常需要聚合计算。

**特征**:
- 数值型数据
- 需要聚合函数（SUM, AVG, COUNT 等）
- 是分析的目标

**示例**:
| 指标类型 | 示例值 | SQL 表示 |
|----------|--------|----------|
| 销售额 | `SUM(amount)` | `sum(sales.amount)` |
| 订单量 | `COUNT(*)` | `count(*)` |
| 客单价 | `AVG(amount)` | `avg(sales.amount)` |
| 利润率 | `SUM(profit)/SUM(revenue)` | 复杂计算 |

### 2.3 维度 (Dimension)

**定义**: 用于分组或筛选数据的属性。

**特征**:
- 分组维度：用于 GROUP BY
- 筛选维度：用于 WHERE 条件
- 时间维度特殊处理

**示例**:
| 维度类型 | 示例值 | SQL 表示 |
|----------|--------|----------|
| 时间 | 上个月、2024年、Q1 | `WHERE date >= ...` |
| 地区 | 华东、北京 | `WHERE region_id = ...` |
| 类别 | 企业版、个人版 | `WHERE category = ...` |

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Graph RAG 系统                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │ 语义解析层      │    │ 图谱层          │    │ 查询构建层      │ │
│  │                 │    │                 │    │                 │ │
│  │ - 实体识别      │───→│ - 关系图谱      │───→│ - 表选择        │ │
│  │ - 指标识别      │    │ - 语义相似度    │    │ - 字段映射      │ │
│  │ - 维度识别      │    │ - 路径推理      │    │ - 条件生成      │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│           │                       │                       │         │
│           ▼                       ▼                       ▼         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │ 知识库          │    │ 图数据库        │    │ SQL生成器       │ │
│  │                 │    │                 │    │                 │ │
│  │ - 业务术语表    │    │ - Neo4j         │    │ - LangChain     │ │
│  │ - 同义词词典    │    │ - NetworkX      │    │   SQL Agent     │ │
│  │ - 实体映射表    │    │ - 内存图谱      │    │                 │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 LangGraph 工作流集成

**变更前工作流：**
```
用户问题 → preprocessing → intent → schema → reasoning → sql → ...
```

**变更后工作流：**
```
用户问题
    │
    ▼
[preprocessing_node] ← 字典值转换
    │
    ▼
[intent_node] ← 意图分类
    │
    ├─→ (非query) ──→ END
    │
    ▼ (query)
[semantic_analysis_node] ← 🆕 语义分析（实体/指标/维度）
    │
    ▼
[graph_retrieval_node] ← 🆕 图谱检索增强
    │
    ▼
[schema_node] ← 表结构选择（图谱增强）
    │
    ▼
[reasoning_node] ← 查询推理（图谱上下文）
    │
    ▼
[sql_node] ← SQL生成（增强的表结构信息）
    │
    ▼
    ...
```

### 3.3 新增状态字段

```python
class ChatBIState(MessagesState):
    # === 现有字段 ===
    question: str
    original_question: Optional[str]
    transformed_question: Optional[str]
    # ... 其他现有字段

    # === Graph RAG 新增字段 ===

    # 语义分析结果
    entities: List[EntityInfo] = Field(default_factory=list)
    metrics: List[MetricInfo] = Field(default_factory=list)
    dimensions: List[DimensionInfo] = Field(default_factory=list)

    # 图谱检索上下文
    graph_context: Optional[GraphContext] = None

    # 增强的表选择信息
    entity_table_mapping: Dict[str, str] = Field(default_factory=dict)
    metric_field_mapping: Dict[str, str] = Field(default_factory=dict)
    dimension_conditions: List[ConditionInfo] = Field(default_factory=list)
```

---

## 4. 数据模型设计

### 4.1 语义信息模型

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import date, datetime

class EntityInfo(BaseModel):
    """实体信息"""
    name: str = Field(description="实体名称，如'云总机'")
    entity_type: str = Field(description="实体类型，如'product'")
    canonical_value: str = Field(description="标准值，如'云总机'")
    database_id: Optional[str] = Field(description="数据库ID，如'1001'")
    table_name: Optional[str] = Field(description="所属表，如'products'")
    id_column: Optional[str] = Field(description="ID字段，如'prod_id'")
    confidence: float = Field(description="识别置信度 0-1", ge=0, le=1)
    synonyms: List[str] = Field(default_factory=list, description="同义词列表")

class MetricInfo(BaseModel):
    """指标信息"""
    name: str = Field(description="指标名称，如'销售额'")
    metric_type: Literal["sum", "avg", "count", "max", "min", "custom"] = Field(description="聚合类型")
    table_name: Optional[str] = Field(description="所属表")
    field_name: Optional[str] = Field(description="字段名")
    expression: Optional[str] = Field(description="自定义表达式")
    alias: Optional[str] = Field(description="SQL中的别名")
    confidence: float = Field(description="识别置信度 0-1", ge=0, le=1)

class DimensionInfo(BaseModel):
    """维度信息"""
    name: str = Field(description="维度名称，如'上个月'")
    dimension_type: Literal["time", "geographic", "category", "custom"] = Field(description="维度类型")
    table_name: Optional[str] = Field(description="所属表")
    field_name: Optional[str] = Field(description="字段名")
    condition_type: Literal["equals", "in", "range", "date_range"] = Field(description="条件类型")
    condition_value: Any = Field(description="条件值")
    date_range: Optional[Dict[str, str]] = Field(description="时间范围 {start, end}")
    confidence: float = Field(description="识别置信度 0-1", ge=0, le=1)

class ConditionInfo(BaseModel):
    """查询条件信息"""
    table_name: str
    field_name: str
    operator: Literal["=", "IN", ">", "<", ">=", "<=", "BETWEEN", "LIKE"]
    value: Any
    sql_fragment: str = Field(description="SQL条件片段")

class GraphContext(BaseModel):
    """图谱上下文"""
    selected_tables: List[str] = Field(default_factory=list, description="选中的表")
    table_relationships: List[Dict[str, Any]] = Field(default_factory=list, description="表关系")
    join_paths: List[List[str]] = Field(default_factory=list, description="JOIN路径")
    recommended_fields: Dict[str, List[str]] = Field(default_factory=dict, description="推荐字段 {table: [fields]}")
```

### 4.2 图谱模型

```python
class KnowledgeGraph:
    """知识图谱"""

    def __init__(self):
        # 使用 NetworkX 或简单的内存图结构
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

    def add_entity_node(self, entity: EntityInfo):
        """添加实体节点"""

    def add_metric_node(self, metric: MetricInfo):
        """添加指标节点"""

    def add_dimension_node(self, dimension: DimensionInfo):
        """添加维度节点"""

    def add_table_node(self, table_name: str, columns: List[Dict]):
        """添加表节点"""

    def find_shortest_path(self, start: str, end: str) -> List[str]:
        """查找最短路径"""

    def get_related_tables(self, entity: str) -> List[str]:
        """获取实体相关的表"""

    def get_metrics_for_entity(self, entity: str) -> List[MetricInfo]:
        """获取实体的可用指标"""

class GraphNode:
    """图谱节点"""
    id: str
    type: Literal["entity", "metric", "dimension", "table", "column"]
    properties: Dict[str, Any]

class GraphEdge:
    """图谱边"""
    source: str
    target: str
    relation_type: Literal["belongs_to", "has_metric", "has_dimension", "joins_with"]
    properties: Dict[str, Any]
```

### 4.3 图谱配置

```yaml
# config/graph_schema_config.yaml

graph_config:
  # 实体定义
  entities:
    - name: product
      table: products
      id_column: prod_id
      name_column: prod_name
      dictionary: product_dict  # 引用字典配置

    - name: region
      table: regions
      id_column: region_id
      name_column: region_name
      dictionary: region_dict

  # 指标定义
  metrics:
    - name: 销售额
      metric_type: sum
      table: sales
      field: amount
      related_entities: [product, region]

    - name: 订单量
      metric_type: count
      table: sales
      field: id
      related_entities: [product, region]

  # 维度定义
  dimensions:
    - name: time
      dimension_type: time
      table: sales
      field: date
      keywords: [上个月, 去年, 本季度, 最近一周]

    - name: region
      dimension_type: geographic
      table: regions
      field: region_name
      keywords: [华东, 华北, 华南]

  # 表关系
  table_relationships:
    - from_table: sales
      to_table: products
      join_type: inner
      on: sales.prod_id = products.prod_id

    - from_table: sales
      to_table: regions
      join_type: inner
      on: sales.region_id = regions.region_id
```

---

## 5. 核心组件设计

### 5.1 SemanticAnalysisAgent

```python
class SemanticAnalysisAgent(LangChainAgentBase):
    """
    语义分析 Agent - 从用户问题中提取实体、指标、维度
    """

    system_prompt = """
你是一个语义分析专家。你的任务是从用户问题中提取：
1. 实体（Entity）：业务对象，如产品、客户
2. 指标（Metric）：需要度量的数据，如销售额、订单量
3. 维度（Dimension）：分组或筛选条件，如时间、地区

分析时注意：
- 同一词可能是不同类型，根据上下文判断
- 时间表达需要规范化
- 地理表达需要层级处理
- 输出置信度帮助后续决策
"""

    async def analyze(
        self,
        question: str,
        available_entities: List[Dict],
        available_metrics: List[Dict],
        available_dimensions: List[Dict]
    ) -> SemanticAnalysisResult:
        """
        分析用户问题

        Args:
            question: 用户问题
            available_entities: 可用的实体定义
            available_metrics: 可用的指标定义
            available_dimensions: 可用的维度定义

        Returns:
            SemanticAnalysisResult: 包含识别的实体、指标、维度
        """
```

### 5.2 GraphRetrievalService

```python
class GraphRetrievalService:
    """
    图谱检索服务 - 基于语义信息检索相关表和字段
    """

    def __init__(self, config_path: str = "config/graph_schema_config.yaml"):
        self.graph = KnowledgeGraph()
        self.config = self._load_config(config_path)
        self._build_graph()

    async def retrieve_context(
        self,
        entities: List[EntityInfo],
        metrics: List[MetricInfo],
        dimensions: List[DimensionInfo]
    ) -> GraphContext:
        """
        基于识别的语义信息检索图谱上下文

        处理流程：
        1. 找到所有实体对应的表
        2. 找到所有指标对应的表和字段
        3. 基于表关系生成 JOIN 路径
        4. 为维度生成查询条件
        """

    def _find_join_path(
        self,
        tables: Set[str]
    ) -> List[Dict[str, str]]:
        """
        找到连接多个表的 JOIN 路径

        例如：sales → products → categories
        """

    def _generate_dimension_conditions(
        self,
        dimensions: List[DimensionInfo]
    ) -> List[ConditionInfo]:
        """
        将维度信息转换为 SQL 条件
        """
```

### 5.3 增强的 SchemaAgent

```python
class EnhancedSchemaAgent(SchemaAgent):
    """
    增强的表选择 Agent - 融合图谱信息
    """

    async def select_schemas(
        self,
        question: str,
        available_schemas: List[Dict],
        graph_context: Optional[GraphContext] = None
    ) -> List[Dict]:
        """
        选择相关表结构

        如果有图谱上下文：
        1. 优先使用图谱推荐的表
        2. 补充必要的关联表
        3. 调整表的优先级
        """
```

---

## 6. 处理流程详解

### 6.1 完整处理流程

```
用户问题: "云总机在华东地区上个月的销售额"

Step 1: preprocessing_node
  输入: "云总机在华东地区上个月的销售额"
  输出: transformed = "1001在华东地区上个月的销售额"

Step 2: intent_node
  输入: transformed
  输出: intent = "query"

Step 3: semantic_analysis_node [NEW]
  输入: transformed, graph_config
  处理:
    - 识别实体: "云总机" → EntityInfo(type="product", db_id="1001")
    - 识别指标: "销售额" → MetricInfo(type="sum", field="amount")
    - 识别维度: "华东地区" → DimensionInfo(type="geographic"), "上个月" → DimensionInfo(type="time")
  输出: entities=[...], metrics=[...], dimensions=[...]

Step 4: graph_retrieval_node [NEW]
  输入: entities, metrics, dimensions
  处理:
    - 实体 "云总机" → products 表
    - 指标 "销售额" → sales.amount 字段
    - 维度 "华东地区" → regions 表，WHERE region_id IN (...)
    - 维度 "上个月" → WHERE date BETWEEN ... AND ...
    - JOIN 路径: sales → products (on prod_id), sales → regions (on region_id)
  输出: graph_context = {
      selected_tables: ["sales", "products", "regions"],
      join_paths: [...],
      recommended_fields: {...},
      dimension_conditions: [...]
    }

Step 5: schema_node
  输入: question, available_schemas, graph_context
  处理: 基于图谱上下文选择表
  输出: selected_schemas = [sales_schema, products_schema, regions_schema]

Step 6: reasoning_node
  输入: question, selected_schemas, graph_context
  处理: 融入图谱信息的推理
  输出: reasoning = "需要连接 sales 和 products 表，按地区分组..."

Step 7: sql_node
  输入: reasoning, selected_schemas, graph_context
  输出: generated_sql = """
      SELECT sum(s.amount) as sales_amount
      FROM sales s
      INNER JOIN products p ON s.prod_id = p.prod_id
      INNER JOIN regions r ON s.region_id = r.region_id
      WHERE p.prod_id = '1001'
        AND r.region_id IN ('001', '002', '003')
        AND s.date BETWEEN '2024-12-01' AND '2024-12-31'
    """

Step 8+: 继续现有流程...
```

### 6.2 时间维度处理

```python
class TimeDimensionProcessor:
    """
    时间维度处理器 - 将自然语言转换为 SQL 日期条件
    """

    TIME_PATTERNS = {
        r"今天": lambda: date.today(),
        r"昨天": lambda: date.today() - timedelta(days=1),
        r"本周": lambda: get_week_range(),
        r"上周": lambda: get_last_week_range(),
        r"本月": lambda: get_month_range(),
        r"上个月": lambda: get_last_month_range(),
        r"本季度": lambda: get_quarter_range(),
        r"去年": lambda: get_year_range(-1),
        r"最近(\d+)天": lambda m: get_recent_days(int(m.group(1))),
    }

    def parse(self, text: str) -> Optional[DateRange]:
        """
        解析时间表达式
        返回: DateRange(start_date, end_date, field_suggestions)
        """
```

### 6.3 地理维度处理

```python
class GeographicDimensionProcessor:
    """
    地理维度处理器 - 处理层级化的地理信息
    """

    def __init__(self, db_connection):
        self.hierarchy = self._load_geographic_hierarchy(db_connection)
        # 示例: {"country": [{"中国", ["华东", "华北", ...]}]}

    def parse(self, text: str) -> List[str]:
        """
        解理地理表达式，返回所有相关的 region_id

        输入: "华东"
        输出: ["001", "002", "003"]  # 华东包含的所有地区ID
        """
```

---

## 7. 实现方案

### 7.1 目录结构

```
langchain_chatbi/
├── graph_rag/                     # 新增：Graph RAG 模块
│   ├── __init__.py
│   ├── semantic_agent.py          # 语义分析 Agent
│   ├── graph_service.py           # 图谱服务
│   ├── dimension_processors/      # 维度处理器
│   │   ├── __init__.py
│   │   ├── time_processor.py      # 时间维度
│   │   ├── geographic_processor.py # 地理维度
│   │   └── category_processor.py  # 类别维度
│   └── models.py                  # 数据模型
├── config/
│   ├── graph_schema_config.yaml   # 图谱配置
│   └── entity_mappings.yaml       # 实体映射配置
├── agents/
│   └── enhanced_schema_agent.py   # 增强的表选择 Agent
├── graph/
│   ├── state.py                   # 修改：添加 Graph RAG 字段
│   ├── nodes.py                   # 修改：添加新节点
│   ├── edges.py                   # 修改：添加新路由
│   └── workflow.py                # 修改：更新工作流
└── tests/
    ├── test_semantic_agent.py     # 语义分析测试
    ├── test_graph_service.py      # 图谱服务测试
    ├── test_dimension_processors.py # 维度处理器测试
    └── test_graph_rag_integration.py # 集成测试
```

### 7.2 文件清单

| 文件 | 预估行数 | 描述 |
|------|----------|------|
| `graph_rag/__init__.py` | 30 | 模块导出 |
| `graph_rag/models.py` | 150 | Pydantic 数据模型 |
| `graph_rag/semantic_agent.py` | 200 | 语义分析 Agent |
| `graph_rag/graph_service.py` | 300 | 图谱服务核心实现 |
| `graph_rag/dimension_processors/time_processor.py` | 180 | 时间维度处理 |
| `graph_rag/dimension_processors/geographic_processor.py` | 150 | 地理维度处理 |
| `graph_rag/dimension_processors/category_processor.py` | 100 | 类别维度处理 |
| `config/graph_schema_config.yaml` | 80 | 图谱配置 |
| `config/entity_mappings.yaml` | 60 | 实体映射 |
| `graph/state.py` | +30 | 添加新状态字段 |
| `graph/nodes.py` | +150 | 添加两个新节点 |
| `graph/edges.py` | +20 | 添加新路由 |
| `graph/workflow.py` | +30 | 更新工作流 |
| `agents/enhanced_schema_agent.py` | 100 | 增强的 Schema Agent |
| `tests/test_semantic_agent.py` | 150 | 单元测试 |
| `tests/test_graph_service.py` | 200 | 单元测试 |
| `tests/test_dimension_processors.py` | 180 | 单元测试 |
| `tests/test_graph_rag_integration.py` | 250 | 集成测试 |

**总计**: ~2200 行新增/修改代码

### 7.3 开发阶段

#### Phase 1: 数据模型和配置 (1-2天)
- [ ] 定义 Pydantic 模型（EntityInfo, MetricInfo, DimensionInfo 等）
- [ ] 设计 graph_schema_config.yaml 结构
- [ ] 创建 entity_mappings.yaml
- [ ] 编写配置加载器

#### Phase 2: 语义分析 Agent (2-3天)
- [ ] 实现 SemanticAnalysisAgent
- [ ] 设计提示词工程
- [ ] 处理边界情况
- [ ] 单元测试

#### Phase 3: 图谱服务 (3-4天)
- [ ] 实现 KnowledgeGraph 类
- [ ] 实现 GraphRetrievalService
- [ ] JOIN 路径查找算法
- [ ] 单元测试

#### Phase 4: 维度处理器 (2-3天)
- [ ] TimeDimensionProcessor
- [ ] GeographicDimensionProcessor
- [ ] CategoryDimensionProcessor
- [ ] 单元测试

#### Phase 5: LangGraph 集成 (2-3天)
- [ ] 添加 semantic_analysis_node
- [ ] 添加 graph_retrieval_node
- [ ] 更新路由逻辑
- [ ] 集成测试

#### Phase 6: 增强的 Schema Agent (1-2天)
- [ ] 修改 SchemaAgent 使用图谱上下文
- [ ] 测试和调优

#### Phase 7: 端到端测试和优化 (2-3天)
- [ ] 完整工作流测试
- [ ] 性能优化
- [ ] 错误处理完善

**总计**: 约 13-20 个工作日

---

## 8. 关键技术点

### 8.1 图谱存储方案对比

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| **内存图 (NetworkX)** | 简单、快速、无依赖 | 不支持大规模、无持久化 | 小型项目（<1000节点） |
| **Neo4j** | 功能强大、图查询语言、可扩展 | 需要额外部署、学习成本 | 大型项目、复杂查询 |
| **关系数据库** | 无额外依赖、易维护 | 图查询性能较差 | 中型项目 |
| **图数据库 (NetworkX + SQLite)** | 平衡性能和复杂度 | 需要自定义实现 | 推荐：本项目的首选 |

**本项目推荐方案**：
```
启动时从配置和数据库元数据构建内存图
使用 NetworkX 进行路径查找
将图结构缓存到 SQLite 以加速启动
```

### 8.2 JOIN 路径查找

```python
def find_join_path(start_table: str, end_table: str, graph: KnowledgeGraph) -> List[str]:
    """
    使用 BFS 查找最短 JOIN 路径

    示例：
    输入: start="products", end="regions"
    输出: ["products", "sales", "regions"]

    生成 SQL: FROM products
            INNER JOIN sales ON products.prod_id = sales.prod_id
            INNER JOIN regions ON sales.region_id = regions.region_id
    """
```

### 8.3 置信度阈值策略

```python
CONFIDENCE_THRESHOLDS = {
    "high": 0.8,    # 直接使用
    "medium": 0.5,  # 需要确认或尝试多个
    "low": 0.3      # 忽略或让用户澄清
}

def handle_low_confidence_items(analysis_result: SemanticAnalysisResult):
    """
    处理低置信度识别结果
    - 如果实体置信度低，生成澄清问题
    - 如果指标置信度低，尝试所有可能的指标
    - 如果维度置信度低，使用宽泛条件
    """
```

---

## 9. 示例场景

### 9.1 简单查询

```
用户问题: "云总机的销售额"

语义分析:
  entities: [云总机 (product)]
  metrics: [销售额 (sum)]
  dimensions: []

图谱检索:
  表: products, sales
  JOIN: sales.prod_id = products.prod_id
  WHERE: products.prod_id = '1001'

SQL: SELECT sum(s.amount) FROM sales s
     INNER JOIN products p ON s.prod_id = p.prod_id
     WHERE p.prod_id = '1001'
```

### 9.2 复杂查询

```
用户问题: "云总机在华东地区最近30天的日销售额趋势"

语义分析:
  entities: [云总机 (product)]
  metrics: [销售额 (sum)]
  dimensions: [华东地区 (geographic), 最近30天 (time)]

图谱检索:
  表: products, sales, regions
  JOIN: sales → products, sales → regions
  WHERE:
    - products.prod_id = '1001'
    - regions.region_id IN ('001', '002', '003')
    - sales.date BETWEEN (NOW()-30d) AND NOW()
  GROUP BY: DATE(sales.date)
  ORDER BY: DATE(sales.date)

SQL: SELECT DATE(s.date) as sale_date,
            sum(s.amount) as daily_sales
     FROM sales s
     INNER JOIN products p ON s.prod_id = p.prod_id
     INNER JOIN regions r ON s.region_id = r.region_id
     WHERE p.prod_id = '1001'
       AND r.region_id IN ('001', '002', '003')
       AND s.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
     GROUP BY DATE(s.date)
     ORDER BY sale_date
```

### 9.3 多维度查询

```
用户问题: "各个产品类别的销售额和订单量对比"

语义分析:
  entities: [] (无特定实体)
  metrics: [销售额 (sum), 订单量 (count)]
  dimensions: [产品类别 (category)]

图谱检索:
  表: products, sales
  JOIN: sales → products
  GROUP BY: products.category

SQL: SELECT p.category as product_category,
            sum(s.amount) as sales_amount,
            count(s.id) as order_count
     FROM sales s
     INNER JOIN products p ON s.prod_id = p.prod_id
     GROUP BY p.category
     ORDER BY sales_amount DESC
```

---

## 10. 性能考虑

### 10.1 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 语义分析延迟 | < 500ms | LLM 调用时间 |
| 图谱检索延迟 | < 50ms | 内存图查询 |
| 端到端延迟 | < 3s | 从问题到 SQL |
| 图谱构建时间 | < 1s | 启动时一次性 |
| 内存占用 | < 100MB | 假设500个节点 |

### 10.2 优化策略

1. **图谱缓存**:
   - 启动时构建并序列化到文件
   - 后续启动直接加载

2. **LLM 并行化**:
   - 语义分析可以使用较小的模型
   - 考虑使用本地模型（如 Llama）

3. **增量更新**:
   - 图谱结构变化时增量更新
   - 而非完全重建

4. **结果缓存**:
   - 相同问题的语义分析结果缓存
   - 使用 LRU 缓存策略

---

## 11. 错误处理

### 11.1 错误场景

| 场景 | 处理策略 |
|------|----------|
| 语义分析失败 | 降级到现有流程（无图谱增强） |
| 找不到 JOIN 路径 | 尝试所有可能的表组合 |
| 低置信度结果 | 生成澄清问题或使用多个候选 |
| 时间解析失败 | 使用默认时间范围 |
| 地理层级缺失 | 降级到精确匹配 |

### 11.2 降级策略

```python
class GraphRAGFallback:
    """
    Graph RAG 降级策略
    """

    @staticmethod
    def safe_semantic_analysis(question: str, agent: SemanticAnalysisAgent):
        """安全执行语义分析，失败时返回空结果"""
        try:
            return await agent.analyze(question)
        except Exception as e:
            logger.warning(f"语义分析失败: {e}, 使用空结果")
            return SemanticAnalysisResult(entities=[], metrics=[], dimensions=[])

    @staticmethod
    def safe_graph_retrieval(semantic_result, graph_service):
        """安全执行图谱检索，失败时返回空上下文"""
        try:
            return await graph_service.retrieve_context(
                semantic_result.entities,
                semantic_result.metrics,
                semantic_result.dimensions
            )
        except Exception as e:
            logger.warning(f"图谱检索失败: {e}, 使用空上下文")
            return GraphContext(selected_tables=[], join_paths=[])
```

---

## 12. 测试策略

### 12.1 单元测试

```python
# test_semantic_agent.py
class TestSemanticAnalysisAgent:
    def test_extract_single_entity(self):
        """测试提取单个实体"""
        result = await agent.analyze("云总机的销售额")
        assert len(result.entities) == 1
        assert result.entities[0].name == "云总机"

    def test_extract_multiple_dimensions(self):
        """测试提取多个维度"""
        result = await agent.analyze("云总机在华东地区上个月的销售额")
        assert len(result.dimensions) == 2

# test_graph_service.py
class TestGraphService:
    def test_find_join_path(self):
        """测试 JOIN 路径查找"""
        path = graph_service.find_join_path("products", "regions")
        assert path == ["products", "sales", "regions"]

    def test_generate_dimension_conditions(self):
        """测试维度条件生成"""
        conditions = graph_service.generate_dimension_conditions([region_dim])
        assert conditions[0].operator == "IN"

# test_dimension_processors.py
class TestTimeDimensionProcessor:
    def test_parse_last_month(self):
        """测试解析'上个月'"""
        range = processor.parse("上个月")
        assert range.start_date.day == 1
        assert range.end_date.day == month_last_day()

    def test_parse_recent_days(self):
        """测试解析'最近30天'"""
        range = processor.parse("最近30天")
        assert (range.end_date - range.start_date).days == 29
```

### 12.2 集成测试

```python
# test_graph_rag_integration.py
class TestGraphRAGIntegration:
    async def test_end_to_end_query(self):
        """测试完整查询流程"""
        question = "云总机在华东地区上个月的销售额"

        config = {
            "configurable": {
                "graph_rag_enabled": True,
                "graph_service": graph_service,
                "db": test_db
            }
        }

        result = await graph.ainvoke({"question": question}, config)

        assert result["entities"][0].name == "云总机"
        assert result["metrics"][0].name == "销售额"
        assert len(result["graph_context"].selected_tables) == 3
        assert "JOIN" in result["generated_sql"]
        assert "prod_id = '1001'" in result["generated_sql"]

    async def test_fallback_when_analysis_fails(self):
        """测试语义分析失败时的降级"""
        # Mock 一个失败的语义分析
        with mock.patch.object(semantic_agent, 'analyze', side_effect=Exception()):
            result = await graph.ainvoke({"question": "云总机的销售额"}, config)

            # 应该降级到原有流程，仍然生成 SQL
            assert result["generated_sql"] is not None
```

---

## 13. 监控和日志

### 13.1 关键指标

```python
# 需要监控的指标
GRAPH_RAG_METRICS = {
    # 语义分析
    "semantic_analysis_latency": "语义分析耗时",
    "semantic_analysis_success_rate": "语义分析成功率",
    "entity_extraction_accuracy": "实体提取准确率",
    "metric_extraction_accuracy": "指标提取准确率",

    # 图谱检索
    "graph_retrieval_latency": "图谱检索耗时",
    "join_path_found_rate": "找到 JOIN 路径的比例",
    "avg_join_path_length": "平均 JOIN 路径长度",

    # 端到端
    "graph_rag_enabled_queries": "启用 Graph RAG 的查询数",
    "graph_rag_fallback_rate": "降级到原有流程的比例",
    "sql_quality_improvement": "SQL 质量（执行成功率）提升"
}
```

### 13.2 日志格式

```python
logger.info(
    "graph_rag_analysis",
    extra={
        "question": question,
        "entities": [e.name for e in result.entities],
        "metrics": [m.name for m in result.metrics],
        "dimensions": [d.name for d in result.dimensions],
        "selected_tables": result.graph_context.selected_tables,
        "join_paths": result.graph_context.join_paths,
        "latency_ms": latency
    }
)
```

---

## 14. 未来扩展

### 14.1 短期增强 (3个月内)

- [ ] 支持更复杂的时间表达式（"工作日"、"周末"）
- [ ] 支持同比、环比计算
- [ ] 支持自定义指标公式
- [ ] 图谱可视化界面

### 14.2 中期增强 (6个月内)

- [ ] 图谱自动发现（从数据库元数据）
- [ ] 语义分析模型微调
- [ ] 多轮对话上下文积累
- [ ] A/B 测试框架

### 14.3 长期愿景 (1年内)

- [ ] 图神经网络（GNN）增强
- [ ] 自动化标注工具
- [ ] 知识图谱与向量检索融合
- [ ] 多租户图谱隔离

---

## 15. 关键文件路径

```
langchain_chatbi/
├── graph_rag/                            # Graph RAG 模块
│   ├── __init__.py
│   ├── models.py                         # 数据模型
│   ├── semantic_agent.py                 # 语义分析 Agent
│   └── graph_service.py                  # 图谱服务
├── config/
│   ├── graph_schema_config.yaml          # 图谱配置
│   └── entity_mappings.yaml              # 实体映射
├── graph/
│   ├── state.py                          # 状态定义（扩展）
│   ├── nodes.py                          # 节点定义（扩展）
│   ├── edges.py                          # 路由定义（扩展）
│   └── workflow.py                       # 工作流编排（扩展）
└── design_doc/
    └── 关系设计GraphRag.md               # 本文档
```

---

## 16. 参考资料

### 16.1 相关技术

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **NetworkX**: https://networkx.org/
- **RAG 论文**: "Retrieval-Augmented Generation for Large Language Models"

### 16.2 类似项目

- **Microsoft GraphRAG**: 微软的开源图谱 RAG 实现
- **LlamaIndex Knowledge Graph**: 索引框架的图谱集成
- **Neo4j LLM KG**: Neo4j 的 LLM 知识图谱解决方案

### 16.3 最佳实践

- 图谱设计遵循"小而美"原则，避免过度复杂
- 优先考虑用户体验，而非系统完美性
- 保持降级策略简单可靠
- 监控和迭代优化

---

*文档版本: 1.0*
*创建日期: 2026-01-28*
*作者: Claude Code*
