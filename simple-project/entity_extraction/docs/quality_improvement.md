# 实体抽取和语句改写准确率提升设计文档

## 1. 概述

本文档描述了针对实体抽取和语句改写服务的准确率提升方案。通过分析当前实现中的问题，提出**成本与准确率平衡**的改进策略，预期提升准确率 35-50%，成本增加 < 10%。

## 2. 问题分析

### 2.1 当前实现的问题

通过代码分析，识别出以下影响准确率的关键问题：

#### 问题 1：Schema 设计过于通用
**位置：** `src/langchain_entity_extraction/models/entity_schemas.py`

**当前代码：**
```python
class PersonEntity(BaseModel):
    name: str = Field(..., description="Full name of the person")
    age: Optional[int] = Field(None, description="Age in years", ge=0, le=150)
```

**问题分析：**
- 字段描述过于通用，缺少业务上下文
- LLM 无法准确理解应该提取什么样的实体
- 没有提供提取规则和约束说明

**影响程度：** 高
**预期提升：** +15-20%

#### 问题 2：缺少 Few-shot Learning
**位置：** `src/langchain_entity_extraction/extractors/pydantic_extractor.py`

**当前代码：**
```python
async def extract(self, text: str, schema: Type[BaseModel], **kwargs):
    chain = create_extraction_chain_pydantic(pydantic_schema=schema, llm=self.llm)
    result = await chain.ainvoke({"input": [text]})
```

**问题分析：**
- 仅依赖零样本推理
- LLM 没有具体的示例参考
- 输出格式和质量不稳定

**影响程度：** 高
**预期提升：** +20-25%

#### 问题 3：提示词设计简略
**位置：** `src/langchain_entity_extraction/rewrite/prompts.py`

**当前代码：**
```python
SYSTEM_PROMPT = """你是一个专业的问题改写助手...
改写规则：
1. 时间规范化...
2. 产品ID规范化...
"""
```

**问题分析：**
- 缺少具体的改写示例
- 没有边界情况处理指导
- 没有否定示例（什么不该做）

**影响程度：** 高
**预期提升：** +10-20%

#### 问题 4：JSON 解析容错性不足
**位置：** `src/langchain_entity_extraction/rewrite/question_rewriter.py`

**当前代码：**
```python
def _parse_response(self, response: str, original_question: str):
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        # fallback 逻辑过于简单
```

**问题分析：**
- LLM 返回非标准 JSON 时容易失败
- 降级处理不够智能
- 缺少多层解析策略

**影响程度：** 中
**预期提升：** 减少 5-10% 的失败率

#### 问题 5：缺少质量验证机制
**位置：** `src/langchain_entity_extraction/models/rewrite_models.py`

**当前代码：**
```python
confidence: float = Field(default=0.8, ge=0.0, le=1.0)
```

**问题分析：**
- confidence 字段未被实际使用
- 缺少业务规则验证
- 没有质量评估机制

**影响程度：** 中
**预期提升：** +10-15%

### 2.2 影响准确率的关键因素

| 因素 | 影响程度 | 当前状态 | 改进优先级 |
|------|----------|----------|------------|
| Schema 描述质量 | 高 | 过于通用 | P0 |
| Few-shot 示例 | 高 | 缺失 | P0 |
| 提示词设计 | 高 | 简略 | P0 |
| 解析容错性 | 中 | 脆弱 | P1 |
| 质量验证 | 中 | 缺失 | P1 |

## 3. 改进方案

### 3.1 核心策略

```
优化提示词（零成本）
    +
Few-shot Learning（低成本，Token +8-12%）
    +
规则验证（本地）
    +
LLM 参数优化（零成本)
    =
准确率提升 35-50%，成本增加 < 5%
```

### 3.2 预期效果

| 改进项 | 预期提升 | 成本影响 | 实施难度 |
|--------|----------|----------|----------|
| 增强 Schema 描述 | +15-20% | 零成本 | 低 |
| Few-shot Learning | +20-25% | Token +8-12% | 中 |
| 业务规则验证 | +10-15% | 本地验证 | 低 |
| LLM 参数优化 | +5-10% | 零成本 | 低 |
| 提示词优化 | +10-15% | 零成本 | 低 |
| **总计** | **+35-50%** | **< 5% 成本增加** | - |

## 4. 详细设计方案

### 4.1 增强 Schema 描述（P0）

**目标文件：** `src/langchain_entity_extraction/models/entity_schemas.py`

**设计要点：**

1. **添加业务上下文文档字符串**
   - 说明业务场景
   - 定义提取原则
   - 列出边界情况

2. **增强 Field description**
   - 业务含义
   - 提取规则
   - 约束条件
   - 正确和错误示例

**改进示例：**

```python
class PersonEntity(BaseModel):
    """
    业务人员实体

    业务场景：
    - 从产品咨询、销售记录、客户服务等中文业务文本中提取人员信息
    - 人员通常与公司、职位、联系方式相关联
    - 中文名可能包含"先生"、"女士"等称谓

    提取原则：
    1. 只提取明确的实体信息，不推测或补充
    2. 优先提取结构化信息（姓名、年龄、职位）
    3. 遇到模糊信息时保持保守（缺失胜过错误）
    4. 不提取泛指词（如"客户"、"用户"）

    示例：
    - ✓ "张三" → 提取姓名
    - ✓ "张三先生" → 提取"张三"（去除称谓）
    - ✗ "客户李先生" → 不提取或仅提取"李"
    - ✗ "某工程师" → 不提取
    """

    name: str = Field(
        ...,
        description="""
        人员全名。

        提取规则：
        - 必须是具体姓名（中文2-4字，或英文标准格式）
        - 去除称谓（"先生"、"女士"、"经理"、"工程师"等）
        - 不提取泛指词（"客户"、"用户"、"某人"、"一位"）

        示例：
        - "张三先生" → "张三"
        - "John Smith" → "John Smith"
        - "李经理" → "李"
        - "客户王女士" → "王"或null

        验证规则：
        - 长度：中文 2-4 字，英文按标准格式
        - 不包含：称谓、泛指词
        """
    )

    age: Optional[int] = Field(
        None,
        description="""
        年龄（数字）。

        提取规则：
        - 必须是明确的数字（如"30岁"中的30）
        - 范围：18-80岁（业务场景通常在此范围）
        - 不提取："年轻"、"中年"、"20多岁"等描述

        示例：
        - "30岁" → 30
        - "二十五岁" → 25
        - "年轻" → null
        - "20多岁" → null

        验证规则：
        - 数值范围：18-80
        """,
        ge=18,
        le=80
    )

    title: Optional[str] = Field(
        None,
        description="""
        职位或职称。

        提取规则：
        - 提取完整职位名称（如"软件工程师"、"销售经理"）
        - 去除"资深"、"高级"等修饰词（除非是职位级别）
        - 常见职位：经理、总监、工程师、顾问、主管等

        示例：
        - "软件工程师" → "软件工程师"
        - "资深产品经理" → "产品经理"或"资深产品经理"
        - "李经理" → 此时从 name 提取，title 为 null

        验证规则：
        - 不包含姓名信息
        - 长度：2-10 字
        """
    )

    organization: Optional[str] = Field(
        None,
        description="""
        公司名称或组织名称。

        提取规则：
        - 提取公司全称或标准简称
        - 去除"公司"、"有限公司"、"科技"等常见后缀
        - 不包含：地点、部门信息

        示例：
        - "阿里巴巴公司" → "阿里巴巴"
        - "华为技术有限公司" → "华为"
        - "腾讯北京分公司" → "腾讯"
        - "阿里云" → "阿里云"（产品名，不提取）

        验证规则：
        - 不是产品名（如 cdn、ecs、oss）
        - 长度：2-20 字
        """
    )

    email: Optional[str] = Field(
        None,
        description="""
        电子邮件地址。

        提取规则：
        - 标准邮箱格式：xxx@xxx.xxx
        - 去除前后空格和标点

        示例：
        - "zhangsan@example.com" → "zhangsan@example.com"
        - "邮箱：john@example.com" → "john@example.com"

        验证规则：
        - 包含 @ 符号
        - 域名部分至少有一个点
        """
    )

    phone: Optional[str] = Field(
        None,
        description="""
        电话号码。

        提取规则：
        - 手机号：11位数字（1开头）
        - 座机：区号+号码（如 010-12345678）
        - 去除空格、短横线等格式符号

        示例：
        - "13812345678" → "13812345678"
        - "138-1234-5678" → "13812345678"
        - "010-12345678" → "01012345678"

        验证规则：
        - 数字长度：7-15位
        - 只包含数字（提取后）
        """
    )

    skills: List[str] = Field(
        default_factory=list,
        description="""
        技能或专长列表。

        提取规则：
        - 提取明确的技能名称
        - 常见技能：Python、Java、机器学习、数据分析等
        - 不提取泛指词（"技术"、"能力"）

        示例：
        - "擅长Python和机器学习" → ["Python", "机器学习"]
        - "熟悉技术" → []

        验证规则：
        - 每个技能 2-10 字
        - 去除重复
        """
    )
```

**同样方式增强其他 Schema：**
- `OrganizationEntity` - 添加公司/组织识别规则
- `ProductEntity` - 添加产品识别规则（区分产品名和公司名）
- `LocationEntity` - 添加地点识别规则
- `EventEntity` - 添加事件识别规则

### 4.2 Few-shot Learning 实现（P0）

**目标文件：**
- `src/langchain_entity_extraction/extractors/pydantic_extractor.py`
- `src/langchain_entity_extraction/extractors/schema_extractor.py`

**设计要点：**

1. **示例选择策略**
   - 每个 Schema 3-5 个示例
   - 覆盖简单、复杂、边界情况
   - 使用真实业务案例

2. **示例数据结构**
```python
FEW_SHOT_EXAMPLES = {
    "PersonEntity": [
        {
            "text": "阿里巴巴的软件工程师张三，今年30岁，负责CDN产品开发，邮箱是zhangsan@example.com",
            "expected": {
                "name": "张三",
                "age": 30,
                "title": "软件工程师",
                "organization": "阿里巴巴",
                "email": "zhangsan@example.com"
            },
            "reasoning": "提取了明确的姓名、年龄、职位、公司和邮箱信息"
        },
        {
            "text": "李经理联系我们咨询云主机产品，表示公司需要扩容",
            "expected": {
                "name": "李",
                "title": "经理",
                "organization": None,
                "age": None
            },
            "reasoning": "只有姓氏和职位，没有完整姓名和公司信息"
        },
        {
            "text": "一位30岁的客户咨询产品价格",
            "expected": {
                "name": None,  # 或不提取
                "age": 30
            },
            "reasoning": "没有明确姓名，但有年龄信息"
        },
        {
            "text": "华为的王五和赵六讨论CDN产品合作",
            "expected": [
                {"name": "王五", "organization": "华为"},
                {"name": "赵六", "organization": "华为"}
            ],
            "reasoning": "识别了两个人，都来自华为"
        }
    ],
    "OrganizationEntity": [
        {
            "text": "华为技术有限公司成立于1987年，总部位于深圳，主营通信设备",
            "expected": {
                "name": "华为技术有限公司",
                "founded_year": 1987,
                "headquarters": "深圳",
                "industry": "通信设备"
            }
        },
        {
            "text": "阿里巴巴和腾讯合作推出新服务",
            "expected": [
                {"name": "阿里巴巴"},
                {"name": "腾讯"}
            ]
        }
    ],
    "ProductEntity": [
        {
            "text": "阿里云CDN产品价格为每GB 0.2元，支持加速和安全功能",
            "expected": {
                "name": "CDN",
                "price": 0.2,
                "currency": "元",
                "features": ["加速", "安全"],
                "manufacturer": "阿里云"
            }
        }
    ]
}
```

3. **提示词构建方法**
```python
def _build_prompt_with_examples(
    self,
    schema: Type[BaseModel],
    examples: List[Dict],
    text: str
) -> str:
    """
    构建包含 Few-shot 示例的提示词

    三层结构：
    1. 任务定义 - 清晰说明要做什么
    2. 示例演示 - 展示正确的提取方式
    3. 当前任务 - 待处理的输入
    """

    schema_name = schema.__name__
    schema_doc = schema.__doc__ or ""

    prompt_parts = [
        f"# 任务：从中文业务文本中提取 {schema_name} 实体\n",
        f"## 实体定义\n{schema_doc}\n",
        "## 提取示例\n"
    ]

    # 添加示例
    for i, example in enumerate(examples, 1):
        prompt_parts.append(f"### 示例 {i}")
        prompt_parts.append(f"**输入文本：**\n{example['text']}\n")
        prompt_parts.append(f"**期望输出：**\n```json\n{json.dumps(example['expected'], ensure_ascii=False, indent=2)}\n```")
        if 'reasoning' in example:
            prompt_parts.append(f"**说明：** {example['reasoning']}\n")

    # 添加当前任务
    prompt_parts.extend([
        "\n## 当前任务",
        f"**输入文本：**\n{text}\n",
        "**输出（JSON格式）：**"
    ])

    return "\n".join(prompt_parts)
```

4. **修改 extract 方法**
```python
async def extract(
    self,
    text: str,
    schema: Type[BaseModel],
    use_few_shot: bool = True,
    **kwargs
) -> ExtractionResult:
    """
    Extract entities from text using Pydantic model.

    Args:
        text: Input text to extract entities from
        schema: Pydantic model class defining entity structure
        use_few_shot: Whether to use Few-shot examples (default: True)
    """
    start_time = time.time()
    text_length = len(text)
    schema_name = schema.__name__

    try:
        # 创建抽取链
        chain = create_extraction_chain_pydantic(
            pydantic_schema=schema,
            llm=self.llm
        )

        # 是否使用 Few-shot
        if use_few_shot:
            # 获取示例
            examples = self.FEW_SHOT_EXAMPLES.get(schema_name, [])

            # 构建增强提示词
            enhanced_text = self._build_prompt_with_examples(
                schema, examples, text
            )

            self.logger.debug(
                f"Starting Few-shot extraction",
                schema=schema_name,
                text_length=len(enhanced_text),
                example_count=len(examples)
            )

            # 使用增强提示词
            result = await chain.ainvoke({"input": [enhanced_text]})
        else:
            # 原有逻辑
            result = await chain.ainvoke({"input": [text]})

        # 解析结果
        entities = self._parse_result(result)

        extraction_time_ms = self._measure_time(start_time)

        self.logger.info(
            f"Pydantic extraction completed",
            schema=schema_name,
            entity_count=len(entities),
            time_ms=extraction_time_ms,
            used_few_shot=use_few_shot
        )

        return self._create_result(
            entities=entities,
            schema_type=schema_name,
            text_length=text_length,
            extraction_time_ms=extraction_time_ms,
            raw_output=result if self.config.get("include_raw_output") else None
        )

    except Exception as e:
        self.logger.error(f"Pydantic extraction failed: {str(e)}")
        return self.handle_error(
            e,
            {
                "text_length": text_length,
                "schema": str(schema)
            }
        )
```

### 4.3 语句改写提示词优化（P0）

**目标文件：** `src/langchain_entity_extraction/rewrite/prompts.py`

**设计要点：**

1. **添加完整的改写示例**
2. **包含边界情况处理**
3. **添加否定示例**

**改进后的 SYSTEM_PROMPT：**

```python
SYSTEM_PROMPT = """你是一个专业的问题改写助手。你的任务是将用户的自然语言问题改写成结构化、明确的问题，以便后续的实体识别和SQL生成。

## 改写规则

### 1. 时间规范化
将相对时间表达转换为明确的绝对时间：

| 原始表达 | 改写后 |
|---------|--------|
| 今年 | 2026年 |
| 上月 | 2025年12月 |
| 去年 | 2025年 |
| 本季度 | 2026年Q1 |
| 最近7天 | 2026-01-22至2026-01-29 |
| 本周 | 2026年第5周 |

### 2. 产品ID规范化
将产品简称或别名转换为标准的产品ID表达：

| 原始表达 | 改写后 |
|---------|--------|
| cdn / CDN / 内容分发 | 产品ID为cdn |
| ecs / ECS / 云主机 | 产品ID为ecs |
| oss / OSS / 对象存储 | 产品ID为oss |
| rds / RDS / 云数据库 | 产品ID为rds |
| slb / SLB / 负载均衡 | 产品ID为slb |

### 3. 字段明确化
将模糊的字段描述转换为明确的字段名：

| 原始表达 | 改写后 |
|---------|--------|
| 金额 / 费用 / 钱 | 出账金额 |
| 数量 / 个数 / 单数 | 订单数量 |
| 收入 / 营收 | 营业收入 |
| 用户数 / 客户数 | 用户数 |

### 4. 结构化重组
将问题改写为结构化的查询模式：
- 模式：`{实体类型}为{值}，{条件}的{指标}是多少`
- 多个产品：`产品ID为A和产品ID为B，{条件}的{指标}是多少`

## 完整改写示例

### 示例 1：简单时间规范化
**输入：**
```
今年cdn产品金额是多少
```

**输出：**
```json
{
  "rewritten": "产品ID为cdn，时间为2026年的出账金额是多少",
  "entities": {
    "product_id": "cdn",
    "time": "2026年",
    "field": "出账金额"
  },
  "reasoning": "将'今年'规范化为'2026年'，'cdn'规范化为'产品ID为cdn'，'金额'明确为'出账金额'",
  "changes_made": [
    "时间规范化：今年 → 2026年",
    "产品ID规范化：cdn → 产品ID为cdn",
    "字段明确化：金额 → 出账金额"
  ]
}
```

### 示例 2：多条件查询
**输入：**
```
上月ecs和oss产品的订单数量总和
```

**输出：**
```json
{
  "rewritten": "产品ID为ecs和产品ID为oss，时间为2025年12月的订单数量总和是多少",
  "entities": {
    "product_id": ["ecs", "oss"],
    "time": "2025年12月",
    "field": "订单数量"
  },
  "reasoning": "识别了两个产品（ecs和oss），将'上月'转换为具体日期（2025年12月），将'数量'明确为'订单数量'",
  "changes_made": [
    "多产品识别：ecs和oss",
    "时间规范化：上月 → 2025年12月",
    "字段明确化：数量 → 订单数量"
  ]
}
```

### 示例 3：相对时间转换
**输入：**
```
最近7天cdn产品的流量数据
```

**输出：**
```json
{
  "rewritten": "产品ID为cdn，时间为2026-01-22至2026-01-29的流量是多少",
  "entities": {
    "product_id": "cdn",
    "time": "2026-01-22至2026-01-29",
    "field": "流量"
  },
  "reasoning": "将'最近7天'转换为具体日期范围（从当前日期2026-01-29往前推7天）",
  "changes_made": [
    "日期范围计算：最近7天 → 2026-01-22至2026-01-29"
  ]
}
```

### 示例 4：复杂嵌套查询
**输入：**
```
去年四季度北京地区cdn和ecs产品的总金额
```

**输出：**
```json
{
  "rewritten": "产品ID为cdn和产品ID为ecs，时间为2025年四季度，地区为北京的出账金额总和是多少",
  "entities": {
    "product_id": ["cdn", "ecs"],
    "time": "2025年四季度",
    "region": "北京",
    "field": "出账金额"
  },
  "reasoning": "识别了两个产品、时间（去年四季度→2025年四季度）、地区（北京），将'金额'明确为'出账金额'",
  "changes_made": [
    "多产品识别",
    "时间规范化：去年四季度 → 2025年四季度",
    "地区识别：北京",
    "字段明确化：金额 → 出账金额"
  ]
}
```

## 边界情况处理

### 情况 1：缺少某些实体类型
**输入：**
```
cdn产品的金额是多少
```
（缺少时间信息）

**输出：**
```json
{
  "rewritten": "产品ID为cdn的出账金额是多少",
  "entities": {
    "product_id": "cdn",
    "field": "出账金额"
  },
  "reasoning": "只有产品和字段信息，缺少时间信息，保持原样"
}
```

### 情况 2：模糊的时间表达
**输入：**
```
那时候cdn产品的金额
```
（"那时候"无法确定具体时间）

**输出：**
```json
{
  "rewritten": "产品ID为cdn的出账金额是多少",
  "entities": {
    "product_id": "cdn",
    "field": "出账金额"
  },
  "reasoning": "无法确定'那时候'的具体时间，移除时间信息，保留产品和字段"
}
```

### 情况 3：未知产品
**输入：**
```
今年ABC产品的金额是多少
```
（ABC 不在已知产品列表中）

**输出：**
```json
{
  "rewritten": "产品为ABC，时间为2026年的出账金额是多少",
  "entities": {
    "product_id": "ABC",
    "time": "2026年",
    "field": "出账金额"
  },
  "reasoning": "ABC不是标准产品ID，保持原样但添加'产品为'前缀"
}
```

## 输出格式要求

请严格按照以下 JSON 格式输出：

```json
{
  "rewritten": "改写后的问题",
  "entities": {
    "product_id": "产品ID或ID列表（如果有）",
    "time": "时间信息（如果有）",
    "field": "字段名（如果有）",
    "region": "地区（如果有）"
  },
  "reasoning": "改写的推理过程说明",
  "changes_made": ["改动1", "改动2", ...]
}
```

**重要提醒：**
- 必须严格按照 JSON 格式输出
- 保持问题的语义一致性
- 如果某个实体类型不存在，对应字段设为 null 或省略
- changes_made 应该列出所有主要改动
- 对于未知产品或无法解析的时间，保持原样但尽量结构化
"""
```

### 4.4 JSON 解析容错性增强（P1）

**目标文件：** `src/langchain_entity_extraction/rewrite/question_rewriter.py`

**设计要点：**

实现多层解析策略：

```python
def _parse_response(self, response: str, original_question: str) -> RewrittenQuestion:
    """
    多层容错的 JSON 解析

    解析策略（按优先级）：
    1. 标准 JSON 解析
    2. Markdown 代码块提取
    3. 正则表达式提取
    4. 逐行提取
    5. 智能文本提取（兜底）
    """

    # 清理响应
    response = response.strip()

    # 策略 1: 标准 JSON 解析
    try:
        # 移除 markdown 代码块标记
        if response.startswith("```"):
            lines = response.split('\n')
            if lines[0].startswith("```"):
                response = '\n'.join(lines[1:])
            if response.rstrip().endswith("```"):
                response = '\n'.join(response.split('\n')[:-1])

        data = json.loads(response.strip())
        return self._validate_and_create_rewritten(data, original_question)

    except json.JSONDecodeError as e:
        self.logger.debug(f"Standard JSON parsing failed: {e}")

    # 策略 2: 正则提取 JSON 对象
    try:
        # 匹配最外层的 JSON 对象
        json_pattern = r'\{[^{}]*(?:"[^"]*"[^{}]*)*\}'
        # 支持嵌套的简化正则
        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'

        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            # 尝试每个匹配
            for match in matches:
                try:
                    data = json.loads(match)
                    # 验证是否包含必需字段
                    if "rewritten" in data:
                        return self._validate_and_create_rewritten(data, original_question)
                except:
                    continue
    except Exception as e:
        self.logger.debug(f"Regex extraction failed: {e}")

    # 策略 3: 逐行提取
    try:
        data = self._extract_json_line_by_line(response)
        if data and "rewritten" in data:
            return self._validate_and_create_rewritten(data, original_question)
    except Exception as e:
        self.logger.debug(f"Line-by-line extraction failed: {e}")

    # 策略 4: 智能文本提取（兜底）
    return self._extract_from_text(response, original_question)


def _extract_from_text(self, response: str, original: str) -> RewrittenQuestion:
    """
    从非 JSON 文本中智能提取信息

    尝试模式：
    1. 查找"改写后问题："或"rewritten:"等关键词
    2. 提取冒号后的内容
    """

    rewritten = original  # 默认保持原样
    entities = {}
    reasoning = ""

    lines = response.split('\n')

    for line in lines:
        # 查找改写后的问题
        if '改写后' in line or 'rewritten' in line.lower():
            # 提取冒号后的内容
            if ':' in line:
                parts = line.split(':', 1)
                candidate = parts[1].strip()
                # 去除引号和标点
                candidate = candidate.strip('"').strip("'").strip('。')
                if len(candidate) > 5:  # 至少5个字符
                    rewritten = candidate

        # 查找实体信息
        if '产品ID' in line or 'product_id' in line.lower():
            # 尝试提取产品ID
            match = re.search(r'产品ID为[\"\']?([^\s\"\']+)', line)
            if match:
                entities['product_id'] = match.group(1)

        if '时间' in line or '202' in line:  # 202x年
            match = re.search(r'时间为[\"\']?([^\s\"\']+)', line)
            if match:
                entities['time'] = match.group(1)

    return RewrittenQuestion(
        original=original,
        rewritten=rewritten,
        entities=entities,
        reasoning=reasoning or "使用兜底解析策略",
        changes_made=[]
    )


def _validate_and_create_rewritten(
    self,
    data: Dict,
    original: str
) -> RewrittenQuestion:
    """
    验证并创建改写结果
    """
    # 确保必需字段存在
    if "rewritten" not in data:
        raise ValueError("缺少 'rewritten' 字段")

    # 验证 entities
    entities = data.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}

    # 验证 reasoning
    reasoning = data.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = ""

    # 验证 changes_made
    changes = data.get("changes_made", [])
    if not isinstance(changes, list):
        changes = []

    # 计算置信度
    confidence = 0.8  # 默认值
    if reasoning or len(entities) >= 2:
        confidence = 0.95
    elif len(entities) == 1:
        confidence = 0.85

    return RewrittenQuestion(
        original=original,
        rewritten=data["rewritten"],
        entities=entities,
        reasoning=reasoning,
        changes_made=changes,
        confidence=confidence
    )
```

### 4.5 质量验证机制（P1）

**新增文件：** `src/langchain_entity_extraction/rewrite/validation.py`

**设计要点：**

```python
"""Validation rules for rewritten questions."""

import re
from typing import Tuple, List
from langchain_entity_extraction.models.rewrite_models import RewrittenQuestion
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class RewriteValidator:
    """
    改写结果验证器

    验证改写结果是否符合业务规则和质量标准。
    """

    # 相对时间模式（不应该出现在改写后的问题中）
    RELATIVE_TIME_PATTERNS = [
        r'今年', r'去年', r'上年', r'本年',
        r'本月', r'上月', r'上个月', r'这月',
        r'本季度', r'上季度', r'这个季度',
        r'最近\d+天', r'近\d+天',
        r'本周', r'上周',
    ]

    # 模糊字段模式
    VAGUE_FIELD_PATTERNS = {
        '金额': r'(?<!出账|总|账单)金额',  # 负向后行断言
        '数量': r'(?<!订单|产品)数量',
        '收入': r'(?<!营业|业务)收入',
    }

    def validate(self, result: RewrittenQuestion) -> Tuple[bool, List[str]]:
        """
        综合验证改写结果

        Returns:
            (是否通过验证, 问题列表)
        """
        issues = []

        # 1. 时间表达验证
        if not self._validate_time_expressions(result.rewritten):
            issues.append("改写结果仍包含相对时间表达")

        # 2. 产品格式验证
        if not self._validate_product_format(result.rewritten):
            issues.append("产品格式不规范，应使用'产品ID为xxx'格式")

        # 3. 字段明确性验证
        field_issues = self._validate_field_specificity(result.rewritten)
        if field_issues:
            issues.extend(field_issues)

        # 4. 结构完整性验证
        if not self._validate_structure(result):
            issues.append("改写结果结构不完整")

        return len(issues) == 0, issues

    def _validate_time_expressions(self, text: str) -> bool:
        """
        验证时间表达是否规范

        Returns:
            True 如果不包含相对时间表达
        """
        for pattern in self.RELATIVE_TIME_PATTERNS:
            if re.search(pattern, text):
                logger.debug(f"Found relative time pattern: {pattern}")
                return False
        return True

    def _validate_product_format(self, text: str) -> bool:
        """
        验证产品格式是否规范

        Returns:
            True 如果产品格式规范
        """
        # 检查是否包含产品相关词汇
        product_keywords = ['cdn', 'ecs', 'oss', 'rds', 'slb', '产品']
        has_product = any(keyword in text.lower() for keyword in product_keywords)

        if not has_product:
            return True  # 没有产品信息，无需验证

        # 如果有产品信息，应该使用"产品ID为"格式
        return '产品ID为' in text

    def _validate_field_specificity(self, text: str) -> List[str]:
        """
        验证字段是否明确

        Returns:
            问题列表
        """
        issues = []

        # 检查模糊字段
        vague_field = '金额'
        if vague_field in text:
            # 检查是否已明确
            if '出账金额' not in text and '账单金额' not in text and '总金额' not in text:
                issues.append(f"字段'{vague_field}'不够明确，应使用'出账金额'等")

        return issues

    def _validate_structure(self, result: RewrittenQuestion) -> bool:
        """
        验证结构完整性

        Returns:
            True 如果结构完整
        """
        # 基本长度检查
        if len(result.rewritten) < 5:
            return False

        # 必需字段检查
        if not result.rewritten:
            return False

        # entities 应该是字典
        if not isinstance(result.entities, dict):
            return False

        return True

    def get_validation_score(self, result: RewrittenQuestion) -> float:
        """
        计算验证分数（0-1）

        Returns:
            验证分数
        """
        passed, issues = self.validate(result)

        if passed:
            return 1.0

        # 根据问题数量计算分数
        max_issues = 5  # 假设最多5个问题
        score = max(0.0, 1.0 - (len(issues) / max_issues))

        return score
```

### 4.6 LLM 参数优化（P1）

**目标文件：** `config/extraction_config.yaml`

**设计要点：**

```yaml
# 优化后的配置
extraction:
  strategy: pydantic

  llm:
    # 使用性价比更高的模型
    provider: ${LLM_PROVIDER:-openai}
    model: ${OPENAI_MODEL:-gpt-4o-mini}  # 从 gpt-4 改为 gpt-4o-mini

    # 参数优化
    temperature: 0.0  # 保持低温度确保稳定性
    max_tokens: 1000   # 限制输出长度
    top_p: 0.9         # 略微降低以提高准确性
    presence_penalty: 0.0  # 不鼓励创新
    frequency_penalty: 0.0  # 不惩罚重复
    request_timeout: 60
    max_retries: 3

  # Few-shot 配置
  few_shot:
    enabled: true
    examples_per_schema: 5  # 每个 Schema 5 个示例
    include_reasoning: true  # 包含推理说明

  # 验证配置
  validation:
    enabled: true
    strict_mode: false  # 标准模式（平衡准确率和召回率）
    min_confidence: 0.7  # 最低置信度阈值

  # 输出配置
  output:
    include_confidence: true
    include_raw_output: false
    format: json

# 实体类型配置保持不变
entity_types:
  person:
    enabled: true
    # ...
```

## 5. 实施计划

### 5.1 实施阶段

| 阶段 | 内容 | 文件 | 工作量 |
|------|------|------|--------|
| **阶段 1** | 增强 Schema 描述 | entity_schemas.py | 2h |
| **阶段 2** | 优化 LLM 参数 | extraction_config.yaml | 0.5h |
| **阶段 3** | 增强提示词 | prompts.py | 2h |
| **阶段 4** | 实现 Few-shot | pydantic_extractor.py, schema_extractor.py | 6h |
| **阶段 5** | 增强解析 | question_rewriter.py | 2h |
| **阶段 6** | 实现验证器 | validation.py (新增) | 2h |
| **阶段 7** | 实现质量检查 | quality_checker.py (新增) | 3h |
| **阶段 8** | 测试 | test_quality_improvement.py | 2h |
| **阶段 9** | 文档 | quality_improvement.md | 1h |

**总工作量：** 约 20.5 小时（2.5 个工作日）

### 5.2 关键文件列表

| 文件路径 | 改动类型 | 优先级 |
|----------|----------|--------|
| `src/.../models/entity_schemas.py` | 增强 Schema 描述 | P0 |
| `src/.../extractors/pydantic_extractor.py` | 添加 Few-shot | P0 |
| `src/.../extractors/schema_extractor.py` | 添加 Few-shot | P0 |
| `src/.../rewrite/prompts.py` | 增强提示词 | P0 |
| `config/extraction_config.yaml` | 优化参数 | P1 |
| `src/.../rewrite/question_rewriter.py` | 增强解析 | P1 |
| `src/.../rewrite/validation.py` | 新增验证器 | P1 |
| `src/.../quality/quality_checker.py` | 新增质量检查 | P1 |

## 6. 测试验证

### 6.1 测试策略

**单元测试：**
- Few-shot 效果对比测试
- 验证规则测试
- JSON 解析鲁棒性测试

**集成测试：**
- 端到端流程测试
- 改进前后准确率对比

**质量评估：**
- 准确率 (Precision)
- 召回率 (Recall)
- F1 分数

### 6.2 评估指标

```python
def calculate_metrics(extracted_entities, expected_entities):
    """计算评估指标"""

    # 准确率 = 正确抽取数 / 总抽取数
    precision = len(extracted_entities & expected_entities) / len(extracted_entities)

    # 召回率 = 实际抽取数 / 应该抽取数
    recall = len(extracted_entities & expected_entities) / len(expected_entities)

    # F1 分数
    f1 = 2 * (precision * recall) / (precision + recall)

    return {
        "precision": precision * 100,  # %
        "recall": recall * 100,        # %
        "f1_score": f1 * 100          # %
    }
```

## 7. 成本效益分析

### 7.1 投入

| 项目 | 成本 |
|------|------|
| 开发时间 | 2.5 个工作日 |
| Token 成本增加 | < 10% |
| 维护成本 | 低（每月 1-2 小时） |

### 7.2 产出

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 准确率 | 60% | 81-90% | +35-50% |
| 召回率 | 70% | 77-80% | +10-15% |
| 一致性 | 50% | 70-80% | +40-60% |
| 人工修正成本 | 100% | 25-50% | -50-75% |

### 7.3 ROI 分析

假设当前准确率为 60%，错误率为 40%：
- 改进后准确率：81-90%
- 错误率降低：从 40% 降至 10-19%
- **减少人工修正成本：50-75%**

## 8. 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Token 成本增加 | 中 | 使用高质量少量示例；使用 gpt-4o-mini |
| 示例维护成本 | 低 | 存储在配置文件；版本管理 |
| 过度拟合 | 低 | 保持示例多样性；定期 A/B 测试 |

## 9. 附录

### 9.1 Few-shot 示例数据

**PersonEntity 示例：**

```python
PERSON_EXAMPLES = [
    {
        "text": "阿里巴巴的软件工程师张三，今年30岁，负责CDN产品开发",
        "expected": {"name": "张三", "age": 30, "title": "软件工程师", "organization": "阿里巴巴"}
    },
    {
        "text": "李经理联系我们咨询云主机产品",
        "expected": {"name": "李", "title": "经理"}
    },
    {
        "text": "一位30岁的客户咨询产品",
        "expected": {"age": 30}
    }
]
```

### 9.2 语句改写示例

**简单示例：**
- 输入：`今年cdn产品金额是多少`
- 输出：`产品ID为cdn，时间为2026年的出账金额是多少`

**复杂示例：**
- 输入：`去年四季度北京地区cdn和ecs产品的总金额`
- 输出：`产品ID为cdn和产品ID为ecs，时间为2025年四季度，地区为北京的出账金额总和是多少`

### 9.3 验证规则

**时间验证：**
- 不应包含：今年、去年、本月、上月等

**产品格式：**
- 应该使用：产品ID为xxx

**字段明确性：**
- 金额 → 出账金额
- 数量 → 订单数量
