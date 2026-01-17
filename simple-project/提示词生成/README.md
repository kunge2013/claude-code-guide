# 简历模板知识库 Agent

基于 LangChain + 智谱 AI GLM-4.7 的简历模板查询助手，提供命令行和 Web 界面两种使用方式。

## 功能特性

- 🤖 **AI 智能查询**: 基于大语言模型的自然语言理解
- 📊 **Excel 知识库**: 简单易用的模板数据管理
- 💬 **聊天界面**: Streamlit 构建的友好 Web 界面
- 🔗 **一键下载**: 直接获取百度网盘下载链接
- 🎯 **模糊匹配**: 支持关键词模糊搜索

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              简历模板知识库 Agent                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐      ┌──────────────────┐      ┌─────────────────┐    │
│  │   用户界面层   │      │    Agent 层      │      │   数据存储层    │    │
│  ├────────────────┤      ├──────────────────┤      ├─────────────────┤    │
│  │                │      │                  │      │                 │    │
│  │  ┌──────────┐  │      │  ┌────────────┐  │      │  ┌───────────┐  │    │
│  │  │ CLI 模式 │  │      │  │ LangChain  │  │      │  │   Excel   │  │    │
│  │  ├──────────┤  │      │  │   Agent    │  │      │  │ Knowledge │  │    │
│  │  │ Web 界面 │  │◄────►│  │            │  │◄────►│  │   Base    │  │    │
│  │  ├──────────┤  │      │  ├────────────┤  │      │  │           │  │    │
│  │  │          │  │      │  │  Tools:    │  │      │  │ 8 简历    │  │    │
│  │  │Streamlit │  │      │  │  - search  │  │      │  │   模板    │  │    │
│  │  └──────────┘  │      │  │  - list    │  │      │  └───────────┘  │    │
│  │                │      │  │  - exact   │  │      │                 │    │
│  └────────────────┘      │  └────────────┘  │      └─────────────────┘    │
│                           │                  │                              │
│                           └──────────────────┘                              │
│                                    │                                        │
│                                    ▼                                        │
│                           ┌──────────────────┐                              │
│                           │  智谱 AI API     │                              │
│                           │  GLM-4.7 模型    │                              │
│                           └──────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
提示词生成/
├── resume_agent/              # Agent 核心模块
│   ├── __init__.py           # 包初始化，导出 ResumeTemplateAgent 和 Config
│   ├── agent.py              # LangChain Agent 实现
│   ├── tools.py              # LangChain 工具（Excel 查询）
│   └── config.py             # 配置管理（API 密钥、文件路径）
├── app.py                    # Streamlit Web 界面
├── resume_agent.py           # 命令行入口脚本
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── .env                      # 环境变量（需自行创建，不提交到版本控制）
├── README.md                 # 本文档
├── resume-template-agent.md  # Agent 提示词参考文档
└── 9b1af114-...xlsx         # 简历模板知识库数据
```

## 快速开始

### 1. 环境准备

```bash
# 创建 Python 虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入您的 API 配置
# 或直接在 .env 中设置：
# ANTHROPIC_AUTH_TOKEN=your_api_token_here
# ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
```

### 3. 运行方式

#### 方式一：Web 界面（推荐）

```bash
# 启动 Web 服务
streamlit run app.py --server.port 8501

# 访问 http://localhost:8501
```

#### 方式二：命令行模式

```bash
# 演示模式（预设查询示例）
python resume_agent.py

# 单次查询
python resume_agent.py --query "大学生简历模板"

# 交互模式
python resume_agent.py --interactive
```

## 可用的简历模板

| 序号 | 模板名称 | 提取码 |
|------|----------|--------|
| 1 | 人事行政简历模板 | he3b |
| 2 | 互联网职位模板 | aax7 |
| 3 | 医生护士简历模板 | cwqw |
| 4 | 大学生简历模板 | gaii |
| 5 | 教师幼师简历模板 | m54g |
| 6 | 研究生简历模板 | ff94 |
| 7 | 财会金融简历模板 | vev7 |
| 8 | 通用简历模板 | n2a6 |

## 使用示例

### Web 界面

1. 打开浏览器访问 `http://localhost:8501`
2. 在聊天框中输入关键词，如"人事行政简历模板"
3. 点击查询按钮
4. 获取下载链接并点击下载

### 命令行

```bash
# 查询人事行政简历模板
python resume_agent.py --query "人事行政简历模板"

# 输出示例：
# **模板名称**: 人事行政简历模板
# **下载地址**: https://pan.baidu.com/s/1sgkqxM8--OoY9Aw26FExxg?pwd=he3b
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | LangChain 1.2.6 |
| 大语言模型 | 智谱 AI GLM-4.7 |
| Web 框架 | Streamlit 1.53.0 |
| 数据存储 | Excel (pandas + openpyxl) |
| 环境配置 | python-dotenv |

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ANTHROPIC_AUTH_TOKEN` | 智谱 AI API 密钥 | - |
| `ANTHROPIC_BASE_URL` | API 基础 URL | `https://open.bigmodel.cn/api/anthropic` |
| `API_TIMEOUT_MS` | 请求超时时间（毫秒） | `3000000` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | 使用的模型 | `GLM-4.7` |

### Agent 工具

| 工具 | 功能 | 使用场景 |
|------|------|----------|
| `search_resume_template` | 模糊搜索模板 | 推荐使用，支持关键词匹配 |
| `list_all_templates` | 列出所有模板 | 查看所有可用模板 |
| `get_template_by_exact_name` | 精确名称匹配 | 提供完整准确名称时使用 |

## 开发说明

### 添加新的简历模板

编辑 `9b1af114-6719-4148-8194-412b68c0d44d-tmp.xlsx` 文件：

| 问题 | 答案 |
|------|------|
| 新模板名称 | https://pan.baidu.com/s/xxx?pwd=xxxx |

### 自定义 Agent 提示词

修改 `resume_agent/agent.py` 中的 `SYSTEM_PROMPT` 常量。

### 修改知识库路径

编辑 `resume_agent/config.py` 中的 `EXCEL_FILE_PATH` 变量。

## 常见问题

### Q: 提示 "Unknown scheme for proxy URL" 错误？

A: 取消代理设置后再运行：

```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
python resume_agent.py
```

### Q: 如何更改端口？

A: Streamlit 启动时指定端口：

```bash
streamlit run app.py --server.port 8080
```

### Q: API 调用失败？

A: 检查 `.env` 文件中的 API 密钥是否正确配置。

## 许可证

MIT License

## 作者

kunge2013
