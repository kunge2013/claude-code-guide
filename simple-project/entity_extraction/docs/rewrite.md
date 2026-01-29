# 问题改写服务设计文档

## 1. 概述

问题改写服务（Question Rewrite Service）是一个基于 LangChain 的智能服务，用于将用户的自然语言问题改写成结构化、明确的问题，便于后续的实体识别和 SQL 生成。

## 2. 背景

### 2.1 问题描述

在自然语言到 SQL 的转换过程中，用户的问题通常包含：
- 隐含的时间表达（如"今年"、"上月"、"去年"）
- 简化的产品名称（如"cdn"而不是完整的产品ID）
- 省略的上下文信息（如"金额是多少"未指明是"出账金额"）

这些隐含信息会导致实体识别不准确，从而影响 SQL 生成的质量。

### 2.2 解决方案

通过问题改写服务，将隐含信息显式化，使问题更加明确和结构化。

**示例：**
```
原始问题: "今年cdn产品金额是多少"
改写问题: "产品ID为cdn，时间为2026年的出账金额是多少"
```

## 3. 核心功能

### 3.1 时间规范化

将相对时间表达转换为明确的绝对时间：

| 原始表达 | 改写后 |
|---------|--------|
| 今年 | 时间为2026年 |
| 上月 | 时间为2025年12月 |
| 去年 | 时间为2025年 |
| 本季度 | 时间为2026年Q1 |
| 最近7天 | 时间为2026-01-22至2026-01-29 |

### 3.2 产品ID规范化

将产品简称/别名转换为标准的产品ID：

| 原始表达 | 改写后 |
|---------|--------|
| cdn | 产品ID为cdn |
| 云主机 | 产品ID为ecs |
| 对象存储 | 产品ID为oss |

### 3.3 字段明确化

将模糊的字段描述转换为明确的字段名：

| 原始表达 | 改写后 |
|---------|--------|
| 金额 | 出账金额 |
| 数量 | 订单数量 |
| 收入 | 营业收入 |

### 3.4 结构化重组

将问题改写为结构化的查询模式：

**模式：** `{实体类型}为{值}，{条件}的{指标}是多少`

## 4. 系统架构

```
┌─────────────────┐
│   用户问题      │
│ "今年cdn金额"   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   QuestionRewriteService │
│                          │
│  1. 问题预处理           │
│  2. 实体识别             │
│  3. 时间解析             │
│  4. 问题改写生成         │
│  5. 结果验证             │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   改写后问题            │
│ "产品ID为cdn，          │
│  时间为2026年的          │
│  出账金额是多少"         │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   后续流程              │
│  - 实体抽取             │
│  - SQL生成              │
└─────────────────────────┘
```

## 5. 数据模型

### 5.1 原始问题模型

```python
class OriginalQuestion(BaseModel):
    """原始用户问题"""
    content: str              # 问题内容
    domain: Optional[str]     # 业务域（可选）
    context: Optional[str]    # 上下文信息（可选）
```

### 5.2 改写问题模型

```python
class RewrittenQuestion(BaseModel):
    """改写后的问题"""
    original: str                    # 原始问题
    rewritten: str                   # 改写后的问题
    entities: Dict[str, Any]         # 识别出的实体
    confidence: float                # 改写置信度
    reasoning: Optional[str]         # 改写推理过程
```

### 5.3 改写结果模型

```python
class RewriteResult(BaseModel):
    """改写结果"""
    success: bool                    # 是否成功
    original: OriginalQuestion       # 原始问题
    rewritten: Optional[RewrittenQuestion]  # 改写后的问题
    errors: List[str]                # 错误列表
    metadata: Dict[str, Any]         # 元数据
```

## 6. 实现设计

### 6.1 目录结构

```
src/langchain_entity_extraction/
├── rewrite/
│   ├── __init__.py
│   ├── question_rewriter.py        # 问题改写服务
│   ├── time_normalizer.py          # 时间规范化工具
│   ├── entity_mapper.py            # 实体映射工具
│   └── prompts.py                  # 提示词模板
├── models/
│   └── rewrite_models.py           # 改写相关数据模型
```

### 6.2 核心类设计

#### QuestionRewriter

```python
class QuestionRewriter:
    """问题改写服务"""

    async def rewrite(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RewriteResult:
        """改写问题"""

    async def rewrite_batch(
        self,
        questions: List[str]
    ) -> List[RewriteResult]:
        """批量改写问题"""
```

#### TimeNormalizer

```python
class TimeNormalizer:
    """时间规范化工具"""

    def normalize(self, time_expr: str) -> str:
        """将相对时间转换为绝对时间"""

    def get_current_date(self) -> datetime:
        """获取当前日期"""
```

#### EntityMapper

```python
class EntityMapper:
    """实体映射工具"""

    def map_product_name(self, name: str) -> str:
        """将产品别名映射为标准ID"""

    def map_field_name(self, name: str) -> str:
        """将字段别名映射为标准字段名"""
```

## 7. 提示词设计

### 7.1 系统提示词

```python
SYSTEM_PROMPT = """你是一个专业的问题改写助手。你的任务是将用户的自然语言问题改写成结构化、明确的问题，以便后续的实体识别和SQL生成。

改写规则：
1. 识别并规范化时间表达（今年→2026年，上月→2025年12月）
2. 识别并规范化产品名称（cdn→产品ID为cdn）
3. 识别并明确化字段名称（金额→出账金额）
4. 保持问题的语义一致性
5. 使问题结构更加清晰

输出格式：
- 改写后的问题
- 识别的关键实体
- 改写的推理过程
"""
```

### 7.2 用户提示词模板

```python
USER_PROMPT_TEMPLATE = """请改写以下问题：

原始问题：{question}

上下文信息：
- 当前日期：{current_date}
- 产品列表：{product_list}
- 字段列表：{field_list}

请按照以下格式输出：
改写后问题：[改写后的问题]
识别实体：[识别出的实体列表]
推理过程：[改写的推理过程]
"""
```

## 8. 配置设计

### 8.1 产品映射配置

```yaml
product_mappings:
  cdn:
    standard_id: "cdn"
    aliases: ["cdn", "CDN", "内容分发网络"]
  ecs:
    standard_id: "ecs"
    aliases: ["ecs", "ECS", "云主机", "弹性计算"]
  oss:
    standard_id: "oss"
    aliases: ["oss", "OSS", "对象存储"]
```

### 8.2 字段映射配置

```yaml
field_mappings:
  amount:
    standard_name: "出账金额"
    aliases: ["金额", "费用", "钱", "总计"]
  quantity:
    standard_name: "订单数量"
    aliases: ["数量", "个数", "单数"]
  revenue:
    standard_name: "营业收入"
    aliases: ["收入", "营收", "收益"]
```

## 9. API 设计

### 9.1 基本改写接口

```python
# 单个问题改写
result = await rewriter.rewrite("今年cdn产品金额是多少")

# 批量问题改写
results = await rewriter.rewrite_batch([
    "今年cdn产品金额是多少",
    "上月ecs产品数量是多少"
])
```

### 9.2 带上下文改写

```python
result = await rewriter.rewrite(
    "金额是多少",
    context={
        "previous_question": "今年cdn产品",
        "product": "cdn",
        "time": "2026年"
    }
)
```

## 10. 单元测试设计

### 10.1 测试用例分类

#### 时间规范化测试
- 测试"今年"转换为当前年份
- 测试"上月"转换为上月月份
- 测试"去年"转换为去年年份
- 测试"本季度"转换为当前季度

#### 产品映射测试
- 测试产品简称到ID的映射
- 测试产品别名到ID的映射
- 测试未知产品的处理

#### 字段映射测试
- 测试字段别名到标准字段的映射
- 测试多个字段的同时识别

#### 完整改写测试
- 测试简单问题的改写
- 测试复杂问题的改写
- 测试多条件问题的改写

### 10.2 测试文件结构

```
tests/
├── test_question_rewriter.py      # 问题改写服务测试
├── test_time_normalizer.py        # 时间规范化测试
└── test_entity_mapper.py          # 实体映射测试
```

## 11. 使用示例

### 11.1 基本使用

```python
from langchain_entity_extraction.rewrite import QuestionRewriter

async def main():
    rewriter = QuestionRewriter()

    # 改写问题
    result = await rewriter.rewrite("今年cdn产品金额是多少")

    if result.success:
        print(f"原始问题: {result.original.content}")
        print(f"改写问题: {result.rewritten.rewritten}")
        print(f"识别实体: {result.rewritten.entities}")
    else:
        print(f"改写失败: {result.errors}")
```

### 11.2 预期输出

```
原始问题: 今年cdn产品金额是多少
改写问题: 产品ID为cdn，时间为2026年的出账金额是多少
识别实体: {
    "product_id": "cdn",
    "time": "2026年",
    "field": "出账金额"
}
```

## 12. 性能考虑

- **并发处理**：支持批量问题改写
- **缓存机制**：对相同问题进行缓存
- **超时控制**：单个问题改写超时时间为30秒
- **重试机制**：改写失败时最多重试3次

## 13. 后续集成计划

当前为独立服务，后续集成计划：

1. **第一阶段**：独立运行，验证改写效果
2. **第二阶段**：与实体抽取服务集成
3. **第三阶段**：与SQL生成服务集成
4. **第四阶段**：集成到完整的问答流程

## 14. 依赖项

- langchain-core >= 0.1.0
- langchain-openai >= 0.0.5
- pydantic >= 2.5.0
- python-dateutil >= 2.8.0

## 15. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1.0 | 2026-01-29 | 初始版本，支持基本问题改写功能 |
