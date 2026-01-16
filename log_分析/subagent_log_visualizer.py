#!/usr/bin/env python3
"""
Claude Code Subagent Log Visualizer

Parses Claude Code subagent JSONL log files and generates interactive HTML reports.
"""

import json
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SubagentLogParser:
    """Parser for Claude Code subagent JSONL log files."""

    def __init__(self, jsonl_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.events: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.user_query: str = ""

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
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse line: {e}", file=sys.stderr)

        return {
            'metadata': self._extract_metadata(),
            'user_query': self._extract_user_query(),
            'event_chain': self._build_event_chain(),
            'tool_groups': self._group_by_tool(),
            'timeline': self._build_timeline(),
            'statistics': self._build_statistics()
        }

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from events."""
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
        """Extract the first user message as the query."""
        for event in self.events:
            if event.get('type') == 'user':
                message = event.get('message', {})
                content = message.get('content', '')
                if isinstance(content, list):
                    # Extract text from content blocks
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            texts.append(block.get('text', ''))
                    return '\n'.join(texts)
                return str(content)
        return "No user query found"

    def _build_event_chain(self) -> List[Dict[str, Any]]:
        """Build a simplified chain of events."""
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
        """Group events by tool type."""
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
        """Build a timeline view of all events."""
        timeline = []
        for i, event in enumerate(self.events):
            timestamp = event.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = timestamp

            timeline.append({
                'index': i + 1,
                'type': event.get('type', 'unknown'),
                'time': time_str,
                'timestamp': timestamp,
                'summary': self._get_event_summary(event),
                'raw': event
            })
        return timeline

    def _get_event_summary(self, event: Dict[str, Any]) -> str:
        """Get a one-line summary of an event."""
        event_type = event.get('type', '')

        if event_type == 'user':
            message = event.get('message', {})
            content = message.get('content', '')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text = block.get('text', '')
                        return text[:100] + '...' if len(text) > 100 else text
            return str(content)[:100] + '...' if len(str(content)) > 100 else str(content)

        elif event_type == 'assistant':
            message = event.get('message', {})
            content = message.get('content', [])
            if isinstance(content, list):
                tool_uses = [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_use']
                texts = [b for b in content if isinstance(b, dict) and b.get('type') == 'text']

                parts = []
                if tool_uses:
                    parts.append(f"Called: {', '.join(t.get('name', '?') for t in tool_uses)}")
                if texts:
                    for t in texts:
                        text = t.get('text', '')
                        if text.strip():
                            parts.append(text[:100] + '...' if len(text) > 100 else text)
                return ' | '.join(parts) if parts else 'Assistant response'
            return str(content)[:100]

        elif event_type == 'progress':
            message = event.get('message', {})
            content = message.get('content', '')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        return block.get('text', '')[:100]
            return str(content)[:100]

        return f'{event_type} event'

    def _build_statistics(self) -> Dict[str, Any]:
        """Build statistics about the log."""
        stats = {
            'total_events': len(self.events),
            'by_type': {},
            'tool_calls': 0,
            'by_tool': {}
        }

        for event in self.events:
            event_type = event.get('type', 'unknown')
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1

            if event_type == 'assistant':
                message = event.get('message', {})
                content = message.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            stats['tool_calls'] += 1
                            tool_name = block.get('name', 'Unknown')
                            stats['by_tool'][tool_name] = stats['by_tool'].get(tool_name, 0) + 1

        return stats


class HTMLGenerator:
    """Generate HTML visualization from parsed log data."""

    def __init__(self, parsed_data: Dict[str, Any]):
        self.data = parsed_data
        self.metadata = parsed_data.get('metadata', {})
        self.user_query = parsed_data.get('user_query', '')
        self.event_chain = parsed_data.get('event_chain', [])
        self.tool_groups = parsed_data.get('tool_groups', {})
        self.timeline = parsed_data.get('timeline', [])
        self.statistics = parsed_data.get('statistics', {})

    def generate(self, output_path: str) -> str:
        """Generate the HTML file."""
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subagent Log Viewer - {self.metadata.get('file_name', 'log')}</title>
    <style>
{self._generate_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Subagent Log Viewer</h1>
            <div class="meta-cards">
                <div class="meta-card">
                    <span class="meta-label">File</span>
                    <span class="meta-value">{self.metadata.get('file_name', 'Unknown')}</span>
                </div>
                <div class="meta-card">
                    <span class="meta-label">Total Events</span>
                    <span class="meta-value">{self.statistics.get('total_events', 0)}</span>
                </div>
                <div class="meta-card">
                    <span class="meta-label">Tool Calls</span>
                    <span class="meta-value">{self.statistics.get('tool_calls', 0)}</span>
                </div>
                <div class="meta-card">
                    <span class="meta-label">Agent ID</span>
                    <span class="meta-value small">{self.metadata.get('agent_id', 'Unknown')[:12]}...</span>
                </div>
            </div>
            <div class="controls">
                <button onclick="expandAll()">Expand All</button>
                <button onclick="collapseAll()">Collapse All</button>
            </div>
        </header>
{self._generate_html_body()}
    </div>
    <script>
{self._generate_javascript()}
    </script>
</body>
</html>'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path

    def _generate_css(self) -> str:
        """Generate CSS styles."""
        return '''        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e0e0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            color: #333;
        }

        h1 {
            font-size: 28px;
            margin-bottom: 16px;
            color: #1a1a2e;
        }

        .meta-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }

        .meta-card {
            background: #f5f5f5;
            padding: 12px 16px;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
        }

        .meta-label {
            font-size: 11px;
            text-transform: uppercase;
            color: #666;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .meta-value {
            font-size: 14px;
            font-weight: 600;
            color: #1a1a2e;
        }

        .meta-value.small {
            font-size: 12px;
            font-family: monospace;
        }

        .controls {
            display: flex;
            gap: 10px;
        }

        .controls button {
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }

        .controls button:hover {
            background: #f0f0f0;
            border-color: #ccc;
        }

        .section {
            background: white;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .section-header {
            padding: 16px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
        }

        .section-header:hover {
            background: #e9ecef;
        }

        .section-header h2 {
            font-size: 18px;
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .section-header .toggle-icon {
            font-size: 12px;
            transition: transform 0.3s ease;
        }

        .section.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }

        .section-content {
            padding: 20px;
        }

        .section.collapsed .section-content {
            display: none;
        }

        .user-query-box {
            background: #f0f7ff;
            border-left: 4px solid #2196F3;
            padding: 16px;
            border-radius: 6px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 14px;
            white-space: pre-wrap;
            word-break: break-word;
            margin-bottom: 16px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
        }

        .stat-card {
            background: #f8f9fa;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #1a1a2e;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }

        /* Timeline Styles */
        .timeline {
            position: relative;
            padding-left: 30px;
        }

        .timeline::before {
            content: '';
            position: absolute;
            left: 10px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: linear-gradient(to bottom, #2196F3, #4CAF50, #FF9800);
        }

        .timeline-item {
            position: relative;
            margin-bottom: 16px;
            padding-left: 20px;
        }

        .timeline-dot {
            position: absolute;
            left: -19px;
            top: 4px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 0 2px #ddd;
        }

        .timeline-item.type-user .timeline-dot {
            background: #4CAF50;
            box-shadow: 0 0 0 2px #4CAF50;
        }

        .timeline-item.type-assistant .timeline-dot {
            background: #2196F3;
            box-shadow: 0 0 0 2px #2196F3;
        }

        .timeline-item.type-progress .timeline-dot {
            background: #FF9800;
            box-shadow: 0 0 0 2px #FF9800;
        }

        .timeline-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }

        .timeline-time {
            font-family: monospace;
            font-size: 12px;
            color: #999;
        }

        .timeline-type {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .type-user .timeline-type {
            background: #e8f5e9;
            color: #2e7d32;
        }

        .type-assistant .timeline-type {
            background: #e3f2fd;
            color: #1565c0;
        }

        .type-progress .timeline-type {
            background: #fff3e0;
            color: #e65100;
        }

        .timeline-summary {
            color: #555;
            font-size: 14px;
            line-height: 1.4;
        }

        .timeline-details {
            margin-top: 10px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-word;
            display: none;
        }

        .timeline-item.expanded .timeline-details {
            display: block;
        }

        .timeline-expand {
            color: #2196F3;
            cursor: pointer;
            font-size: 12px;
            margin-top: 6px;
        }

        .timeline-expand:hover {
            text-decoration: underline;
        }

        /* Tool Groups */
        .tool-group {
            margin-bottom: 16px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }

        .tool-group-header {
            padding: 12px 16px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .tool-group-header:hover {
            background: #e9ecef;
        }

        .tool-name {
            font-weight: 600;
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .tool-count {
            background: #2196F3;
            color: white;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }

        .tool-calls {
            display: none;
            padding: 12px;
        }

        .tool-group.expanded .tool-calls {
            display: block;
        }

        .tool-call {
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            margin-bottom: 8px;
            font-family: monospace;
            font-size: 12px;
        }

        .tool-call-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: #666;
            font-size: 11px;
        }

        .tool-call-input {
            background: white;
            padding: 10px;
            border-radius: 4px;
            white-space: pre-wrap;
            word-break: break-word;
        }

        /* Event List */
        .event-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .event-item {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }

        .event-header {
            padding: 12px 16px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .event-header:hover {
            background: #e9ecef;
        }

        .event-index {
            background: #6c757d;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            min-width: 40px;
            text-align: center;
        }

        .event-item.type-user .event-index {
            background: #4CAF50;
        }

        .event-item.type-assistant .event-index {
            background: #2196F3;
        }

        .event-item.type-progress .event-index {
            background: #FF9800;
        }

        .event-info {
            flex: 1;
        }

        .event-timestamp {
            font-size: 11px;
            color: #999;
        }

        .event-type {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .event-json {
            display: none;
            padding: 16px;
            background: #1a1a2e;
            color: #a0a0a0;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-word;
            overflow-x: auto;
        }

        .event-item.expanded .event-json {
            display: block;
        }

        /* Collapsible states */
        .collapsed .section-content {
            display: none;
        }

        /* Type colors */
        .type-user { color: #4CAF50; }
        .type-assistant { color: #2196F3; }
        .type-progress { color: #FF9800; }
'''

    def _generate_html_body(self) -> str:
        """Generate the main HTML body content."""
        parts = []

        # Task Overview Section
        parts.append(self._generate_task_overview())

        # Timeline Section
        parts.append(self._generate_timeline_section())

        # Tool Groups Section
        parts.append(self._generate_tool_groups_section())

        # Detailed Event Log Section
        parts.append(self._generate_event_log_section())

        return '\n'.join(parts)

    def _generate_task_overview(self) -> str:
        """Generate the task overview section."""
        stats = self.statistics
        by_type = stats.get('by_type', {})

        return f'''        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▼</span> Task Overview</h2>
            </div>
            <div class="section-content">
                <h3 style="font-size: 14px; margin-bottom: 10px; color: #666;">User Query</h3>
                <div class="user-query-box">{self._html_escape(self.user_query)}</div>
                <h3 style="font-size: 14px; margin-bottom: 10px; color: #666;">Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats.get('total_events', 0)}</div>
                        <div class="stat-label">Total Events</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats.get('tool_calls', 0)}</div>
                        <div class="stat-label">Tool Calls</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{by_type.get('user', 0)}</div>
                        <div class="stat-label">User Events</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{by_type.get('assistant', 0)}</div>
                        <div class="stat-label">Assistant Events</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{by_type.get('progress', 0)}</div>
                        <div class="stat-label">Progress Events</div>
                    </div>
                </div>
            </div>
        </div>'''

    def _generate_timeline_section(self) -> str:
        """Generate the timeline section."""
        timeline_items = []
        for item in self.timeline:
            event_type = item.get('type', 'unknown')
            timeline_items.append(f'''                <div class="timeline-item type-{event_type}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-header">
                        <span class="timeline-time">{self._html_escape(item.get('time', ''))}</span>
                        <span class="timeline-type">{event_type}</span>
                    </div>
                    <div class="timeline-summary">{self._html_escape(item.get('summary', ''))}</div>
                    <div class="timeline-expand" onclick="this.parentElement.classList.toggle('expanded')">
                        Show details
                    </div>
                    <div class="timeline-details">{self._html_escape(json.dumps(item.get('raw'), indent=2, ensure_ascii=False))}</div>
                </div>''')

        return f'''        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▼</span> Timeline View</h2>
            </div>
            <div class="section-content">
                <div class="timeline">
{chr(10).join(timeline_items)}
                </div>
            </div>
        </div>'''

    def _generate_tool_groups_section(self) -> str:
        """Generate the tool groups section (collapsed by default)."""
        tool_groups = []
        for tool_name, calls in sorted(self.tool_groups.items()):
            calls_html = []
            for call in calls:
                calls_html.append(f'''                    <div class="tool-call">
                        <div class="tool-call-header">
                            <span>#{call.get('index', '?')}</span>
                            <span>{call.get('timestamp', '')}</span>
                        </div>
                        <div class="tool-call-input">{self._html_escape(json.dumps(call.get('input', {}), indent=2, ensure_ascii=False))}</div>
                    </div>''')

            tool_groups.append(f'''            <div class="tool-group">
                <div class="tool-group-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span class="tool-name">{self._html_escape(tool_name)}</span>
                    <span class="tool-count">{len(calls)}</span>
                </div>
                <div class="tool-calls">
{chr(10).join(calls_html)}
                </div>
            </div>''')

        return f'''        <div class="section collapsed">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▶</span> Tool Calls Grouped</h2>
            </div>
            <div class="section-content">
{chr(10).join(tool_groups) if tool_groups else '<p style="color: #999;">No tool calls found</p>'}
            </div>
        </div>'''

    def _generate_event_log_section(self) -> str:
        """Generate the detailed event log section (collapsed by default)."""
        events = []
        for event in self.event_chain:
            event_type = event.get('type', 'unknown')
            events.append(f'''            <div class="event-item type-{event_type}">
                <div class="event-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span class="event-index">#{event.get('index', '?')}</span>
                    <span class="event-info">
                        <span class="event-type">{event_type}</span>
                        <span class="event-timestamp">{event.get('timestamp', '')}</span>
                    </span>
                </div>
                <div class="event-json">{self._html_escape(json.dumps(event.get('raw'), indent=2, ensure_ascii=False))}</div>
            </div>''')

        return f'''        <div class="section collapsed">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▶</span> Detailed Event Log</h2>
            </div>
            <div class="section-content">
                <div class="event-list">
{chr(10).join(events)}
                </div>
            </div>
        </div>'''

    def _generate_javascript(self) -> str:
        """Generate JavaScript for interactivity."""
        return '''        function toggleSection(header) {
            const section = header.parentElement;
            section.classList.toggle('collapsed');
            const icon = header.querySelector('.toggle-icon');
            if (section.classList.contains('collapsed')) {
                icon.textContent = '▶';
            } else {
                icon.textContent = '▼';
            }
        }

        function expandAll() {
            document.querySelectorAll('.section').forEach(section => {
                section.classList.remove('collapsed');
                const icon = section.querySelector('.toggle-icon');
                if (icon) icon.textContent = '▼';
            });
            document.querySelectorAll('.tool-group').forEach(group => {
                group.classList.add('expanded');
            });
        }

        function collapseAll() {
            document.querySelectorAll('.section').forEach(section => {
                section.classList.add('collapsed');
                const icon = section.querySelector('.toggle-icon');
                if (icon) icon.textContent = '▶';
            });
            document.querySelectorAll('.tool-group').forEach(group => {
                group.classList.remove('expanded');
            });
            document.querySelectorAll('.timeline-item, .event-item').forEach(item => {
                item.classList.remove('expanded');
            });
        }
'''

    def _html_escape(self, text: str) -> str:
        """Escape HTML special characters."""
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def main():
    parser = argparse.ArgumentParser(
        description='Visualize Claude Code subagent JSONL logs as HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python subagent_log_visualizer.py input.jsonl
  python subagent_log_visualizer.py input.jsonl -o report.html
  python subagent_log_visualizer.py input.jsonl --open
        '''
    )
    parser.add_argument('input', help='Input JSONL log file path')
    parser.add_argument('-o', '--output', help='Output HTML file path (default: input_name.html)')
    parser.add_argument('--open', action='store_true', help='Open the generated HTML in browser')

    args = parser.parse_args()

    # Determine output path
    input_path = Path(args.input)
    if args.output:
        output_path = args.output
    else:
        output_path = str(input_path.with_suffix('.html'))

    # Parse log file
    print(f"Parsing log file: {args.input}")
    log_parser = SubagentLogParser(args.input)
    parsed_data = log_parser.parse()

    print(f"  - Total events: {parsed_data['statistics']['total_events']}")
    print(f"  - Tool calls: {parsed_data['statistics']['tool_calls']}")
    print(f"  - Tools used: {', '.join(parsed_data['statistics']['by_tool'].keys())}")

    # Generate HTML
    print(f"Generating HTML report: {output_path}")
    generator = HTMLGenerator(parsed_data)
    generator.generate(output_path)

    # Open in browser if requested
    if args.open:
        import webbrowser
        file_url = f"file:///{Path(output_path).absolute()}".replace('\\', '/')
        webbrowser.open(file_url)

    print(f"Done! Report saved to: {output_path}")


if __name__ == '__main__':
    main()
