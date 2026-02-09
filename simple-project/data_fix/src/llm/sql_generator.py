"""
LLM-based SQL Generator for cal_acct_record data repair

This module uses langchain with multiple LLM providers to generate repair SQL statements
for invalid data in the Change Record table.

Supported LLM providers:
- Zhipu AI (智谱AI): GLM-4 models
- Qwen (千问): Via OpenAI-compatible API
"""
import os
import re
from typing import Dict, List, Any, Optional
# from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from langchain_community.chat_models.zhipuai import ChatZhipuAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class SQLGeneratorAgent:
    """
    LLM-based SQL generator using langchain with multiple LLM providers.

    This class uses langchain's framework with supported LLM providers
    to generate SQL fix statements based on current record data and violation information.

    Supported providers:
    - Zhipu AI (智谱AI): GLM-4 models
    - Qwen (千问): Via DashScope OpenAI-compatible API
    """

    # Table structure context for the LLM
    TABLE_SCHEMA = """
表: cal_acct_record
列:
- ID: 主键 (bigint)
- PROD_INST_ID: 产品实例ID (varchar(50))
- ACCT_ITEM_TYPE_ID: 账目项类型ID (varchar(50))
- NAME: 账目名称 (varchar(255))
- START_DATE: 记录开始日期 (datetime)
- END_DATE: 记录结束日期，当前活跃记录为NULL (datetime)
- START_FLAG: 首条记录标志 (tinyint, 1或0)
- LATEST_FLAG: 最新/活跃记录标志 (tinyint, 1或0)

验证规则:
1. 连续性: 每行的END_DATE必须等于下一行的START_DATE
2. 唯一性: 每个(ACCT_ITEM_TYPE_ID, PROD_INST_ID)组合应只有一行START_FLAG = 1
3. 一致性: END_DATE为NULL或最大END_DATE的行必须设置LATEST_FLAG = 1
"""

    # Business data query template
    BUSINESS_DATA_SCHEMA = """
业务数据查询 (cal_acct_record):
SELECT a.ACCT_ITEM_TYPE_ID, a.ID, a.PROD_INST_ID, b.NAME, a.START_DATE,
       a.END_DATE, a.START_FLAG, a.LATEST_FLAG, a.LOOP_MONEY,
       a.CAL_ACCT_RECORD_ID, a.ACCT_ID, a.CREATE_DATE, a.UPDATE_DATE
FROM cal_acct_record a
LEFT JOIN acct_item_type b ON a.ACCT_ITEM_TYPE_ID = b.ACCT_ITEM_TYPE_ID
WHERE a.PROD_INST_ID = '<PROD_INST_ID>'
ORDER BY a.ACCT_ITEM_TYPE_ID DESC, a.START_DATE ASC
"""

    # Log data query template
    LOG_DATA_SCHEMA = """
日志数据查询 (prod_inst_log):
SELECT PROD_INST_ID, BEGIN_DATE, INPUT_DATE, ATTR_ID, ATTR_NAME,
       MOD_BEFORE, MOD_AFTER, MOD_BEFORE_VAL, MOD_AFTER_VAL, MOD_DATE, MOD_REASON
FROM prod_inst_log
WHERE prod_inst_id = '<PROD_INST_ID>'
ORDER BY AUD_DATE DESC
"""

    # Few-shot examples based on check_record_results.xlsx
    FEW_SHOT_EXAMPLES = """## 示例 1: 根据变更日志的BEGIN_DATE修复START_DATE和START_FLAG

### 当前异常数据 (cal_acct_record):
| ACCT_ITEM_TYPE_ID | ID             | PROD_INST_ID | NAME              | START_DATE          | END_DATE            | START_FLAG | LATEST_FLAG |
| ----------------- | ------------- | ------------ | ----------------- | ------------------- | ------------------- | ---------- | ----------- |
| 11907105          | 10000094580884 | 237620465    | 带宽型国际长途费用 | 2016-12-22 00:00:00 | 2022-03-17 00:00:00 | 0          | 0           |
| 11907105          | 10000094580891 | 237620465    | 带宽型国际长途费用 | 2016-12-22 00:00:00 | NULL               | 1          | 1           |

### 变更日志 (prod_inst_log):
| BEGIN_DATE          | ATTR_ID | ATTR_NAME      | MOD_BEFORE_VAL | MOD_AFTER_VAL | MOD_REASON |
| ------------------- | ------- | -------------- | -------------- | ------------- | ---------- |
| 2022-03-17 00:00:00 | GJYZF   | 国际长途月租费  | 0              | 535100        | 国际长途月租费由0变更535100,生效日期:2022-03-17 |

### 推理分析:
1. 观察数据：
   - 记录1(ID=10000094580884): START_DATE='2016-12-22', END_DATE='2022-03-17', START_FLAG='0'
   - 记录2(ID=10000094580891): START_DATE='2016-12-22', END_DATE=NULL, START_FLAG='1'
   - 异常：两条记录的START_DATE相同(2016-12-22)，违反唯一性；且START_DATE='2016-12-22'的记录不应有START_FLAG='1'（因为它不是最早的）

2. 查看变更日志：
   - BEGIN_DATE='2022-03-17' 表示这次变更的生效日期是 2022-03-17
   - MOD_REASON="生效日期:2022-03-17" 明确指出新记录应该从 2022-03-17 开始

3. 推断：
   - 记录1(10000094580884)的END_DATE='2022-03-17'，这是原始记录，应该设置START_FLAG='1'
   - 记录2(10000094580891)应该是从2022-03-17开始的新记录，但START_DATE错误地设置为了'2016-12-22'
   - 需要修正：记录2的START_DATE应该改为'2022-03-17'，START_FLAG改为'0'

4. 修复方案：
   - 记录1：设置START_FLAG='1'（它是2016-12-22开始的原始记录）
   - 记录2：设置START_DATE='2022-03-17'（变更生效日期），START_FLAG='0'

### 修复SQL:
```sql
UPDATE cal_acct_record SET START_FLAG = '1' WHERE PROD_INST_ID = '237620465' AND ID = 10000094580884 AND (START_FLAG = '0');
UPDATE cal_acct_record SET START_DATE = '2022-03-17 00:00:00', START_FLAG = '0' WHERE PROD_INST_ID = '237620465' AND ID = 10000094580891 AND (START_DATE = '2016-12-22 00:00:00');
```

---

## 示例 2: 连续性违规 - 根据变更日志BEGIN_DATE修复END_DATE

### 当前异常数据 (cal_acct_record):
| ACCT_ITEM_TYPE_ID | ID         | PROD_INST_ID | NAME            | START_DATE          | END_DATE            | START_FLAG | LATEST_FLAG |
| ----------------- | ---------- | ------------ | --------------- | ------------------- | ------------------- | ---------- | ----------- |
| 11907111          | 6050187507 | 114453109    | 带宽型Z端代维费 | 2016-12-01 00:00:00 | 2022-04-13 00:00:00 | 1          | 0           |
| 11907111          | 6050187529 | 114453109    | 带宽型Z端代维费 | 2021-04-01 00:00:00 | 2022-04-13 00:00:00 | 0          | 1           |

### 变更日志 (prod_inst_log):
| BEGIN_DATE          | ATTR_ID | ATTR_NAME | MOD_REASON |
| ------------------- | ------- | --------- | ---------- |
| 2021-04-01 00:00:00 | -       | -         | 产品变更，生效日期:2021-04-01 |

### 推理分析:
1. 观察数据：记录1的END_DATE='2022-04-13'，记录2的START_DATE='2021-04-01'
2. 查看变更日志：BEGIN_DATE='2021-04-01'，MOD_REASON显示"生效日期:2021-04-01"
3. 推断：2021-04-01发生了产品变更，记录2应该是从2021-04-01开始的新记录。记录1的END_DATE应该更新为2021-04-01（而不是2022-04-13）
4. 修复方案：将记录1的END_DATE更新为'2021-04-01 00:00:00'

### 修复SQL:
```sql
UPDATE cal_acct_record SET END_DATE = '2021-04-01 00:00:00' WHERE PROD_INST_ID = '114453109' AND ID = 6050187507 AND (END_DATE = '2022-04-13 00:00:00');
```

---

## 示例 3: 多段连续性违规 - 多次变更根据BEGIN_DATE修复

### 当前异常数据 (cal_acct_record):
| ACCT_ITEM_TYPE_ID | ID         | PROD_INST_ID | NAME                  | START_DATE          | END_DATE            | START_FLAG | LATEST_FLAG |
| ----------------- | ---------- | ------------ | --------------------- | ------------------- | ------------------- | ---------- | ----------- |
| 11907104          | 6050187513 | 114453109    | 带宽型国内长途Z端费用 | 2016-12-01 00:00:00 | 2022-04-13 00:00:00 | 1          | 0           |
| 11907104          | 6050187519 | 114453109    | 带宽型国内长途Z端费用 | 2019-11-28 00:00:00 | 2022-04-13 00:00:00 | 0          | 0           |
| 11907104          | 6050187521 | 114453109    | 带宽型国内长途Z端费用 | 2020-04-01 00:00:00 | 2022-04-13 00:00:00 | 0          | 0           |
| 11907104          | 6050187526 | 114453109    | 带宽型国内长途Z端费用 | 2022-04-13 00:00:00 | 2022-04-13 00:00:00 | 0          | 1           |

### 变更日志 (prod_inst_log):
| BEGIN_DATE          | ATTR_ID | ATTR_NAME | MOD_REASON |
| ------------------- | ------- | --------- | ---------- |
| 2019-11-28 00:00:00 | -       | -         | 产品变更，生效日期:2019-11-28 |
| 2020-04-01 00:00:00 | -       | -         | 产品变更，生效日期:2020-04-01 |
| 2022-04-13 00:00:00 | -       | -         | 产品变更，生效日期:2022-04-13 |

### 推理分析:
1. 观察数据：所有记录的END_DATE都是'2022-04-13'，但START_DATE分别是2016-12-01、2019-11-28、2020-04-01、2022-04-13
2. 查看变更日志：有3次变更，BEGIN_DATE分别是2019-11-28、2020-04-01、2022-04-13，每个都标注了"生效日期"
3. 推断：
   - 原始记录：2016-12-01开始(ID=6050187513)
   - 第一次变更：2019-11-28生效，应新增记录，原记录END_DATE应改为2019-11-28
   - 第二次变更：2020-04-01生效，应新增记录，上一条记录END_DATE应改为2020-04-01
   - 第三次变更：2022-04-13生效，应新增记录，上一条记录END_DATE应改为2022-04-13
4. 修复方案：按时间顺序，每个记录的END_DATE更新为下一个变更的BEGIN_DATE

### 修复SQL:
```sql
UPDATE cal_acct_record SET END_DATE = '2019-11-28 00:00:00' WHERE PROD_INST_ID = '114453109' AND ID = 6050187513 AND (END_DATE = '2022-04-13 00:00:00');
UPDATE cal_acct_record SET END_DATE = '2020-04-01 00:00:00' WHERE PROD_INST_ID = '114453109' AND ID = 6050187519 AND (END_DATE = '2022-04-13 00:00:00');
```

---

## 示例 4: 避免生成无意义的SQL

### 当前异常数据 (cal_acct_record):
| ACCT_ITEM_TYPE_ID | ID         | PROD_INST_ID | NAME                  | START_DATE          | END_DATE            | START_FLAG | LATEST_FLAG |
| ----------------- | ---------- | ------------ | --------------------- | ------------------- | ------------------- | ---------- | ----------- |
| 11907103          | 6917553987 | 301757698    | 带宽型国内长途A端费用 | 2019-08-01 00:00:00 | 2019-09-01 00:00:00 | 0          | 0           |
| 11907103          | 6917553989 | 301757698    | 带宽型国内长途A端费用 | 2019-09-01 00:00:00 | 2022-05-01 00:00:00 | 0          | 0           |

### 变更日志 (prod_inst_log):
| BEGIN_DATE          | ATTR_ID | ATTR_NAME | MOD_REASON |
| ------------------- | ------- | --------- | ---------- |
| 2019-09-01 00:00:00 | -       | -         | 产品变更，生效日期:2019-09-01 |

### 推理分析:
1. 观察数据：
   - 记录1: START_DATE='2019-08-01', END_DATE='2019-09-01'
   - 记录2: START_DATE='2019-09-01', END_DATE='2022-05-01'
   - 连续性检查：记录1的END_DATE('2019-09-01') = 记录2的START_DATE('2019-09-01') ✓ 正确

2. 查看变更日志：2019-09-01有产品变更，与记录2的START_DATE一致 ✓

3. 推断：
   - 记录2是从2019-09-01开始的新记录
   - 记录1的END_DATE='2019-09-01'已经正确（等于记录2的START_DATE）
   - 记录1和记录2的数据都是正确的，不需要修复

4. 修复方案：无需修复（数据已经正确）

### 修复SQL:
```sql
-- 无需修复，数据已经正确
-- 不生成任何SQL语句
```

### 注意：
如果错误地生成了以下SQL，那是无意义的：
```sql
-- ❌ 错误：这个SQL将START_DATE从'2019-08-01'更新为'2019-08-01'，没有任何变化
UPDATE cal_acct_record SET START_DATE = '2019-08-01 00:00:00' WHERE PROD_INST_ID = '301757698' AND ID = 6917553987 AND (START_DATE = '2019-08-01 00:00:00');

-- ❌ 错误：这个SQL将END_DATE从'2019-09-01'更新为'2019-09-01'，没有任何变化
UPDATE cal_acct_record SET END_DATE = '2019-09-01 00:00:00' WHERE PROD_INST_ID = '301757698' AND ID = 6917553987 AND (END_DATE = '2019-09-01 00:00:00');
```

---

## 推理规则总结:

### 核心逻辑：变更日志的BEGIN_DATE = 新记录的START_DATE = 上一条记录的END_DATE

1. **变更日志BEGIN_DATE的含义**:
   - BEGIN_DATE 表示变更的"生效日期"
   - 这个生效日期应该是新记录的START_DATE
   - 前一条记录的END_DATE应该更新为这个生效日期

2. **START_DATE错误时的修复**:
   - 如果某条记录的START_DATE与变更日志的BEGIN_DATE不匹配
   - 需要将该记录的START_DATE更新为变更日志的BEGIN_DATE
   - 同时调整START_FLAG：最早的记录START_FLAG=1，其他为0

3. **END_DATE错误时的修复**:
   - 如果前一条记录的END_DATE不等于下一记录的START_DATE
   - 需要将前一条记录的END_DATE更新为下一记录的START_DATE

4. **START_FLAG唯一性**:
   - 按START_DATE排序，最早（最小）的记录应设置START_FLAG='1'
   - 其他记录的START_FLAG应设置为'0'

5. **LATEST_FLAG一致性**:
   - END_DATE为NULL的记录必须设置LATEST_FLAG='1'
   - 如果没有NULL，则END_DATE最大的记录设置LATEST_FLAG='1'

6. **重要：避免生成无意义的SQL**:
   - 如果SET的值等于WHERE条件中的值，则这个UPDATE语句没有任何作用，不需要生成
   - 只生成真正会改变数据的SQL语句
   - 例如：`UPDATE SET START_DATE = '2019-08-01' WHERE (START_DATE = '2019-08-01')` 是无意义的，不要生成
"""

    def __init__(self, api_key: Optional[str] = None, model: str = "glm-4-flash",
                 debug: bool = False, provider: str = "auto"):
        """
        初始化 SQL 生成器代理。

        Args:
            api_key: API密钥。如果为None，则从环境变量读取（ZHIPUAI_API_KEY或OPENAI_API_KEY）
            model: 使用的模型 (默认: glm-4-flash，支持: glm-4-plus, qwen-plus, qwen-turbo 等)
            debug: 是否开启调试模式（打印发送给LLM的提示词）
            provider: LLM提供商 ("auto", "zhipu", "qwen")，auto表示根据模型名称自动检测
        """
        self.debug = debug
        self.model = model
        self.provider = provider

        # 自动检测提供商
        if provider == "auto":
            if model.startswith("qwen") or model.startswith("qw-"):
                provider = "qwen"
            else:
                provider = "zhipu"

        # Disable proxy to avoid SOCKS proxy errors
        old_env = {}
        proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                      'all_proxy', 'ALL_PROXY', 'socks_proxy', 'SOCKS_PROXY']
        for var in proxy_vars:
            if var in os.environ:
                old_env[var] = os.environ[var]
                del os.environ[var]

        try:
            # 使用千问模型 (通过 OpenAI 兼容 API)
            self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
            if not self.api_key:
                raise ValueError(
                    "千问 API密钥未提供。请设置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY 环境变量。"
                )
            api_base = os.getenv('OPENAI_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')

            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=api_base,
                model=model,
                temperature=0.1,
            )
        finally:
            # Restore original environment variables
            for var, val in old_env.items():
                os.environ[var] = val

        # Create tools for the agent
        self.tools = self._create_tools()

        # Store current data context
        self.current_data = []
        self.violation_info = ""
        self.last_prompt = None  # 存储最后一次发送的提示词用于调试

    def _create_tools(self) -> List:
        """创建 agent 可用的工具"""

        @tool
        def analyze_continuity(data: str) -> str:
            """分析连续性违规（END_DATE与下一行START_DATE不匹配）并生成修复SQL。输入: 数据列表"""
            return self._analyze_continuity(data)

        @tool
        def analyze_start_flag(data: str) -> str:
            """分析START_FLAG唯一性违规（应只有一行START_FLAG=1）并生成修复SQL。输入: 数据列表"""
            return self._analyze_start_flag(data)

        @tool
        def analyze_latest_flag(data: str) -> str:
            """分析LATEST_FLAG一致性违规（最新记录应设置LATEST_FLAG=1）并生成修复SQL。输入: 数据列表"""
            return self._analyze_latest_flag(data)

        @tool
        def generate_sql(analysis: str) -> str:
            """根据分析结果生成最终的修复SQL语句。输入: 分析结果"""
            return self._format_final_sql(analysis)

        return [analyze_continuity, analyze_start_flag, analyze_latest_flag, generate_sql]

    def generate_fix_sql(self, current_data: List[Dict[str, Any]],
                        violation_info: str,
                        log_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        使用 langchain agent 生成修复 SQL。

        Args:
            current_data: 表示当前记录数据的字典列表
            violation_info: 违规描述
            log_data: 日志数据列表（可选）

        Returns:
            包含 'sql' 和 'explanation' 键的字典
        """
        try:
            # Store context for tools
            self.current_data = current_data
            self.violation_info = violation_info
            self.current_log_data = log_data

            # Format current data for the prompt
            data_str = self._format_data_for_prompt(current_data)
            log_str = self._format_log_data_for_prompt(log_data) if log_data else "无日志数据"

            # Create the prompt template
            prompt_template = PromptTemplate(
                input_variables=["data", "log_data", "few_shot_examples",
                                "table_schema", "business_data_schema", "log_data_schema"],
                template="""你是一个专业的SQL专家，专门处理MySQL数据库中 cal_acct_record 表的数据修复。

# 表结构
{table_schema}

# 业务数据查询模板
{business_data_schema}

# 日志数据查询模板
{log_data_schema}

# Few-shot 示例
{few_shot_examples}

---

# 当前实例数据

## 当前异常数据 (cal_acct_record):
{data}

## 变更日志 (prod_inst_log):
{log_data}

---

请参考上面的 Few-shot 示例，按照以下步骤进行分析并生成修复 SQL。

### 推理分析步骤（请按照此格式输出）:

### 推理分析:
1. 观察数据：[描述数据中的异常情况，如日期不连续、标志重复等]
2. 查看变更日志：[列出关键的变更记录，如BEGIN_DATE、MOD_REASON等]
3. 推断：[根据变更日志推断应该如何修复数据]
4. 修复方案：[具体说明需要更新哪些字段的什么值]

### 修复SQL:
```sql
-- 在这里输出修复SQL语句
UPDATE cal_acct_record SET ...
```

### 重要注意事项:
- 始终使用 PROD_INST_ID 和 ID 作为 WHERE 条件以确保安全
- 在 WHERE 子句中添加当前值的检查条件：(END_DATE = '当前值') 或 (START_FLAG = 当前值)
- **避免生成无意义的SQL**：如果SET的值等于WHERE条件中的值，不要生成该SQL（因为它不会改变任何数据）
- 参考变更日志的日期信息进行修复

### 无意义SQL示例（不要生成）:
-- 无意义的sql不要返回 即更新前后字段值是一样的

```sql
-- ❌ 错误：SET值等于WHERE条件值，无意义
UPDATE cal_acct_record SET START_DATE = '2019-08-01' WHERE prod_inst_id = 'xxx' AND (START_DATE = '2019-08-01');

-- ✅ 正确：SET值不等于WHERE条件值，有意义
UPDATE cal_acct_record SET START_DATE = '2019-09-01' WHERE prod_inst_id = 'xxx' AND (START_DATE = '2019-08-01');
```

请开始分析并生成修复SQL:"""
            )

            # Create LCEL chain
            chain = prompt_template | self.llm | StrOutputParser()

            # Prepare the input for the chain
            chain_input = {
                "table_schema": self.TABLE_SCHEMA,
                "business_data_schema": self.BUSINESS_DATA_SCHEMA,
                "log_data_schema": self.LOG_DATA_SCHEMA,
                "few_shot_examples": self.FEW_SHOT_EXAMPLES,
                "data": data_str,
                "log_data": log_str
            }

            # Debug: 打印发送给LLM的完整提示词
            if self.debug:
                print("=" * 80)
                print("发送给LLM的提示词:")
                print("=" * 80)
                full_prompt = prompt_template.format(**chain_input)
                print(full_prompt)
                print("=" * 80)
                print(f"业务数据行数: {len(current_data)}")
                print(f"日志数据行数: {len(log_data) if log_data else 0}")
                print("=" * 80)

            # Store the prompt for debugging
            self.last_prompt = prompt_template.format(**chain_input)

            # Run the chain using invoke (LCEL syntax)
            result = chain.invoke(chain_input)

            # Parse the response
            return self._parse_response(result)

        except Exception as e:
            # Fallback to direct generation
            return self._generate_fallback(current_data, violation_info, str(e), log_data)

    def _generate_fallback(self, current_data: List[Dict[str, Any]],
                          violation_info: str, error: str,
                          log_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """降级方案：直接生成SQL"""
        try:
            data_str = self._format_data_for_prompt(current_data)
            log_str = self._format_log_data_for_prompt(log_data) if log_data else "无日志数据"

            prompt = f"""请根据以下信息生成修复SQL语句：

{self.TABLE_SCHEMA}

{self.FEW_SHOT_EXAMPLES}

当前异常数据:
{data_str}

变更日志:
{log_str}

请参考上面的示例，按照以下步骤进行分析并生成修复 SQL。

### 推理分析步骤（请按照此格式输出）:

### 推理分析:
1. 观察数据：[描述数据中的异常情况]
2. 查看变更日志：[列出关键的变更记录]
3. 推断：[根据变更日志推断应该如何修复]
4. 修复方案：[具体说明需要更新的内容]

### 修复SQL:
```sql
-- 在这里输出修复SQL语句
UPDATE cal_acct_record SET ...
```

要求:
1. 生成有效的MySQL UPDATE语句
2. 使用ID和PROD_INST_ID作为WHERE条件以确保安全
3. 在 WHERE 子句中添加当前值的检查条件
4. 如果需要多个语句，用换行符分隔

请开始分析并生成修复SQL。"""

            prompt_template = ChatPromptTemplate.from_template("{input}")
            chain = prompt_template | self.llm | StrOutputParser()
            print(prompt_template.format_prompt(input=prompt).to_string())
            result = chain.invoke({"input": prompt})

            return self._parse_response(result)

        except Exception as e:
            print(e)
            return {
                "sql": f"-- 生成SQL时出错: {error}",
                "explanation": f"生成SQL失败: {str(e)}"
            }

    def _analyze_continuity(self, data: str) -> str:
        """分析连续性违规"""
        violations = []
        for i in range(len(self.current_data) - 1):
            current = self.current_data[i]
            next_row = self.current_data[i + 1]

            if current.get('END_DATE') and next_row.get('START_DATE'):
                if current['END_DATE'] != next_row['START_DATE']:
                    violations.append({
                        'index': i,
                        'id': current['ID'],
                        'current_end': current['END_DATE'],
                        'next_start': next_row['START_DATE']
                    })

        if violations:
            sql_list = []
            for v in violations:
                sql_list.append(
                    f"UPDATE cal_acct_record SET END_DATE = '{v['next_start']}' "
                    f"WHERE ID = {v['id']} AND PROD_INST_ID = {self.current_data[0]['PROD_INST_ID']};"
                )
            return "连续性违规\n" + "\n".join(sql_list)
        return "无连续性违规"

    def _analyze_start_flag(self, data: str) -> str:
        """分析START_FLAG唯一性违规"""
        start_flag_rows = [r for r in self.current_data if r.get('START_FLAG') == 1]

        if len(start_flag_rows) != 1:
            # Find earliest START_DATE
            sorted_by_date = sorted(self.current_data,
                                   key=lambda x: x.get('START_DATE', ''))
            earliest = sorted_by_date[0]

            sql_list = []
            for r in self.current_data:
                if r['ID'] == earliest['ID']:
                    sql_list.append(
                        f"UPDATE cal_acct_record SET START_FLAG = 1 "
                        f"WHERE ID = {r['ID']} AND PROD_INST_ID = {r['PROD_INST_ID']};"
                    )
                elif r.get('START_FLAG') == 1:
                    sql_list.append(
                        f"UPDATE cal_acct_record SET START_FLAG = 0 "
                        f"WHERE ID = {r['ID']} AND PROD_INST_ID = {r['PROD_INST_ID']};"
                    )

            return "START_FLAG唯一性违规\n" + "\n".join(sql_list)
        return "无START_FLAG唯一性违规"

    def _analyze_latest_flag(self, data: str) -> str:
        """分析LATEST_FLAG一致性违规"""
        null_end_rows = [r for r in self.current_data if not r.get('END_DATE')]

        if null_end_rows:
            # Rows with NULL END_DATE must have LATEST_FLAG = 1
            invalid = [r for r in null_end_rows if r.get('LATEST_FLAG') != 1]

            if invalid:
                sql_list = []
                for r in invalid:
                    sql_list.append(
                        f"UPDATE cal_acct_record SET LATEST_FLAG = 1 "
                        f"WHERE ID = {r['ID']} AND PROD_INST_ID = {r['PROD_INST_ID']};"
                    )
                return "LATEST_FLAG一致性违规 (NULL END_DATE)\n" + "\n".join(sql_list)
        else:
            # Find row with max END_DATE
            max_end = max(self.current_data,
                         key=lambda x: x.get('END_DATE', ''))
            if max_end.get('LATEST_FLAG') != 1:
                sql_list = [
                    f"UPDATE cal_acct_record SET LATEST_FLAG = 1 "
                    f"WHERE ID = {max_end['ID']} AND PROD_INST_ID = {max_end['PROD_INST_ID']};"
                ]

                # Set others to 0
                for r in self.current_data:
                    if r['ID'] != max_end['ID'] and r.get('LATEST_FLAG') == 1:
                        sql_list.append(
                            f"UPDATE cal_acct_record SET LATEST_FLAG = 0 "
                            f"WHERE ID = {r['ID']} AND PROD_INST_ID = {r['PROD_INST_ID']};"
                        )

                return "LATEST_FLAG一致性违规 (MAX END_DATE)\n" + "\n".join(sql_list)

        return "无LATEST_FLAG一致性违规"

    def _format_final_sql(self, analysis: str) -> str:
        """格式化最终SQL"""
        lines = analysis.split('\n')
        sql_lines = [l for l in lines if l.strip().startswith('UPDATE')]
        return '\n'.join(sql_lines) if sql_lines else analysis

    def _parse_response(self, content: str) -> Dict[str, str]:
        """解析LLM响应以提取SQL和说明"""
        sql = ""
        explanation = ""

        # Try to extract SQL from code blocks
        sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Try to find UPDATE statements
            update_matches = re.findall(r'UPDATE.*?;', content, re.DOTALL | re.IGNORECASE)
            if update_matches:
                sql = '\n'.join(update_matches)
            else:
                # Look for SQL: prefix
                sql_match = re.search(r'SQL:\s*(.*?)(?:\n说明:|$)', content, re.DOTALL)
                if sql_match:
                    sql = sql_match.group(1).strip()
                else:
                    sql = content.strip()

        # Extract explanation
        # Look for 说明: prefix
        exp_match = re.search(r'说明:\s*(.*?)$', content, re.DOTALL)
        if exp_match:
            explanation = exp_match.group(1).strip()
        else:
            explanation = "SQL修复语句"

        return {
            "sql": sql if sql else "-- 无法从响应中提取SQL",
            "explanation": explanation if explanation else "SQL修复语句"
        }

    def call_with_custom_prompt(self, custom_prompt: str) -> Dict[str, str]:
        """
        使用自定义 prompt 直接调用 LLM。

        Args:
            custom_prompt: 自定义的提示词

        Returns:
            包含 'sql' 和 'explanation' 键的字典
        """
        try:
            if self.debug:
                print("=" * 80)
                print("使用自定义 Prompt 调用 LLM:")
                print("=" * 80)
                print(custom_prompt[:500] + "..." if len(custom_prompt) > 500 else custom_prompt)
                print("=" * 80)

            # 直接使用自定义 prompt 调用 LLM
            result = self.llm.invoke(custom_prompt)

            # 获取响应内容
            if hasattr(result, 'content'):
                content = result.content
            else:
                content = str(result)

            # 解析响应
            return self._parse_response(content)

        except Exception as e:
            return {
                "sql": f"-- 调用失败: {str(e)}",
                "explanation": f"错误: {str(e)}"
            }

    def _format_data_for_prompt(self, data: List[Dict[str, Any]]) -> str:
        """格式化记录数据以便包含在提示词中"""
        if not data:
            return "无数据"

        lines = []
        for i, row in enumerate(data, 1):
            row_data = []
            for k in ['ID', 'PROD_INST_ID', 'ACCT_ITEM_TYPE_ID', 'NAME',
                      'START_DATE', 'END_DATE', 'START_FLAG', 'LATEST_FLAG']:
                if k in row:
                    v = row[k]
                    if isinstance(v, str):
                        row_data.append(f"{k}='{v}'")
                    else:
                        row_data.append(f"{k}={v}")
            lines.append(f"  行{i}: " + ", ".join(row_data))

        return "\n".join(lines)

    def _format_log_data_for_prompt(self, log_data: Optional[List[Dict[str, Any]]]) -> str:
        """格式化日志数据以便包含在提示词中"""
        if not log_data:
            return "无日志数据"

        # 使用表格格式，与Few-shot示例保持一致
        headers = ['BEGIN_DATE', 'ATTR_ID', 'ATTR_NAME', 'MOD_BEFORE', 'MOD_AFTER',
                   'MOD_BEFORE_VAL', 'MOD_AFTER_VAL', 'MOD_REASON']

        # 构建表头
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        separator = " | ".join(["-------------------"] * len(headers))
        lines.append("| " + separator + " |")

        # 构建数据行
        for row in log_data:
            values = []
            for h in headers:
                val = row.get(h, '')
                if val is None:
                    val = '-'
                values.append(str(val))
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)


# Convenience function for quick usage
def generate_sql_fix(current_data: List[Dict[str, Any]],
                    violation_info: str,
                    log_data: Optional[List[Dict[str, Any]]] = None,
                    api_key: Optional[str] = None,
                    model: str = "glm-4-flash",
                    debug: bool = False) -> Dict[str, str]:
    """便捷函数，无需创建实例即可生成SQL修复"""
    agent = SQLGeneratorAgent(api_key=api_key, model=model, debug=debug)
    return agent.generate_fix_sql(current_data, violation_info, log_data)
