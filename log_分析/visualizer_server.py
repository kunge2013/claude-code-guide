#!/usr/bin/env python3
"""
Claude Code Log Visualizer Web Server

A web-based tool to visualize Claude Code JSONL logs with file selection and preview.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from flask import Flask, render_template_string, request, jsonify, send_file
from typing import Any, Dict, List

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Log Visualizer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            text-align: center;
        }

        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 32px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 25px;
        }

        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f8f9ff;
        }

        .upload-area:hover {
            background: #f0f2ff;
            border-color: #5568d3;
        }

        .upload-area.dragover {
            background: #e8ebff;
            border-color: #4c5fd1;
        }

        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }

        .upload-text {
            color: #667eea;
            font-size: 18px;
            margin-bottom: 10px;
        }

        .upload-hint {
            color: #999;
            font-size: 14px;
        }

        #fileInput {
            display: none;
        }

        .quick-files {
            background: white;
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        }

        .quick-files h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 20px;
        }

        .file-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
        }

        .file-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 10px;
            cursor: pointer;
            text-align: left;
            transition: all 0.3s;
            font-size: 14px;
        }

        .file-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .file-btn-name {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .file-btn-path {
            font-size: 11px;
            opacity: 0.8;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .preview-container {
            display: none;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }

        .preview-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .preview-title {
            color: white;
            font-size: 18px;
            font-weight: 600;
        }

        .preview-actions {
            display: flex;
            gap: 10px;
        }

        .preview-actions button {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }

        .btn-download {
            background: white;
            color: #667eea;
            font-weight: 600;
        }

        .btn-download:hover {
            background: #f0f2ff;
        }

        .btn-close {
            background: rgba(255,255,255,0.2);
            color: white;
        }

        .btn-close:hover {
            background: rgba(255,255,255,0.3);
        }

        .preview-frame {
            width: 100%;
            height: 80vh;
            border: none;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 60px;
            color: #667eea;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error {
            display: none;
            background: #fee;
            border: 1px solid #fcc;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            color: #c33;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .stat-card {
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ebff 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #667eea;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Claude Code Log Visualizer</h1>
            <p class="subtitle">可视化 Claude Code JSONL 日志文件</p>

            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div class="upload-text">点击选择文件 或 拖拽文件到此处</div>
                <div class="upload-hint">支持 .jsonl 文件 (Subagent Log / History)</div>
                <input type="file" id="fileInput" accept=".jsonl" />
            </div>
        </div>

        <div class="quick-files" id="quickFiles">
            <h2>快速打开常用文件</h2>
            <div class="file-buttons" id="fileButtons">
                <!-- File buttons will be inserted here -->
            </div>
        </div>

        <div class="error" id="errorBox"></div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>正在解析并生成可视化...</p>
        </div>

        <div class="preview-container" id="previewContainer">
            <div class="preview-header">
                <span class="preview-title" id="previewTitle">预览</span>
                <div class="preview-actions">
                    <button class="btn-download" onclick="downloadHTML()">下载 HTML</button>
                    <button class="btn-close" onclick="closePreview()">关闭</button>
                </div>
            </div>
            <iframe class="preview-frame" id="previewFrame"></iframe>
        </div>
    </div>

    <script>
        const quickFiles = {{ quick_files | tojson }};
        let currentHTML = '';

        // Initialize quick file buttons
        function initQuickFiles() {
            const container = document.getElementById('fileButtons');
            container.innerHTML = '';

            quickFiles.forEach(file => {
                const btn = document.createElement('button');
                btn.className = 'file-btn';
                btn.innerHTML = `
                    <div class="file-btn-name">${file.name}</div>
                    <div class="file-btn-path">${file.path}</div>
                `;
                btn.onclick = () => loadFile(file.path, file.type);
                container.appendChild(btn);
            });
        }

        // File upload handling
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.name.endsWith('.jsonl')) {
                handleFileUpload(file);
            }
        });

        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                handleFileUpload(file);
            }
        });

        async function handleFileUpload(file) {
            const formData = new FormData();
            formData.append('file', file);

            showLoading();
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (result.success) {
                    showPreview(result.html, file.name);
                } else {
                    showError(result.error || '文件解析失败');
                }
            } catch (err) {
                showError('上传失败: ' + err.message);
            }
            hideLoading();
        }

        async function loadFile(path, type) {
            showLoading();
            try {
                const response = await fetch('/load_file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path, type })
                });
                const result = await response.json();
                if (result.success) {
                    const name = path.split(/[\\/]/).pop();
                    showPreview(result.html, name);
                } else {
                    showError(result.error || '文件加载失败');
                }
            } catch (err) {
                showError('加载失败: ' + err.message);
            }
            hideLoading();
        }

        function showPreview(html, title) {
            currentHTML = html;
            document.getElementById('previewTitle').textContent = title;
            const frame = document.getElementById('previewFrame');
            frame.srcdoc = html;
            document.getElementById('previewContainer').style.display = 'block';
            document.getElementById('previewContainer').scrollIntoView({ behavior: 'smooth' });
        }

        function closePreview() {
            document.getElementById('previewContainer').style.display = 'none';
            currentHTML = '';
        }

        function downloadHTML() {
            if (!currentHTML) return;
            const blob = new Blob([currentHTML], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = document.getElementById('previewTitle').textContent.replace('.jsonl', '.html');
            a.click();
            URL.revokeObjectURL(url);
        }

        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('errorBox').style.display = 'none';
        }

        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }

        function showError(message) {
            const errorBox = document.getElementById('errorBox');
            errorBox.textContent = message;
            errorBox.style.display = 'block';
        }

        // Initialize
        initQuickFiles();
    </script>
</body>
</html>
'''


# =============================================================================
# PARSING CODE (Reused from previous scripts)
# =============================================================================

class SubagentLogParser:
    """Parser for Claude Code subagent JSONL log files."""

    def __init__(self, jsonl_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.events: List[Dict[str, Any]] = []

    def parse(self) -> Dict[str, Any]:
        """Parse the JSONL file and return structured data."""
        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.jsonl_path}")

        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return {
            'metadata': self._extract_metadata(),
            'user_query': self._extract_user_query(),
            'event_chain': self._build_event_chain(),
            'tool_groups': self._group_by_tool(),
            'timeline': self._build_timeline(),
            'statistics': self._build_statistics(),
            'file_type': 'subagent'
        }

    def _extract_metadata(self) -> Dict[str, Any]:
        if not self.events:
            return {}
        first_event = self.events[0]
        last_event = self.events[-1]
        return {
            'agent_id': first_event.get('agentId', 'Unknown'),
            'session_id': first_event.get('sessionId', 'Unknown'),
            'total_events': len(self.events),
            'start_time': first_event.get('timestamp', 'Unknown'),
            'end_time': last_event.get('timestamp', 'Unknown'),
            'file_name': self.jsonl_path.name
        }

    def _extract_user_query(self) -> str:
        for event in self.events:
            if event.get('type') == 'user':
                message = event.get('message', {})
                content = message.get('content', '')
                if isinstance(content, list):
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            texts.append(block.get('text', ''))
                    return '\n'.join(texts)
                return str(content)
        return "No user query found"

    def _build_event_chain(self) -> List[Dict[str, Any]]:
        chain = []
        for i, event in enumerate(self.events):
            chain.append({
                'index': i + 1,
                'type': event.get('type', 'unknown'),
                'timestamp': event.get('timestamp', ''),
                'message': event.get('message', {}),
                'raw': event
            })
        return chain

    def _group_by_tool(self) -> Dict[str, List[Dict[str, Any]]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for i, event in enumerate(self.events):
            if event.get('type') == 'assistant':
                message = event.get('message', {})
                content = message.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            tool_name = block.get('name', 'Unknown')
                            if tool_name not in groups:
                                groups[tool_name] = []
                            groups[tool_name].append({
                                'index': i + 1,
                                'id': block.get('id', ''),
                                'name': tool_name,
                                'input': block.get('input', {}),
                                'timestamp': event.get('timestamp', ''),
                                'raw': block
                            })
        return groups

    def _build_timeline(self) -> List[Dict[str, Any]]:
        timeline = []
        for i, event in enumerate(self.events):
            timestamp = event.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp

            event_type = event.get('type', '')
            summary_info = self._get_event_summary(event)

            timeline.append({
                'index': i + 1,
                'type': event_type,
                'sub_type': summary_info.get('sub_type', 'unknown'),
                'is_model_call': summary_info.get('is_model_call', False),
                'is_tool_call': summary_info.get('is_tool_call', False),
                'time': time_str,
                'timestamp': timestamp,
                'summary': summary_info.get('summary', ''),
                'tool_name': summary_info.get('tool_name', ''),
                'model_text': summary_info.get('model_text', ''),
                'raw': event
            })
        return timeline

    def _get_event_summary(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed event summary with type classification."""
        event_type = event.get('type', '')
        result = {
            'summary': '',
            'sub_type': 'unknown',
            'is_model_call': False,
            'is_tool_call': False,
            'tool_name': '',
            'model_text': ''
        }

        if event_type == 'user':
            result['sub_type'] = 'user_input'
            message = event.get('message', {})
            content = message.get('content', '')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text = block.get('text', '')
                        result['summary'] = text[:100] + '...' if len(text) > 100 else text
                        return result
            result['summary'] = str(content)[:100] + '...' if len(str(content)) > 100 else str(content)
            return result

        elif event_type == 'assistant':
            message = event.get('message', {})
            content = message.get('content', [])
            if isinstance(content, list):
                tool_uses = [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_use']
                texts = [b for b in content if isinstance(b, dict) and b.get('type') == 'text']

                # Check if this is primarily a tool call
                if tool_uses and not texts:
                    result['sub_type'] = 'tool_call_only'
                    result['is_tool_call'] = True
                    result['tool_name'] = tool_uses[0].get('name', 'Unknown')
                    result['summary'] = f"🔧 {result['tool_name']}: {str(tool_uses[0].get('input', {}))[:80]}"
                    return result

                # Check if this is model response with text
                if texts and any(t.get('text', '').strip() for t in texts):
                    result['sub_type'] = 'model_response'
                    result['is_model_call'] = True
                    model_text = ' '.join(t.get('text', '') for t in texts if t.get('text', '').strip())
                    result['model_text'] = model_text
                    result['summary'] = f"🤖 {model_text[:100]}..." if len(model_text) > 100 else f"🤖 {model_text}"

                    if tool_uses:
                        tool_names = ', '.join(t.get('name', '?') for t in tool_uses)
                        result['summary'] += f" | +工具: {tool_names}"
                        result['sub_type'] = 'model_with_tools'
                        result['is_tool_call'] = True
                    return result

                # Just tool calls without model text
                if tool_uses:
                    result['sub_type'] = 'tool_call'
                    result['is_tool_call'] = True
                    tool_names = ', '.join(t.get('name', '?') for t in tool_uses)
                    result['summary'] = f"🔧 调用工具: {tool_names}"
                    return result

            result['summary'] = 'Assistant response'
            return result

        elif event_type == 'progress':
            result['sub_type'] = 'progress_update'
            message = event.get('message', {})
            content = message.get('content', '')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text = block.get('text', '')[:100]
                        result['summary'] = f"📋 {text}"
                        return result
            result['summary'] = 'Progress update'
            return result

        result['summary'] = f'{event_type} event'
        return result

    def _build_statistics(self) -> Dict[str, Any]:
        stats = {
            'total_events': len(self.events),
            'by_type': {},
            'by_sub_type': {},
            'model_calls': 0,
            'tool_calls': 0,
            'by_tool': {}
        }
        for event in self.events:
            event_type = event.get('type', 'unknown')
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1

            summary_info = self._get_event_summary(event)
            sub_type = summary_info.get('sub_type', 'unknown')
            stats['by_sub_type'][sub_type] = stats['by_sub_type'].get(sub_type, 0) + 1

            if summary_info.get('is_model_call'):
                stats['model_calls'] += 1
            if summary_info.get('is_tool_call'):
                stats['tool_calls'] += 1

            # Count by tool name
            if summary_info.get('tool_name'):
                tool_name = summary_info.get('tool_name')
                stats['by_tool'][tool_name] = stats['by_tool'].get(tool_name, 0) + 1

        return stats


class HistoryParser:
    """Parser for Claude Code history.jsonl log files."""

    def __init__(self, jsonl_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.entries: List[Dict[str, Any]] = []

    def parse(self) -> Dict[str, Any]:
        """Parse the JSONL file and return structured data."""
        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"History file not found: {self.jsonl_path}")

        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return {
            'metadata': self._extract_metadata(),
            'timeline': self._build_timeline(),
            'commands': self._analyze_commands(),
            'statistics': self._build_statistics(),
            'hourly_activity': self._build_hourly_activity(),
            'file_type': 'history'
        }

    def _extract_metadata(self) -> Dict[str, Any]:
        if not self.entries:
            return {}
        first = self.entries[0]
        last = self.entries[-1]
        return {
            'file_name': self.jsonl_path.name,
            'total_entries': len(self.entries),
            'unique_sessions': len(set(e.get('sessionId', '') for e in self.entries)),
            'unique_projects': len(set(e.get('project', '') for e in self.entries)),
            'time_span_days': self._calculate_time_span(first, last)
        }

    def _calculate_time_span(self, first: Dict, last: Dict) -> float:
        try:
            first_time = first.get('timestamp', 0) / 1000
            last_time = last.get('timestamp', 0) / 1000
            return (last_time - first_time) / 86400
        except:
            return 0

    def _build_timeline(self) -> List[Dict[str, Any]]:
        timeline = []
        for i, entry in enumerate(self.entries):
            timestamp = entry.get('timestamp', 0)
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                hour = dt.hour
            except:
                time_str = str(timestamp)
                hour = 0
            display = entry.get('display', '')
            command_type = self._classify_command(display)
            timeline.append({
                'index': i + 1,
                'timestamp': timestamp,
                'time_str': time_str,
                'hour': hour,
                'display': display,
                'project': entry.get('project', ''),
                'command_type': command_type,
                'raw': entry
            })
        return timeline

    def _classify_command(self, display: str) -> str:
        if not display:
            return 'empty'
        if display.startswith('/'):
            return 'slash_command'
        return 'user_input'

    def _analyze_commands(self) -> Dict[str, Any]:
        slash_commands = []
        for entry in self.entries:
            display = entry.get('display', '')
            if display.startswith('/'):
                cmd = display.split()[0].lower()
                slash_commands.append(cmd)
        return {
            'slash_commands': Counter(slash_commands),
            'most_common_commands': Counter(slash_commands).most_common(10)
        }

    def _build_statistics(self) -> Dict[str, Any]:
        return {
            'total_entries': len(self.entries),
            'total_sessions': len(set(e.get('sessionId', '') for e in self.entries))
        }

    def _build_hourly_activity(self) -> Dict[int, int]:
        hourly = defaultdict(int)
        for entry in self.entries:
            timestamp = entry.get('timestamp', 0)
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                hourly[dt.hour] += 1
            except:
                pass
        return dict(hourly)


# =============================================================================
# HTML GENERATION CODE (Simplified for web display)
# =============================================================================

def _get_type_badge(sub_type: str, is_model: bool, is_tool: bool) -> str:
    """Get HTML badge for event type."""
    if is_model:
        return '<span class="badge-model">🤖 AI</span>'
    elif is_tool:
        return '<span class="badge-tool">🔧 工具</span>'
    elif sub_type == 'user_input':
        return '<span class="badge-user">👤 用户</span>'
    elif sub_type == 'progress_update':
        return '<span class="badge-progress">📋 进度</span>'
    return ''


def generate_subagent_html(data: Dict[str, Any]) -> str:
    """Generate HTML for subagent log visualization."""
    metadata = data.get('metadata', {})
    stats = data.get('statistics', {})
    timeline = data.get('timeline', [])
    tool_groups = data.get('tool_groups', {})
    user_query = data.get('user_query', '')

    timeline_items = []
    for item in timeline:
        event_type = item.get('type', 'unknown')
        sub_type = item.get('sub_type', 'unknown')
        raw_json = _html_escape(json.dumps(item.get('raw'), indent=2, ensure_ascii=False))
        is_model = item.get('is_model_call', False)
        is_tool = item.get('is_tool_call', False)

        # Add specific class for model/tool calls
        extra_class = ''
        if is_model:
            extra_class = ' is-model-call'
        elif is_tool:
            extra_class = ' is-tool-call'

        timeline_items.append(f'''<div class="timeline-item type-{event_type} subtype-{sub_type}{extra_class}" onclick="this.classList.toggle('expanded')">
            <div class="timeline-dot"></div>
            <div class="timeline-time">{item.get('time', '')}</div>
            <div class="timeline-type-badge">{_get_type_badge(sub_type, is_model, is_tool)}</div>
            <div class="timeline-summary">{_html_escape(item.get('summary', ''))}</div>
            <div class="timeline-expand">点击查看详情</div>
            <div class="timeline-details">{raw_json}</div>
        </div>''')

    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: system-ui; background: #f5f5f5; padding: 20px; }}
        .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin: 0 0 15px 0; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .stat-card.model {{ background: linear-gradient(135deg, #FF6B6B, #ee5a6f); }}
        .stat-card.tool {{ background: linear-gradient(135deg, #4ECDC4, #44a08d); }}
        .stat-value {{ font-size: 28px; font-weight: bold; }}
        .stat-label {{ font-size: 12px; opacity: 0.9; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .section h2 {{ font-size: 16px; margin-bottom: 15px; color: #333; }}
        .user-query {{ background: #f0f7ff; padding: 15px; border-left: 4px solid #2196F3; border-radius: 5px; white-space: pre-wrap; }}
        .timeline {{ position: relative; padding-left: 30px; }}
        .timeline-item {{ padding: 12px 0; border-left: 2px solid #ddd; margin-left: 10px; position: relative; padding-left: 20px; cursor: pointer; transition: background 0.2s; border-radius: 5px; }}
        .timeline-item:hover {{ background: #f9f9f9; padding-left: 25px; }}
        .timeline-item.is-model-call {{ border-left-color: #FF6B6B; }}
        .timeline-item.is-tool-call {{ border-left-color: #4ECDC4; }}
        .timeline-dot {{ position: absolute; left: -6px; top: 18px; width: 10px; height: 10px; border-radius: 50%; background: #999; }}
        .type-user .timeline-dot {{ background: #4CAF50; }}
        .type-assistant .timeline-dot {{ background: #2196F3; }}
        .type-progress .timeline-dot {{ background: #FF9800; }}
        .is-model-call .timeline-dot {{ background: #FF6B6B; }}
        .is-tool-call .timeline-dot {{ background: #4ECDC4; }}
        .timeline-time {{ font-size: 11px; color: #999; font-weight: 500; }}
        .timeline-type-badge {{ display: inline-block; margin-left: 8px; font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
        .badge-model {{ background: #FFE5E5; color: #D63031; }}
        .badge-tool {{ background: #E5F9F6; color: #00B894; }}
        .badge-user {{ background: #E8F5E9; color: #2E7D32; }}
        .badge-progress {{ background: #FFF3E0; color: #E65100; }}
        .timeline-summary {{ margin-top: 8px; color: #333; line-height: 1.5; }}
        .timeline-expand {{ color: #667eea; font-size: 11px; margin-top: 8px; display: inline-block; }}
        .timeline-details {{ display: none; margin-top: 12px; padding: 12px; background: #1e1e1e; color: #d4d4d4; border-radius: 6px; font-family: Consolas, Monaco, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto; }}
        .timeline-item.expanded .timeline-details {{ display: block; }}
        .timeline-item.expanded .timeline-expand {{ display: none; }}
        .tool-item {{ padding: 10px; background: #f8f9fa; margin-bottom: 8px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Subagent Log: {_html_escape(metadata.get('file_name', 'Unknown'))}</h1>
        <div class="stats">
            <div class="stat-card"><div class="stat-value">{stats.get('total_events', 0)}</div><div class="stat-label">总事件</div></div>
            <div class="stat-card model"><div class="stat-value">{stats.get('model_calls', 0)}</div><div class="stat-label">🤖 AI 调用</div></div>
            <div class="stat-card tool"><div class="stat-value">{stats.get('tool_calls', 0)}</div><div class="stat-label">🔧 工具调用</div></div>
            <div class="stat-card"><div class="stat-value">{stats.get('by_type', {}).get('user', 0)}</div><div class="stat-label">👤 用户</div></div>
            <div class="stat-card"><div class="stat-value">{stats.get('by_type', {}).get('progress', 0)}</div><div class="stat-label">📋 进度</div></div>
        </div>
    </div>
    <div class="section">
        <h2>User Query</h2>
        <div class="user-query">{_html_escape(user_query)}</div>
    </div>
    <div class="section">
        <h2>Timeline</h2>
        <div class="timeline">{''.join(timeline_items)}</div>
    </div>
    <div class="section">
        <h2>Tools Used</h2>
        {tool_html}
    </div>
</body>
</html>'''


def generate_history_html(data: Dict[str, Any]) -> str:
    """Generate HTML for history visualization."""
    metadata = data.get('metadata', {})
    stats = data.get('statistics', {})
    commands = data.get('commands', {})
    timeline = data.get('timeline', [])

    cmd_items = ''
    for cmd, count in commands.get('most_common_commands', []):
        cmd_items += f'<div class="cmd-item"><code>{_html_escape(cmd)}</code> <span>{count}</span></div>'

    timeline_items = ''
    for item in reversed(timeline[-100:]):  # Last 100
        cmd_type = item.get('command_type', 'user_input')
        raw_json = _html_escape(json.dumps(item.get('raw'), indent=2, ensure_ascii=False))
        timeline_items += f'''<div class="timeline-item type-{cmd_type}" onclick="this.classList.toggle('expanded')">
            <div class="timeline-time">{item.get('time_str', '')}</div>
            <div class="timeline-display">{_html_escape(item.get('display', ''))}</div>
            <div class="timeline-expand">点击查看详情</div>
            <div class="timeline-details">{raw_json}</div>
        </div>'''

    return f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: system-ui; background: #f5f5f5; padding: 20px; }}
        .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin: 0 0 15px 0; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .stat-value {{ font-size: 28px; font-weight: bold; }}
        .stat-label {{ font-size: 12px; opacity: 0.9; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .cmd-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .cmd-item {{ display: flex; justify-content: space-between; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .cmd-item code {{ background: #e9ecef; padding: 2px 8px; border-radius: 3px; }}
        .timeline {{ position: relative; padding-left: 30px; }}
        .timeline-item {{ padding: 12px 0; border-left: 2px solid #ddd; margin-left: 10px; position: relative; padding-left: 20px; cursor: pointer; transition: background 0.2s; border-radius: 5px; }}
        .timeline-item:hover {{ background: #f9f9f9; padding-left: 25px; }}
        .timeline-dot {{ position: absolute; left: -6px; top: 18px; width: 10px; height: 10px; border-radius: 50%; background: #999; }}
        .type-slash_command .timeline-dot {{ background: #17a2b8; }}
        .type-user_input .timeline-dot {{ background: #28a745; }}
        .timeline-time {{ font-size: 11px; color: #999; font-weight: 500; }}
        .timeline-display {{ margin-top: 5px; color: #333; line-height: 1.5; }}
        .timeline-expand {{ color: #667eea; font-size: 11px; margin-top: 8px; display: inline-block; }}
        .timeline-details {{ display: none; margin-top: 12px; padding: 12px; background: #1e1e1e; color: #d4d4d4; border-radius: 6px; font-family: Consolas, Monaco, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto; }}
        .timeline-item.expanded .timeline-details {{ display: block; }}
        .timeline-item.expanded .timeline-expand {{ display: none; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>History Log</h1>
        <div class="stats">
            <div class="stat-card"><div class="stat-value">{stats.get('total_entries', 0)}</div><div class="stat-label">Total Entries</div></div>
            <div class="stat-card"><div class="stat-value">{metadata.get('unique_sessions', 0)}</div><div class="stat-label">Sessions</div></div>
            <div class="stat-card"><div class="stat-value">{metadata.get('unique_projects', 0)}</div><div class="stat-label">Projects</div></div>
            <div class="stat-card"><div class="stat-value">{metadata.get('time_span_days', 0):.1f}</div><div class="stat-label">Days</div></div>
        </div>
    </div>
    <div class="section">
        <h2>Top Commands</h2>
        <div class="cmd-grid">{cmd_items}</div>
    </div>
    <div class="section">
        <h2>Timeline (Last 50)</h2>
        <div class="timeline">{timeline_items}</div>
    </div>
</body>
</html>'''


def _html_escape(text: str) -> str:
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def detect_file_type(file_path: str) -> str:
    """Detect if file is history or subagent log."""
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line:
            try:
                data = json.loads(first_line)
                if 'type' in data and 'message' in data:
                    return 'subagent'
                elif 'display' in data and 'timestamp' in data:
                    return 'history'
            except:
                pass
    return 'unknown'


def get_quick_files() -> List[Dict[str, str]]:
    """Get list of quick access files."""
    files = []

    # History file
    history_path = Path.home() / '.claude' / 'history.jsonl'
    if history_path.exists():
        files.append({
            'name': 'History (主历史记录)',
            'path': str(history_path),
            'type': 'history'
        })

    # Subagent files
    claude_projects = Path.home() / '.claude' / 'projects'
    if claude_projects.exists():
        for jsonl_file in claude_projects.glob('**/subagents/*.jsonl'):
            files.append({
                'name': f"Subagent: {jsonl_file.stem}",
                'path': str(jsonl_file),
                'type': 'subagent'
            })

    return files[:20]  # Limit to 20 files


# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route('/')
def index():
    quick_files = get_quick_files()
    return render_template_string(HTML_TEMPLATE, quick_files=quick_files)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    if not file.filename.endswith('.jsonl'):
        return jsonify({'success': False, 'error': 'Invalid file format. Please upload .jsonl file'})

    try:
        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl') as tmp:
            file.save(tmp.name)
            file_type = detect_file_type(tmp.name)

            if file_type == 'subagent':
                parser = SubagentLogParser(tmp.name)
                data = parser.parse()
                html = generate_subagent_html(data)
            elif file_type == 'history':
                parser = HistoryParser(tmp.name)
                data = parser.parse()
                html = generate_history_html(data)
            else:
                return jsonify({'success': False, 'error': 'Unknown file format'})

        os.unlink(tmp.name)
        return jsonify({'success': True, 'html': html})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/load_file', methods=['POST'])
def load_file():
    data = request.json
    file_path = data.get('path')
    file_type = data.get('type', 'auto')

    if not file_path or not Path(file_path).exists():
        return jsonify({'success': False, 'error': 'File not found'})

    try:
        if file_type == 'auto':
            file_type = detect_file_type(file_path)

        if file_type == 'subagent':
            parser = SubagentLogParser(file_path)
            parsed_data = parser.parse()
            html = generate_subagent_html(parsed_data)
        elif file_type == 'history':
            parser = HistoryParser(file_path)
            parsed_data = parser.parse()
            html = generate_history_html(parsed_data)
        else:
            return jsonify({'success': False, 'error': 'Unknown file type'})

        return jsonify({'success': True, 'html': html})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print('''
    ╔════════════════════════════════════════════════════════════╗
    ║       Claude Code Log Visualizer Web Server               ║
    ╠════════════════════════════════════════════════════════════╣
    ║  Open your browser and go to:                              ║
    ║  http://localhost:5000                                      ║
    ╠════════════════════════════════════════════════════════════╣
    ║  Features:                                                 ║
    ║  - Drag & drop JSONL files                                 ║
    ║  - Quick access to common files                            ║
    ║  - Live preview in browser                                 ║
    ║  - Download generated HTML                                 ║
    ╚════════════════════════════════════════════════════════════╝
    ''')
    app.run(host='127.0.0.1', port=5000, debug=False)
