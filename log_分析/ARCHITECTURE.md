# Claude Code Log Visualizer - 架构文档

## 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [核心组件](#核心组件)
4. [数据流](#数据流)
5. [文件格式](#文件格式)
6. [API 接口](#api-接口)
7. [扩展指南](#扩展指南)

---

## 系统概述

Claude Code Log Visualizer 是一套用于解析和可视化 Claude Code 生成的 JSONL 日志文件的工具集。

### 设计目标

- **模块化** - 每个组件独立可测试
- **可扩展** - 易于添加新的日志类型支持
- **用户友好** - Web 界面和 CLI 双模式支持
- **高性能** - 支持大文件的流式处理

### 技术选型

| 需求 | 技术选择 | 理由 |
|------|----------|------|
| Web 框架 | Flask | 轻量级、易部署、单文件即可运行 |
| 数据处理 | Python 标准库 | 无外部依赖、跨平台 |
| HTML 生成 | 模板字符串 | 单文件部署、无需模板引擎 |
| 前端交互 | Vanilla JS | 无需构建、浏览器原生支持 |

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              表现层 (Presentation Layer)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │   Web Interface  │  │  CLI Interface   │  │  HTML Reports           │  │
│  │   (Flask + HTML) │  │  (argparse)      │  │  (Standalone Files)     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              业务层 (Business Layer)                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Parser Engine                                    │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │ │
│  │  │ HistoryParser   │  │ SessionLogParser│  │ SubagentLogParser    │  │ │
│  │  │                 │  │                 │  │                      │  │ │
│  │  │ - Timeline      │  │ - Conversations  │  │ - Event Chain        │  │ │
│  │  │ - Commands      │  │ - Tool Calls     │  │ - Tool Groups        │  │ │
│  │  │ - Statistics    │  │ - File Ops       │  │ - User Query         │  │ │
│  │  └─────────────────┘  └─────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                      │
│                                        ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        HTML Generator                                   │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  CSS Styles │ JavaScript │ HTML Structure │ Data Binding         │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层 (Data Layer)                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  File System    │  │  Type Detector  │  │  Relationship Finder       │ │
│  │  - JSONL Files  │  │  - Auto Detect  │  │  - Session ↔ Subagent     │ │
│  │  - Temp Files   │  │  - Validation   │  │  - History ↔ Session      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 组件交互图

```
┌─────────────┐     上传/选择      ┌─────────────┐
│    用户     │ ────────────────> │ Web Server  │
│  (Browser)  │ <──────────────── │   (Flask)   │
└─────────────┘     HTML 响应     └──────┬──────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                              ▼                           ▼
                    ┌───────────────┐           ┌───────────────┐
                    │ File Upload   │           │ Quick Access  │
                    │ Handler       │           │ Handler       │
                    └───────┬───────┘           └───────┬───────┘
                            │                           │
                            └───────────┬───────────────┘
                                        ▼
                              ┌──────────────────┐
                              │ Type Detector    │
                              │                  │
                              │  sessionId?      │──> Session Parser
                              │  + cwd?           │
                              │                  │
                              │  type + message? │──> Subagent Parser
                              │                  │
                              │  display?        │──> History Parser
                              └──────────────────┘
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                        ┌─────────┐          ┌─────────┐
                        │ Parser  │          │ Parser  │
                        └────┬────┘          └────┬────┘
                             │                   │
                             └───────────┬───────┘
                                         ▼
                              ┌──────────────────┐
                              │ HTML Generator   │
                              └────────┬─────────┘
                                       │
                              ┌────────┴─────────┐
                              ▼                  ▼
                        ┌─────────┐        ┌──────────┐
                        │ Preview │        │ Download │
                        │ (iframe)│        │   .html  │
                        └─────────┘        └──────────┘
```

---

## 核心组件

### 1. Visualizer Server (Web 服务器)

**文件**: `visualizer_server.py`

**职责**:
- 提供 Web 界面
- 处理文件上传
- 路由请求到对应的 Parser
- 返回生成的 HTML

**核心类**:
- `SubagentLogParser` - 解析子代理日志
- `HistoryParser` - 解析历史日志
- `SessionLogParser` - 解析会话日志

**Flask 路由**:

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 返回主页面 |
| `/upload` | POST | 处理上传的文件 |
| `/load_file` | POST | 加载指定路径的文件 |
| `/get_related_files` | POST | 获取相关文件列表 |

### 2. History Visualizer (CLI 工具)

**文件**: `history_visualizer.py`

**职责**:
- 命令行接口
- 解析 history.jsonl
- 生成独立 HTML 报告

**核心类**:

#### `HistoryParser`

```python
class HistoryParser:
    def parse() -> Dict[str, Any]  # 主入口
    def _extract_metadata() -> Dict  # 提取元数据
    def _build_timeline() -> List    # 构建时间线
    def _analyze_commands() -> Dict   # 分析命令使用
    def _build_hourly_activity() -> Dict   # 按小时统计
    def _build_daily_activity() -> Dict     # 按天统计
```

#### `HistoryHTMLGenerator`

```python
class HistoryHTMLGenerator:
    def generate(output_path: str) -> str  # 生成 HTML
    def _generate_css() -> str              # 生成 CSS
    def _generate_html_body() -> str        # 生成 HTML 主体
    def _generate_javascript() -> str       # 生成 JavaScript
```

### 3. Subagent Log Visualizer (CLI 工具)

**文件**: `subagent_log_visualizer.py`

**职责**:
- 解析 agent-*.jsonl 文件
- 提取用户查询
- 分析工具调用模式

**核心类**:

#### `SubagentLogParser`

```python
class SubagentLogParser:
    def parse() -> Dict[str, Any]
    def _extract_metadata() -> Dict
    def _extract_user_query() -> str   # 提取原始用户请求
    def _build_event_chain() -> List
    def _group_by_tool() -> Dict       # 按工具分组
    def _build_timeline() -> List
    def _build_statistics() -> Dict
```

---

## 数据流

### Web 模式数据流

```
用户选择文件
    │
    ▼
┌───────────────────┐
│ 文件上传 / 路径   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ detect_file_type()│
│ ┌─────────────────│
│ │ 读第一行 JSON   │
│ │ 判断类型:       │
│ │ - sessionId+cwd │
│ │   → Session     │
│ │ - type+message  │
│ │   → Subagent    │
│ │ - display       │
│ │   → History     │
│ └─────────────────│
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 对应 Parser.parse()│
│ ┌─────────────────│
│ │ 解析 JSONL      │
│ │ 提取结构化数据   │
│ └─────────────────│
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ generate_*_html() │
│ ┌─────────────────│
│ │ 生成 HTML + CSS │
│ │ + JavaScript    │
│ └─────────────────│
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 返回 HTML 响应    │
│ (浏览器显示)      │
└───────────────────┘
```

### CLI 模式数据流

```
命令行输入
    │
    ▼
┌───────────────────┐
│ argparse 解析参数 │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Parser.parse()    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Generator.generate()│
│ ┌─────────────────│
│ │ 写入 .html 文件  │
│ │ (可选: 打开浏览器)│
│ └─────────────────│
└───────────────────┘
```

---

## 文件格式

### 1. History 日志格式

**路径**: `~/.claude/history.jsonl`

```json
{
  "timestamp": 1705488000000,
  "sessionId": "abc123...",
  "project": "/path/to/project",
  "display": "user message or /command",
  "pastedContents": "optional pasted text"
}
```

**字段说明**:
- `timestamp`: Unix 时间戳（毫秒）
- `sessionId`: Claude Code 会话 ID
- `project`: 项目路径
- `display`: 用户输入或命令
- `pastedContents`: 粘贴的内容（可选）

### 2. Session 日志格式

**路径**: `~/.claude/projects/<sessionId>.jsonl`

```json
{
  "type": "user|assistant|system|file-history-snapshot|queue-operation",
  "uuid": "unique-message-id",
  "parentUuid": "parent-message-id",
  "timestamp": "2024-01-17T10:00:00Z",
  "sessionId": "session-id",
  "cwd": "/current/working/directory",
  "gitBranch": "main",
  "slug": "session-slug",
  "version": "1.0.0",
  "userType": "pro",
  "message": {
    "content": [
      {"type": "text", "text": "message content"},
      {"type": "tool_use", "id": "tool-id", "name": "bash", "input": {...}},
      {"type": "tool_result", "tool_use_id": "tool-id", "content": "...", "is_error": false}
    ],
    "model": "claude-3-opus-4-20250219",
    "usage": {"input_tokens": 100, "output_tokens": 50}
  }
}
```

**事件类型**:
- `user`: 用户消息
- `assistant`: AI 助手回复
- `system`: 系统事件（API 错误、重试等）
- `file-history-snapshot`: 文件历史快照
- `queue-operation`: 队列操作

### 3. Subagent 日志格式

**路径**: `~/.claude/projects/<sessionId>/subagents/agent-*.jsonl`

```json
{
  "type": "user|assistant|progress",
  "agentId": "agent-id",
  "sessionId": "session-id",
  "timestamp": "2024-01-17T10:00:00Z",
  "message": {
    "content": [
      {"type": "text", "text": "..."},
      {"type": "tool_use", "id": "...", "name": "Read", "input": {...}}
    ]
  }
}
```

**事件类型**:
- `user`: 用户输入到 Agent
- `assistant`: Agent 的响应
- `progress`: 进度更新

---

## API 接口

### Flask 路由规范

#### 1. `GET /`

返回主页面 HTML。

**响应**:
```html
<!DOCTYPE html>
<html>
  <!-- 完整的 Web 界面 -->
</html>
```

#### 2. `POST /upload`

上传并解析 JSONL 文件。

**请求**:
- Content-Type: `multipart/form-data`
- Body: `file` (文件)

**响应**:
```json
{
  "success": true,
  "html": "<html>...</html>"
}
```

或错误:
```json
{
  "success": false,
  "error": "error message"
}
```

#### 3. `POST /load_file`

通过文件路径加载日志文件。

**请求**:
```json
{
  "path": "/absolute/path/to/file.jsonl",
  "type": "session|subagent|history"
}
```

**响应**:
```json
{
  "success": true,
  "html": "<html>...</html>"
}
```

#### 4. `POST /get_related_files`

获取相关的日志文件列表。

**请求**:
```json
{
  "path": "/absolute/path/to/current.jsonl",
  "type": "session|subagent|history"
}
```

**响应**:
```json
{
  "success": true,
  "related": [
    {
      "name": "Session: abc123...",
      "path": "/absolute/path/to/session.jsonl",
      "type": "session"
    }
  ]
}
```

---

## 扩展指南

### 添加新的日志类型

#### 步骤 1: 创建 Parser 类

```python
class NewLogParser:
    def __init__(self, jsonl_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.entries: List[Dict[str, Any]] = []

    def parse(self) -> Dict[str, Any]:
        # 解析逻辑
        return {
            'metadata': self._extract_metadata(),
            'timeline': self._build_timeline(),
            'statistics': self._build_statistics(),
            'file_type': 'new_type'
        }
```

#### 步骤 2: 添加 HTML 生成函数

```python
def generate_new_type_html(data: Dict[str, Any]) -> str:
    metadata = data.get('metadata', {})
    timeline = data.get('timeline', [])

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            /* CSS 样式 */
        </style>
    </head>
    <body>
        <!-- HTML 内容 -->
    </body>
    </html>
    '''
```

#### 步骤 3: 更新文件类型检测

```python
def detect_file_type(file_path: str) -> str:
    with open(file_path, 'r') as f:
        first_line = f.readline()
        data = json.loads(first_line)

        if 'new_type_field' in data:
            return 'new_type'
        # ... 其他类型检测

    return 'unknown'
```

#### 步骤 4: 添加 Flask 路由处理

```python
@app.route('/load_file', methods=['POST'])
def load_file():
    # ... 现有代码

    if file_type == 'new_type':
        parser = NewLogParser(file_path)
        parsed_data = parser.parse()
        html = generate_new_type_html(parsed_data)
    # ... 其他类型
```

### 自定义 HTML 样式

编辑 `HTML_TEMPLATE` 变量中的 `<style>` 标签内容：

```python
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <style>
        /* 自定义样式 */
        .my-custom-class {
            background: linear-gradient(135deg, #custom, #colors);
        }
    </style>
</head>
...
'''
```

### 添加新的统计指标

在 Parser 类中扩展 `_build_statistics()` 方法：

```python
def _build_statistics(self) -> Dict[str, Any]:
    stats = {
        # 现有统计
        'total_events': len(self.events),
        # 新统计
        'custom_metric': self._calculate_custom_metric()
    }
    return stats
```

---

## 性能考虑

### 大文件处理

- **流式读取**: 逐行读取 JSONL，而非一次性加载到内存
- **显示限制**: Web 界面限制显示最近 100 条记录
- **分页支持**: CLI 工具支持指定输出范围

### 内存优化

- **生成器模式**: 使用生成器处理大量数据
- **及时清理**: 处理完临时文件后立即删除
- **字符串优化**: 使用字符串拼接而非列表展开（适用于小数据量）

---

## 安全考虑

### 文件访问限制

- 仅允许访问 `~/.claude/` 目录下的文件
- 路径验证防止目录遍历攻击
- 文件类型白名单验证

### 输入清理

- HTML 转义防止 XSS 攻击
- 文件名验证防止路径注入
- 请求大小限制（50MB max）

---

## 故障排查

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `File not found` | 日志文件路径错误 | 检查 `~/.claude/` 目录 |
| `Unknown file format` | 文件格式不匹配 | 验证 JSONL 格式 |
| `Port 5000 already in use` | 端口被占用 | 修改端口或停止占用进程 |
| `Failed to parse line` | JSON 格式错误 | 检查日志文件完整性 |

### 调试模式

启用 Flask 调试模式：

```python
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)  # 启用调试
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2024-01-17 | 初始版本 |

---

## 作者

kunge2013
