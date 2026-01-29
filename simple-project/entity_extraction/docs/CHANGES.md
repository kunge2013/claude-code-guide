# 改动记录 - 问题改写服务

## 改动日期
2026-01-29

## 改动概述

新增问题改写服务（Question Rewrite Service），用于将用户的自然语言问题改写成结构化、明确的问题，便于后续的实体识别和 SQL 生成。

## 新增文件

### 设计文档
- `docs/rewrite.md` - 完整的设计文档，包含系统架构、数据模型、API设计等
- `docs/rewrite_README.md` - 使用说明文档
- `docs/CHANGES.md` - 本改动记录

### 核心代码模块
- `src/langchain_entity_extraction/rewrite/__init__.py` - 模块导出
- `src/langchain_entity_extraction/rewrite/question_rewriter.py` - 主服务类 (240行)
- `src/langchain_entity_extraction/rewrite/time_normalizer.py` - 时间规范化工具 (130行)
- `src/langchain_entity_extraction/rewrite/entity_mapper.py` - 实体映射工具 (170行)
- `src/langchain_entity_extraction/rewrite/prompts.py` - 提示词模板 (90行)

### 数据模型
- `src/langchain_entity_extraction/models/rewrite_models.py` - 改写相关数据模型 (150行)
  - OriginalQuestion - 原始问题模型
  - RewrittenQuestion - 改写后问题模型
  - RewriteResult - 改写结果模型
  - BatchRewriteResult - 批量改写结果模型

### 单元测试
- `tests/test_question_rewriter.py` - 完整单元测试 (350行)
  - TestTimeNormalizer - 时间规范化测试 (7个测试用例)
  - TestEntityMapper - 实体映射测试 (8个测试用例)
  - TestQuestionRewriter - 问题改写服务测试 (4个测试用例)
  - TestRewriteModels - 数据模型测试 (5个测试用例)
- `tests/test_rewrite_standalone.py` - 独立测试脚本
- `tests/test_rewrite_only.py` - 简化测试脚本

### 示例脚本
- `scripts/question_rewrite_example.py` - 使用示例脚本 (200行)
  - 7个示例场景展示各种使用方式

## 修改文件

### 更新的文件
- `src/langchain_entity_extraction/__init__.py` - 添加问题改写模块导出
  - 版本号更新: 0.1.0 → 0.2.0
  - 新增导出: QuestionRewriter, TimeNormalizer, EntityMapper

## 功能特性

### 1. 时间规范化
- 支持相对时间表达转换为绝对时间
- 支持: 今年、去年、本月、上月、本季度、上季度、最近N天
- 示例: "今年" → "2026年"

### 2. 产品ID规范化
- 支持产品别名映射到标准ID
- 默认支持: cdn, ecs, oss, rds, slb
- 示例: "云主机" → "产品ID为ecs"

### 3. 字段明确化
- 支持字段别名映射到标准字段名
- 默认支持: 出账金额、订单数量、营业收入、用户数、流量
- 示例: "金额" → "出账金额"

### 4. 问题改写服务
- 支持单个问题改写
- 支持批量问题改写
- 支持同步和异步API
- 支持上下文感知改写

## 使用示例

### 基本使用
```python
from langchain_entity_extraction.rewrite import QuestionRewriter

rewriter = QuestionRewriter()
result = await rewriter.rewrite("今年cdn产品金额是多少")

# 输出:
# 原始问题: 今年cdn产品金额是多少
# 改写问题: 产品ID为cdn，时间为2026年的出账金额是多少
```

### 单独使用工具类
```python
from langchain_entity_extraction.rewrite import TimeNormalizer, EntityMapper

# 时间规范化
normalizer = TimeNormalizer()
normalizer.normalize("今年")  # "2026年"

# 实体映射
mapper = EntityMapper()
mapper.map_product_name("cdn")  # "cdn"
mapper.map_field_name("金额")   # "出账金额"
```

## 测试结果

### TimeNormalizer 测试
```
✓ 今年           → 2026年
✓ 去年           → 2025年
✓ 本月           → 2026年1月
✓ 上月           → 2025年12月
✓ 本季度          → 2026年Q1
```

### EntityMapper 测试
```
✓ cdn          → cdn
✓ CDN          → cdn
✓ 内容分发网络       → cdn
✓ 金额     → 出账金额
✓ 费用     → 出账金额
```

## 配置要求

### 环境变量
需要在 `.env` 文件中配置 LLM API Key：

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# 或智谱 AI
ZHIPUAI_API_KEY=your_zhipuai_api_key
ZHIPUAI_MODEL=glm-4
```

### 新增依赖
无新增依赖，使用现有的 LangChain 依赖

## 项目结构变化

```
entity_extraction/
├── docs/
│   ├── rewrite.md              # 新增
│   ├── rewrite_README.md       # 新增
│   └── CHANGES.md              # 新增
├── src/langchain_entity_extraction/
│   ├── rewrite/                # 新增目录
│   │   ├── __init__.py
│   │   ├── question_rewriter.py
│   │   ├── time_normalizer.py
│   │   ├── entity_mapper.py
│   │   └── prompts.py
│   └── models/
│       └── rewrite_models.py   # 新增
├── tests/
│   ├── test_question_rewriter.py   # 新增
│   ├── test_rewrite_standalone.py  # 新增
│   └── test_rewrite_only.py        # 新增
└── scripts/
    └── question_rewrite_example.py # 新增
```

## 版本更新

- 版本号: 0.1.0 → 0.2.0
- 变更类型: minor (新增功能)

## 后续计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| 第一阶段 | 独立运行，验证改写效果 | ✓ 完成 |
| 第二阶段 | 与实体抽取服务集成 | 待开发 |
| 第三阶段 | 与SQL生成服务集成 | 待开发 |
| 第四阶段 | 集成到完整的问答流程 | 待开发 |

## 注意事项

1. **暂时独立运行**：当前未接入主流程，仅作为独立服务
2. **需要 API Key**：使用 LLM 功能需要配置有效的 API Key
3. **时间参考**：时间规范化以当前日期为参考
4. **可扩展配置**：产品别名和字段别名可在配置中扩展
