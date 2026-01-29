# 基于小模型的实体识别与语句改写方案

## 1. 方案概述

### 1.1 核心思路

使用**预训练小模型**替代大模型（LLM）进行实体识别和语句改写，实现：
- **成本降低 90%+**（无需每次 API 调用）
- **速度提升 10-100 倍**（本地推理）
- **数据隐私安全**（数据不出本地）
- **可控性强**（模型完全自主）

### 1.2 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      输入：用户问题                            │
│                 "今年cdn产品金额是多少"                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────┐
        │   实体识别小模型 (NER)         │
        │   - BERT-based Tagger         │
        │   - 本地推理，~10ms           │
        └────────────────┬─────────────┘
                         │
                         ▼
              ┌─────────────────┐
              │  识别的实体       │
              │  {              │
              │   product_id: cdn│
              │   time: 今年      │
              │   field: 金额     │
              │  }              │
              └─────────────────┘
                         │
                         ▼
        ┌──────────────────────────────┐
        │   语句改写小模型 (Seq2Seq)    │
        │   - T5 / BART               │
        │   - 本地推理，~50ms          │
        └────────────────┬─────────────┘
                         │
                         ▼
        ┌──────────────────────────────┐
        │      改写后的问题             │
        │ "产品ID为cdn，时间为2026年的    │
        │  出账金额是多少"               │
        └──────────────────────────────┘
```

### 1.3 模型选型

#### 方案 A：完全开源方案（推荐）

| 任务 | 模型 | 参数量 | 推理速度 | 准确率 |
|------|------|--------|----------|--------|
| 实体识别 | **Chinese-BERT-wwm** | 110M | ~10ms | 85-90% |
| 实体识别 | **RoBERTa-chinese-base** | 102M | ~8ms | 88-92% |
| 语句改写 | **T5-Chinese-small** | 77M | ~50ms | 80-85% |
| 语句改写 | **BART-base-chinese** | 140M | ~40ms | 82-87% |

#### 方案 B：国产模型方案

| 任务 | 模型 | 参数量 | 推理速度 | 准确率 |
|------|------|--------|----------|--------|
| 实体识别 | **Qwen-BERT** | 110M | ~10ms | 90-93% |
| 实体识别 | **ChatGLM2-6B**（微调） | 6B | ~100ms | 92-95% |
| 语句改写 | **Qwen-VL**（指令微调） | 7B | ~150ms | 88-92% |

#### 方案 C：轻量级方案（边缘设备）

| 任务 | 模型 | 参数量 | 推理速度 | 准确率 | 适用场景 |
|------|------|--------|----------|--------|----------|
| 实体识别 | **DistilBERT-Chinese** | 66M | ~5ms | 82-87% | 高并发 |
| 语句改写 | **TinyT5-Chinese** | 30M | ~30ms | 78-83% | 移动端 |

## 2. 实体识别模型设计

### 2.1 模型架构

基于 BERT 的序列标注模型：

```python
# 伪代码示意
class EntityRecognitionModel(nn.Module):
    """
    基于 BERT 的实体识别模型

    Architecture:
    1. BERT Encoder - 中文预训练模型
    2. Dropout Layer - 防止过拟合
    3. Linear Classifier - 实体类型分类
    4. CRF Layer - 序列标签优化
    """

    def __init__(self, num_entity_types, bert_model="bert-base-chinese"):
        self.bert = BertModel.from_pretrained(bert_model)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(768, num_entity_types)
        self.crf = CRF(num_entity_types, batch_first=True)

    def forward(self, input_ids, attention_mask, labels=None):
        # BERT encoding
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state

        # Classification
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)

        # CRF decoding
        if labels is not None:
            loss = self.crf(logits, labels, mask=attention_mask)
            return -loss
        else:
            predictions = self.crf.decode(logits, mask=attention_mask)
            return predictions
```

### 2.2 实体标签体系

采用 **BIO** (Beginning, Inside, Outside) 标注格式：

| 标签 | 说明 | 示例 |
|------|------|------|
| O | 非实体 | "今天" |
| B-PRODUCT | 产品开始 | "cdn" |
| I-PRODUCT | 产品内部 | "云主机" |
| B-TIME | 时间开始 | "今年" |
| I-TIME | 时间内部 | "2026年" |
| B-FIELD | 字段开始 | "金额" |
| I-FIELD | 字段内部 | "出账金额" |

### 2.3 训练数据格式

#### 实体识别训练数据（JSONL 格式）

**文件格式：** `data/ner/train.jsonl`

```jsonl
{"text": "今年cdn产品金额是多少", "entities": [{"entity": "cdn", "label": "PRODUCT", "start": 2, "end": 5}, {"entity": "今年", "label": "TIME", "start": 0, "end": 2}, {"entity": "金额", "label": "FIELD", "start": 6, "end": 8}]}
{"text": "上月ecs产品的订单数量", "entities": [{"entity": "上月", "label": "TIME", "start": 0, "end": 2}, {"entity": "ecs", "label": "PRODUCT", "start": 3, "end": 6}, {"entity": "数量", "label": "FIELD", "start": 11, "end": 13}]}
{"text": "华为技术有限公司成立于1987年", "entities": [{"entity": "华为技术有限公司", "label": "ORG", "start": 0, "end": 9}, {"entity": "1987年", "label": "TIME", "start": 14, "end": 19}]}
{"text": "阿里云CDN产品价格为每GB 0.2元", "entities": [{"entity": "阿里云", "label": "ORG", "start": 0, "end": 3}, {"entity": "CDN", "label": "PRODUCT", "start": 3, "end": 6}, {"entity": "0.2元", "label": "PRICE", "start": 16, "end": 20}]}
{"text": "张三是阿里巴巴的软件工程师，今年30岁", "entities": [{"entity": "张三", "label": "PERSON", "start": 0, "end": 2}, {"entity": "阿里巴巴", "label": "ORG", "start": 5, "end": 9}, {"entity": "30岁", "label": "AGE", "start": 19, "end": 22}]}
```

#### 数据格式详细说明

```python
# 单条数据示例
{
    "text": "今年cdn产品金额是多少",
    "entities": [
        {
            "entity": "今年",        # 实体原文
            "label": "TIME",        # 实体类型
            "start": 0,             # 开始位置（字符索引）
            "end": 2                # 结束位置（不包含）
        },
        {
            "entity": "cdn",
            "label": "PRODUCT",
            "start": 2,
            "end": 5
        },
        {
            "entity": "金额",
            "label": "FIELD",
            "start": 6,
            "end": 8
        }
    ]
}
```

#### 完整的训练数据文件结构

```
data/ner/
├── train.jsonl          # 训练集（10000+ 条）
├── dev.jsonl            # 验证集（1000+ 条）
├── test.jsonl           # 测试集（1000+ 条）
└── labels.txt            # 标签列表
```

**labels.txt 内容：**
```
O
B-PRODUCT
I-PRODUCT
B-TIME
I-TIME
B-FIELD
I-FIELD
B-ORG
I-ORG
B-PERSON
I-PERSON
```

#### 数据集统计要求

| 数据集 | 最小数量 | 推荐数量 | 说明 |
|--------|----------|----------|------|
| 训练集 | 5,000 条 | 10,000-50,000 条 | 覆盖各种场景 |
| 验证集 | 500 条 | 1,000-5,000 条 | 用于调参 |
| 测试集 | 500 条 | 1,000-5,000 条 | 评估模型 |

#### 数据增强策略

如果数据量不足，可以使用以下增强方法：

```python
def augment_entity_data(data):
    """
    实体数据增强方法

    1. 同义词替换
       - "cdn" → "内容分发网络" / "CDN"
       - "金额" → "费用" / "总金额"

    2. 实体别名扩展
       - 产品名：cdn, ecs, oss, rds, slb
       - 时间：今年 → 2026年，本月 → 1月

    3. 实体位置变换
       - "今年cdn金额" → "cdn今年金额"
       - "上月ecs数量" → "数量上月ecs"

    4. 上下文扩充
       - "cdn产品" → "阿里云CDN加速产品"
       - "金额" → "CDN服务的账单金额"
    """
    # 具体实现...
```

### 2.4 标注工具推荐

| 工具 | 类型 | 推荐度 |
|------|------|--------|
| **Doccano** | 开源、Web 界面 | ⭐⭐⭐⭐⭐ |
| **Label Studio** | 免费、功能强大 | ⭐⭐⭐⭐⭐ |
| **Prodigy** | 商业、高效 | ⭐⭐⭐⭐ |
| **Brat** | 学术、轻量 | ⭐⭐⭐ |

#### Doccano 标注示例

**安装：**
```bash
pip install doccano
doccano init
doccano server
```

**标注流程：**
1. 访问 http://localhost:8000
2. 创建项目，选择 "序列标注"
3. 导入文本数据
4. 标注实体边界和类型
5. 导出为 JSON 格式

## 3. 语句改写模型设计

### 3.1 模型架构

基于 T5 / BART 的 Seq2Seq 模型：

```python
# 伪代码示意
class QuestionRewriteModel(nn.Module):
    """
    基于 Seq2Seq 的语句改写模型

    Architecture:
    1. T5 Encoder - 编码原始问题
    2. T5 Decoder - 生成改写后问题
    3. Fine-tuning - 在改写任务上微调
    """

    def __init__(self, model_name="t5-small"):
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)

    def rewrite(self, question: str, max_length=128):
        """
        改写问题

        Args:
            question: 原始问题
            max_length: 最大生成长度

        Returns:
            改写后的问题
        """
        # 添加前缀提示
        input_text = f"改写问题：{question}"

        # 编码
        inputs = self.tokenizer(input_text, return_tensors="pt")

        # 生成
        outputs = self.model.generate(
            inputs.input_ids,
            max_length=max_length,
            num_beams=4,
            no_repeat_ngram_size=2,
            early_stopping=True
        )

        # 解码
        rewritten = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return rewritten
```

### 3.2 训练数据格式

#### 语句改写训练数据（JSONL 格式）

**文件格式：** `data/rewrite/train.jsonl`

```jsonl
{"input": "今年cdn产品金额是多少", "target": "产品ID为cdn，时间为2026年的出账金额是多少"}
{"input": "上月ecs产品的订单数量", "target": "产品ID为ecs，时间为2025年12月的订单数量是多少"}
{"input": "去年oss产品的收入", "target": "产品ID为oss，时间为2025年的营业收入是多少"}
{"input": "今年cdn和ecs产品的总金额", "target": "产品ID为cdn和产品ID为ecs，时间为2026年的出账金额总和是多少"}
{"input": "最近7天slb产品的流量", "target": "产品ID为slb，时间为2026-01-22至2026-01-29的流量是多少"}
```

#### 数据格式详细说明

```python
# 单条数据示例
{
    "input": "今年cdn产品金额是多少",      # 原始问题
    "target": "产品ID为cdn，时间为2026年的出账金额是多少"  # 改写后问题
}
```

#### 高级训练数据（包含实体标注）

如果想要更好的效果，可以在训练数据中包含实体信息：

```jsonl
{"input": "今年cdn产品金额是多少", "target": "产品ID为cdn，时间为2026年的出账金额是多少", "entities": {"product_id": "cdn", "time": "2026年", "field": "出账金额"}}
{"input": "上月ecs产品的订单数量", "target": "产品ID为ecs，时间为2025年12月的订单数量是多少", "entities": {"product_id": "ecs", "time": "2025年12月", "field": "订单数量"}}
```

#### 数据集统计

| 数据集 | 最小数量 | 推荐数量 | 说明 |
|--------|----------|----------|------|
| 训练集 | 1,000 条 | 5,000-20,000 条 | 覆盖各种改写模式 |
| 验证集 | 200 条 | 500-2,000 条 | 用于调参 |
| 测试集 | 200 条 | 500-2,000 条 | 评估模型 |

### 3.3 数据增强策略

```python
def augment_rewrite_data(data):
    """
    语句改写数据增强

    1. 实体替换
       - 同一实体的不同表达
       - "今年" → "2026年"

    2. 模板扩展
       - 基于模板生成变体
       - "{时间}{产品}{字段}是多少"

    3. 组合扩展
       - 多个实体组合
       - "A和B产品的{字段}"
    """
    # 具体实现...
```

## 4. 完整技术方案

### 4.1 端到端流程

```
┌──────────────────────────────────────────────────────────────┐
│                        用户问题                                │
│              "今年cdn产品金额是多少"                           │
└───────────────────────────────────────┬──────────────────────┘
                                        │
                                        ▼
                        ┌─────────────────────────────┐
                        │    1. 实体识别 NER          │
                        │    (BERT-based Model)      │
                        │    推理时间: ~10ms          │
                        └─────────────────┬───────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │  识别的实体                   │
                            │  {                          │
                            │   product: "cdn",            │
                            │   time: "今年",              │
                            │   field: "金额"              │
                            │  }                          │
                            └─────────────────┬─────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────┐
                          │  2. 规范化引擎               │
                          │  - 时间: "今年" → "2026年"   │
                          │  - 产品: "cdn" → "产品ID为cdn"│
                          │  - 字段: "金额" → "出账金额" │
                          │  推理时间: ~1ms             │
                          └─────────────────┬─────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────┐
                          │  3. 语句改写 Seq2Seq        │
                          │  (T5 / BART Model)         │
                          │  推理时间: ~50ms            │
                          └─────────────────┬─────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────┐
                          │  改写后的问题                 │
                          │ "产品ID为cdn，时间为2026年的  │
                          │  出账金额是多少"             │
                          └─────────────────────────────┘
```

### 4.2 混合方案（推荐）

结合小模型和规则引擎：

```python
class HybridEntityExtractor:
    """
    混合实体抽取器

    策略：
    1. 小模型识别实体（准确率高、速度快）
    2. 规则引擎规范化（零错误）
    3. 少数疑难用例才调用 LLM（兜底）
    """

    def __init__(self):
        self.ner_model = load_ner_model()      # BERT-based
        self.normalizer = RuleNormalizer()    # 规则引擎
        self.llm_client = LLMClient()          # 兜底（<5% 用例）

    def extract(self, text: str) -> Dict:
        # 1. 小模型识别
        entities = self.ner_model.predict(text)

        # 2. 规则规范化
        normalized_entities = self.normalizer.normalize(entities)

        # 3. 置信度检查
        confidence = self.ner_model.get_confidence(text)

        # 4. 低置信度时调用 LLM
        if confidence < 0.8:
            entities = self.llm_client.extract(text)

        return normalized_entities
```

**成本对比：**

| 方案 | 准确率 | 推理速度 | 成本（每1000次） |
|------|--------|----------|-------------------|
| 纯 LLM | 92% | 2000ms | ~$0.10 |
| 纯小模型 | 85% | 60ms | ~$0.0001 |
| **混合方案** | **90%** | **70ms** | **~$0.001** |

### 4.3 部署架构

```python
# 服务接口
class EntityService:
    """实体抽取服务"""

    def __init__(self):
        # 加载小模型（启动时一次性加载）
        self.ner_model = load_model("models/ner_bert.pt")
        self.rewrite_model = load_model("models/rewrite_t5.pt")
        self.normalizer = RuleNormalizer()

    async def extract_and_rewrite(self, question: str) -> Dict:
        """提取实体并改写问题"""

        # 1. 实体识别（小模型，本地推理）
        entities = self.ner_model.extract(question)

        # 2. 实体规范化（规则引擎）
        normalized_entities = self.normalizer.normalize(entities)

        # 3. 语句改写（小模型，本地推理）
        rewritten = self.rewrite_model.rewrite(
            question,
            entities=normalized_entities
        )

        return {
            "original": question,
            "rewritten": rewritten,
            "entities": normalized_entities
        }
```

## 5. 训练数据详细规格

### 5.1 实体识别训练数据

#### 最小数据集（5000 条）

**data/ner/train_minimal.jsonl**
```jsonl
{"text": "今年cdn产品金额是多少", "entities": [{"entity": "今年", "label": "TIME", "start": 0, "end": 2}, {"entity": "cdn", "label": "PRODUCT", "start": 2, "end": 5}, {"entity": "金额", "label": "FIELD", "start": 6, "end": 8}]}
{"text": "上月ecs产品的订单数量", "entities": [{"entity": "上月", "label": "TIME", "start": 0, "end": 2}, {"entity": "ecs", "label": "PRODUCT", "start": 3, "end": 6}, {"entity": "数量", "label": "FIELD", "start": 11, "end": 13}]}
{"text": "去年oss产品的收入", "entities": [{"entity": "去年", "label": "TIME", "start": 0, "end": 2}, {"entity": "oss", "label": "PRODUCT", "start": 2, "end": 5}, {"entity": "收入", "label": "FIELD", "start": 5, "end": 7}]}
{"text": "阿里云CDN产品价格为每GB 0.2元", "entities": [{"entity": "阿里云", "label": "ORG", "start": 0, "end": 3}, {"entity": "CDN", "label": "PRODUCT", "start": 3, "end": 6}, {"entity": "0.2元", "label": "PRICE", "start": 16, "end": 20}]}
{"text": "张三负责cdn产品的技术支持", "entities": [{"entity": "张三", "label": "PERSON", "start": 0, "end": 2}, {"entity": "cdn", "label": "PRODUCT", "start": 7, "end": 10}]}
```

#### 推荐数据集（20000 条）

包含以下场景的分布：
- 简单单实体：30%
- 多实体组合：40%
- 嵌套实体：20%
- 边界情况：10%

### 5.2 语句改写训练数据

#### 最小数据集（1000 条）

**data/rewrite/train_minimal.jsonl**
```jsonl
{"input": "今年cdn产品金额是多少", "target": "产品ID为cdn，时间为2026年的出账金额是多少"}
{"input": "上月ecs产品的订单数量", "target": "产品ID为ecs，时间为2025年12月的订单数量是多少"}
{"input": "去年oss产品的收入", "target": "产品ID为oss，时间为2025年的营业收入是多少"}
{"input": "最近7天slb产品的流量", "target": "产品ID为slb，时间为2026-01-22至2026-01-29的流量是多少"}
{"input": "今年cdn和ecs产品的总金额", "target": "产品ID为cdn和产品ID为ecs，时间为2026年的出账金额总和是多少"}
```

#### 推荐数据集（10000 条）

包含以下模式的分布：
- 时间规范化：20%
- 产品规范化：15%
- 字段明确化：15%
- 多条件组合：30%
- 复杂查询：20%

### 5.3 数据生成脚本

```python
"""
训练数据生成脚本

用于自动生成训练数据，快速构建数据集
"""

import random
import json
from typing import List, Dict

class TrainingDataGenerator:
    """训练数据生成器"""

    # 产品列表
    PRODUCTS = ["cdn", "ecs", "oss", "rds", "slb"]

    # 时间表达
    TIME_EXPRESSIONS = {
        "今年": "2026年",
        "去年": "2025年",
        "上月": "2025年12月",
        "本月": "2026年1月",
        "本季度": "2026年Q1",
        "最近7天": "2026-01-22至2026-01-29",
    }

    # 字段映射
    FIELD_MAPPING = {
        "金额": "出账金额",
        "数量": "订单数量",
        "收入": "营业收入",
        "流量": "流量",
        "用户数": "用户数",
    }

    def generate_ner_data(self, count: int) -> List[Dict]:
        """生成实体识别训练数据"""
        data = []

        templates = [
            "{time}{product}产品{field}",
            "{time}{product}和{product2}的{field}",
            "{product}产品的{field}是{value}",
            "{org}的{person}负责{product}产品",
        ]

        for _ in range(count):
            # 随机选择模板
            template = random.choice(templates)

            # 随机填充
            text = template.format(
                time=random.choice(list(self.TIME_EXPRESSIONS.keys())),
                product=random.choice(self.PRODUCTS),
                product2=random.choice(self.PRODUCTS),
                field=random.choice(list(self.FIELD_MAPPING.keys())),
                value=random.choice(["100", "200", "1000"]),
                org=random.choice(["阿里巴巴", "腾讯", "华为", "百度"]),
                person=random.choice(["张三", "李四", "王五"])
            )

            # 自动标注实体
            entities = self._auto_tag_entities(text)

            data.append({
                "text": text,
                "entities": entities
            })

        return data

    def generate_rewrite_data(self, count: int) -> List[Dict]:
        """生成语句改写训练数据"""
        data = []

        for _ in range(count):
            # 随机组合
            time_expr = random.choice(list(self.TIME_EXPRESSIONS.keys()))
            product = random.choice(self.PRODUCTS)
            field = random.choice(list(self.FIELD_MAPPING.keys()))

            # 生成原始问题
            input_text = f"{time_expr}{product}产品{field}是多少"

            # 生成改写后问题
            time_normalized = self.TIME_EXPRESSIONS[time_expr]
            field_normalized = self.FIELD_MAPPING[field]

            target_text = f"产品ID为{product}，时间为{time_normalized}的{field_normalized}是多少"

            data.append({
                "input": input_text,
                "target": target_text
            })

        return data

    def save_jsonl(self, data: List[Dict], filepath: str):
        """保存为 JSONL 格式"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

# 使用示例
if __name__ == "__main__":
    generator = TrainingDataGenerator()

    # 生成实体识别数据
    ner_data = generator.generate_ner_data(10000)
    generator.save_jsonl(ner_data, "data/ner/train.jsonl")

    # 生成语句改写数据
    rewrite_data = generator.generate_rewrite_data(5000)
    generator.save_jsonl(rewrite_data, "data/rewrite/train.jsonl")

    print("训练数据生成完成！")
```

## 6. 模型训练方案

### 6.1 环境要求

```bash
# 安装依赖
pip install torch>=2.0.0
pip install transformers>=4.30.0
pip install datasets>=2.12.0
pip install accelerate>=0.20.0
pip install seqeval>=1.2.2
pip install tensorboard>=2.13.0
```

### 6.2 实体识别模型训练

```bash
# 训练脚本
python scripts/train_ner.py \
    --model_name hfl/chinese-bert-wwm-ext \
    --data_dir data/ner \
    --output_dir models/ner_bert \
    --num_train_epochs 10 \
    --learning_rate 2e-5 \
    --batch_size 16 \
    --max_seq_length 128 \
    --eval_steps 500
```

### 6.3 语句改写模型训练

```bash
# 训练脚本
python scripts/train_rewrite.py \
    --model_name uxin/t5-chinese-small \
    --data_dir data/rewrite \
    --output_dir models/rewrite_t5 \
    --num_train_epochs 5 \
    --learning_rate 3e-4 \
    --batch_size 8 \
    --max_source_length 128 \
    --max_target_length 128 \
    --eval_steps 200
```

### 6.4 模型评估

```python
# 评估脚本
def evaluate_model(model, test_data):
    """评估模型性能"""

    metrics = {
        "precision": [],
        "recall": [],
        "f1": []
    }

    for example in test_data:
        # 预测
        prediction = model.predict(example["text"])

        # 计算指标
        precision, recall, f1 = calculate_metrics(
            prediction,
            example["entities"]
        )

        metrics["precision"].append(precision)
        metrics["recall"].append(recall)
        metrics["f1"].append(f1)

    # 平均指标
    results = {
        key: sum(values) / len(values)
        for key, values in metrics.items()
    }

    return results
```

## 7. 部署方案

### 7.1 FastAPI 服务部署

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ExtractRequest(BaseModel):
    question: str

class ExtractResponse(BaseModel):
    original: str
    rewritten: str
    entities: Dict[str, str]
    confidence: float

@app.post("/extract", response_model=ExtractResponse)
async def extract_entities(request: ExtractRequest):
    """
    实体抽取和语句改写接口

    性能：本地推理 ~60ms，无需 API 调用
    """
    # 1. 实体识别
    entities = ner_model.extract(request.question)

    # 2. 实体规范化
    normalized = normalizer.normalize(entities)

    # 3. 语句改写
    rewritten = rewrite_model.rewrite(
        request.question,
        entities=normalized
    )

    # 4. 置信度
    confidence = ner_model.get_confidence(request.question)

    return ExtractResponse(
        original=request.question,
        rewritten=rewritten,
        entities=normalized,
        confidence=confidence
    )

# 启动服务
# uvicorn app:app --host 0.0.0.0 --port 8000
```

### 7.2 性能优化

```python
# 批处理支持
@app.post("/extract_batch")
async def extract_batch(requests: List[ExtractRequest]):
    """批量处理，提高吞吐量"""

    results = []

    # 批量推理（GPU 加速）
    questions = [r.question for r in requests]
    entities_batch = ner_model.extract_batch(questions)

    # 批量改写
    rewritten_batch = rewrite_model.rewrite_batch(questions)

    return results
```

### 7.3 监控和日志

```python
from prometheus_client import Counter, Histogram

# 指标
REQUEST_COUNT = Counter('request_count', 'Number of requests')
LATENCY = Histogram('latency_seconds', 'Request latency')
ACCURACY = Histogram('accuracy', 'Model accuracy')

@app.post("/extract")
async def extract(request: ExtractRequest):
    start_time = time.time()

    # 处理逻辑...

    # 记录指标
    REQUEST_COUNT.inc()
    LATENCY.observe(time.time() - start_time)
    ACCURACY.observe(result.confidence)

    return result
```

## 8. 成本对比分析

### 8.1 LLM 方案 vs 小模型方案

| 维度 | LLM 方案 | 小模型方案 | 混合方案 |
|------|----------|------------|----------|
| **初始成本** | API 配置 | 训练成本 | 训练成本 |
| **单次推理** | ~$0.0001 | ~$0.0000001 | ~$0.000001 |
| **100万次** | ~$100 | ~$0.1 | ~$1 |
| **准确率** | 92% | 85% | 90% |
| **延迟** | 2000ms | 60ms | 70ms |
| **数据隐私** | 需要外部API | 完全本地 | 完全本地 |

### 8.2 投资回报分析

#### 初期投资（3个月）

| 项目 | 成本 | 说明 |
|------|------|------|
| 数据标注 | $2,000-5,000 | 人工标注 10,000 条数据 |
| 模型训练 | $500-1,000 | GPU 时间成本 |
| 基础设施 | $200-500 | 服务器成本 |
| 开发时间 | 80-120 小时 | 工程师时间 |
| **总计** | **$3,000-7,000** | 一次性投资 |

#### 运营成本对比（月）

| 使用量 | LLM 方案 | 小模型方案 | 节省 |
|--------|----------|------------|------|
| 10万次 | $10 | $0.01 | 99.9% |
| 100万次 | $100 | $0.1 | 99.9% |
| 1000万次 | $1,000 | $1 | 99.9% |

**ROI 分析：**
- 月使用量 100 万次
- LLM 成本：$100/月
- 小模型成本：$0.1/月
- **节省：$99.9/月**
- **回本周期：** < 1 个月

## 9. 实施路线图

### 阶段 1：数据准备（1-2 周）
- [ ] 设计数据标注规范
- [ ] 标注 1000 条初始数据
- [ ] 搭建标注环境（Doccano）
- [ ] 标注 5000 条 NER 数据
- [ ] 标注 2000 条改写数据

### 阶段 2：模型训练（1-2 周）
- [ ] 准备训练环境
- [ ] 训练 NER 模型
- [ ] 训练改写模型
- [ ] 模型调优和验证

### 阶段 3：服务开发（1 周）
- [ ] 实现 FastAPI 服务
- [ ] 集成模型推理
- [ ] 性能优化
- [ ] 监控和日志

### 阶段 4：测试上线（1 周）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 灰度发布

**总时间：** 4-6 周

## 10. 数据集模板

### 10.1 完整训练数据模板

**文件：data/templates/training_data_template.jsonl**

```jsonl
{"text": "今年cdn产品金额是多少", "entities": [{"entity": "今年", "label": "TIME", "start": 0, "end": 2}, {"entity": "cdn", "label": "PRODUCT", "start": 2, "end": 5}, {"entity": "金额", "label": "FIELD", "start": 6, "end": 8}]}
{"text": "上月ecs产品的订单数量", "entities": [{"entity": "上月", "label": "TIME", "start": 0, "end": 2}, {"entity": "ecs", "label": "PRODUCT", "start": 3, "end": 6}, {"entity": "数量", "label": "FIELD", "start": 11, "end": 13}]}
{"text": "去年oss产品的收入", "entities": [{"entity": "去年", "label": "TIME", "start": 0, "end": 2}, {"entity": "oss", "label": "PRODUCT", "start": 2, "end": 5}, {"entity": "收入", "label": "FIELD", "start": 5, "end": 7}]}
{"text": "最近7天slb产品的流量", "entities": [{"entity": "最近7天", "label": "TIME", "start": 0, "end": 4}, {"entity": "slb", "label": "PRODUCT", "start": 4, "end": 7}, {"entity": "流量", "label": "FIELD", "start": 7, "end": 9}]}
{"text": "阿里云CDN产品价格为每GB 0.2元", "entities": [{"entity": "阿里云", "label": "ORG", "start": 0, "end": 3}, {"entity": "CDN", "label": "PRODUCT", "start": 3, "end": 6}, {"entity": "0.2元", "label": "PRICE", "start": 16, "end": 20}]}
{"text": "张三负责cdn产品的技术支持工作", "entities": [{"entity": "张三", "label": "PERSON", "start": 0, "end": 2}, {"entity": "cdn", "label": "PRODUCT", "start": 7, "end": 10}]}
{"text": "腾讯云的北京数据中心部署了新节点", "entities": [{"entity": "腾讯云", "label": "ORG", "start": 0, "end": 3}, {"entity": "北京", "label": "LOCATION", "start": 5, "end": 7}, {"entity": "数据中心", "label": "FACILITY", "start": 7, "end": 11}]}
{"text": "华为在2024年推出了新款手机Mate60", "entities": [{"entity": "华为", "label": "ORG", "start": 0, "end": 2}, {"entity": "2024年", "label": "TIME", "start": 4, "end": 9}, {"entity": "Mate60", "label": "PRODUCT", "start": 14, "end": 19}]}
{"text": "李四使用iPhone 15 Pro打视频电话", "entities": [{"entity": "李四", "label": "PERSON", "start": 0, "end": 2}, {"entity": "iPhone 15 Pro", "label": "PRODUCT", "start": 4, "end": 15}]}
```

### 10.2 标签文件模板

**文件：data/ner/labels.txt**

```
O
B-PRODUCT
I-PRODUCT
B-TIME
I-TIME
B-FIELD
I-FIELD
B-ORG
I-ORG
B-PERSON
I-PERSON
B-LOCATION
I-LOCATION
B-PRICE
I-PRICE
```

### 10.3 配置文件模板

**文件：configs/model_config.yaml**

```yaml
# NER 模型配置
ner_model:
  name: "hfl/chinese-bert-wwm-ext"
  max_seq_length: 128
  num_labels: 13
  dropout: 0.1

training:
  num_epochs: 10
  batch_size: 16
  learning_rate: 2e-5
  warmup_steps: 500
  weight_decay: 0.01

evaluation:
  eval_steps: 500
  save_steps: 1000
  logging_steps: 100

# Seq2Seq 模型配置
seq2seq_model:
  name: "uer/t5-small"
  max_source_length: 128
  max_target_length: 128

training:
  num_epochs: 5
  batch_size: 8
  learning_rate: 3e-4
  warmup_ratio: 0.1

generation:
  num_beams: 4
  no_repeat_ngram_size: 2
  early_stopping: true
  length_penalty: 0.6
```

## 11. 总结与建议

### 11.1 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **纯 LLM** | 准确率高、无需训练 | 成本高、速度慢 | ⭐⭐ |
| **纯小模型** | 成本低、速度快 | 准确率略低 | ⭐⭐⭐⭐ |
| **混合方案** | 平衡成本和准确率 | 复杂度中等 | ⭐⭐⭐⭐⭐ |

### 11.2 推荐方案

**采用混合方案：**
1. **小模型为主**：处理 95% 的常规用例
2. **规则引擎辅助**：规范化实体（零错误）
3. **LLM 兜底**：处理 5% 的疑难用例

**预期效果：**
- 准确率：90%（vs LLM 的 92%）
- 成本降低：99%（vs 纯 LLM）
- 速度提升：28 倍（70ms vs 2000ms）

### 11.3 快速开始

**最小可行方案（MVP）：**
1. 收集 1000 条标注数据（1 周）
2. 使用开源预训练模型微调（1 周）
3. 部署 FastAPI 服务（3 天）
4. 总时间：**3 周**

**完整方案：**
1. 收集 10000 条高质量数据（4 周）
2. 训练定制模型（2 周）
3. 完整的监控和优化（2 周）
4. 总时间：**8 周**
