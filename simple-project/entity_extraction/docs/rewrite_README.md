# 问题改写服务 - 使用说明

## 概述

问题改写服务（Question Rewrite Service）是一个基于 LangChain 的智能服务，用于将用户的自然语言问题改写成结构化、明确的问题，便于后续的实体识别和 SQL 生成。

## 核心功能

### 1. 时间规范化
将相对时间表达转换为明确的绝对时间：
- "今年" → "2026年"
- "上月" → "2025年12月"
- "本季度" → "2026年Q1"

### 2. 产品ID规范化
将产品简称/别名转换为标准的产品ID：
- "cdn" → "产品ID为cdn"
- "云主机" → "产品ID为ecs"

### 3. 字段明确化
将模糊的字段描述转换为明确的字段名：
- "金额" → "出账金额"
- "数量" → "订单数量"

## 使用示例

### 基本使用

```python
import asyncio
from langchain_entity_extraction.rewrite import QuestionRewriter

async def main():
    rewriter = QuestionRewriter()

    # 改写问题
    result = await rewriter.rewrite("今年cdn产品金额是多少")

    if result.success:
        print(f"原始问题: {result.original.content}")
        print(f"改写问题: {result.rewritten.rewritten}")
        print(f"识别实体: {result.rewritten.entities}")

asyncio.run(main())
```

**输出示例：**
```
原始问题: 今年cdn产品金额是多少
改写问题: 产品ID为cdn，时间为2026年的出账金额是多少
识别实体: {"product_id": "cdn", "time": "2026年", "field": "出账金额"}
```

### 批量改写

```python
questions = [
    "今年cdn产品金额是多少",
    "上月ecs产品数量是多少",
    "去年oss产品收入是多少"
]

batch_result = await rewriter.rewrite_batch(questions)

print(f"总数: {batch_result.total_count}")
print(f"成功: {batch_result.successful_count}")
print(f"失败: {batch_result.failed_count}")
```

### 同步 API

```python
# 使用同步包装方法
result = rewriter.rewrite_sync("今年cdn产品金额是多少")
```

### 单独使用工具类

```python
from langchain_entity_extraction.rewrite import TimeNormalizer, EntityMapper

# 时间规范化
normalizer = TimeNormalizer()
print(normalizer.normalize("今年"))  # "2026年"

# 实体映射
mapper = EntityMapper()
print(mapper.map_product_name("cdn"))  # "cdn"
print(mapper.map_field_name("金额"))   # "出账金额"
```

## 单元测试

运行单元测试：

```bash
# 运行独立测试（不需要 LLM API）
python tests/test_rewrite_standalone.py

# 或运行内联测试
python -c "
from datetime import date
from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper

normalizer = TimeNormalizer(date(2026, 1, 15))
assert normalizer.normalize('今年') == '2026年'
assert normalizer.normalize('上月') == '2025年12月'

mapper = EntityMapper()
assert mapper.map_product_name('cdn') == 'cdn'
assert mapper.map_field_name('金额') == '出账金额'

print('所有测试通过!')
"
```

## 测试结果

```
=== TimeNormalizer 测试 ===
  ✓ 今年           → 2026年
  ✓ 去年           → 2025年
  ✓ 本月           → 2026年1月
  ✓ 上月           → 2025年12月
  ✓ 本季度          → 2026年Q1

=== EntityMapper 测试 ===
  ✓ cdn          → cdn
  ✓ CDN          → cdn
  ✓ 内容分发网络       → cdn
  ✓ 金额     → 出账金额
  ✓ 费用     → 出账金额
```

## 配置

在 `.env` 文件中配置 LLM API：

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# 或智谱 AI
ZHIPUAI_API_KEY=your_zhipuai_api_key
ZHIPUAI_MODEL=glm-4
```

## 文件结构

```
src/langchain_entity_extraction/rewrite/
├── __init__.py              # 模块导出
├── question_rewriter.py     # 主服务类
├── time_normalizer.py       # 时间规范化工具
├── entity_mapper.py         # 实体映射工具
└── prompts.py               # 提示词模板

models/
└── rewrite_models.py        # 改写相关数据模型

tests/
└── test_question_rewriter.py  # 单元测试

scripts/
└── question_rewrite_example.py  # 使用示例

docs/
├── rewrite.md              # 详细设计文档
└── rewrite_README.md       # 本文档
```

## 后续集成计划

当前为独立服务，按以下阶段集成：

1. **第一阶段**：独立运行，验证改写效果
2. **第二阶段**：与实体抽取服务集成
3. **第三阶段**：与SQL生成服务集成
4. **第四阶段**：集成到完整的问答流程

## 注意事项

1. **API Key 配置**：使用 LLM 功能需要配置有效的 API Key
2. **时间参考**：时间规范化以当前日期为参考
3. **实体映射**：产品别名和字段别名可在配置中扩展
4. **暂时独立**：当前未接入主流程，仅作为独立服务运行
