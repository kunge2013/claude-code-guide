#!/usr/bin/env python3
"""
Claude Code History Visualizer

Parses Claude Code history.jsonl log files and generates interactive HTML reports.
"""

import json
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from collections import Counter, defaultdict


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
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse line: {e}", file=sys.stderr)

        return {
            'metadata': self._extract_metadata(),
            'timeline': self._build_timeline(),
            'sessions': self._group_by_session(),
            'projects': self._group_by_project(),
            'commands': self._analyze_commands(),
            'statistics': self._build_statistics(),
            'hourly_activity': self._build_hourly_activity(),
            'daily_activity': self._build_daily_activity()
        }

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from history entries."""
        if not self.entries:
            return {}

        first = self.entries[0]
        last = self.entries[-1]

        return {
            'file_name': self.jsonl_path.name,
            'total_entries': len(self.entries),
            'unique_sessions': len(set(e.get('sessionId', '') for e in self.entries)),
            'unique_projects': len(set(e.get('project', '') for e in self.entries)),
            'first_entry': first.get('timestamp', 0),
            'last_entry': last.get('timestamp', 0),
            'time_span_days': self._calculate_time_span(first, last)
        }

    def _calculate_time_span(self, first: Dict, last: Dict) -> float:
        """Calculate time span in days."""
        try:
            first_time = first.get('timestamp', 0) / 1000
            last_time = last.get('timestamp', 0) / 1000
            return (last_time - first_time) / 86400
        except:
            return 0

    def _build_timeline(self) -> List[Dict[str, Any]]:
        """Build a chronological timeline of all entries."""
        timeline = []
        for i, entry in enumerate(self.entries):
            timestamp = entry.get('timestamp', 0)
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                hour = dt.hour
                date = dt.strftime('%Y-%m-%d')
            except:
                time_str = str(timestamp)
                hour = 0
                date = 'Unknown'

            display = entry.get('display', '')
            command_type = self._classify_command(display)

            timeline.append({
                'index': i + 1,
                'timestamp': timestamp,
                'time_str': time_str,
                'hour': hour,
                'date': date,
                'display': display,
                'project': entry.get('project', ''),
                'session_id': entry.get('sessionId', ''),
                'command_type': command_type,
                'has_pasted': bool(entry.get('pastedContents')),
                'raw': entry
            })
        return timeline

    def _classify_command(self, display: str) -> str:
        """Classify the type of command."""
        if not display:
            return 'empty'
        if display.startswith('/'):
            cmd = display.split()[0].lower()
            if cmd in ['/model', '/cost', '/context', '/clear', '/help', '/commit', '/plan']:
                return 'slash_command'
            return 'slash_command'
        return 'user_input'

    def _group_by_session(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group entries by session ID."""
        sessions = defaultdict(list)
        for entry in self.entries:
            session_id = entry.get('sessionId', 'unknown')
            sessions[session_id].append(entry)
        return dict(sessions)

    def _group_by_project(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group entries by project path."""
        projects = defaultdict(list)
        for entry in self.entries:
            project = entry.get('project', 'unknown')
            projects[project].append(entry)
        return dict(projects)

    def _analyze_commands(self) -> Dict[str, Any]:
        """Analyze command usage patterns."""
        slash_commands = []
        user_inputs = []

        for entry in self.entries:
            display = entry.get('display', '')
            if display.startswith('/'):
                cmd = display.split()[0].lower()
                slash_commands.append(cmd)
            else:
                user_inputs.append(display)

        return {
            'slash_commands': Counter(slash_commands),
            'total_slash_commands': len(slash_commands),
            'total_user_inputs': len(user_inputs),
            'most_common_commands': Counter(slash_commands).most_common(10)
        }

    def _build_statistics(self) -> Dict[str, Any]:
        """Build overall statistics."""
        project_counts = Counter(e.get('project', 'unknown') for e in self.entries)
        session_lengths = [len(entries) for entries in self._group_by_session().values()]

        return {
            'total_entries': len(self.entries),
            'total_sessions': len(self._group_by_session()),
            'total_projects': len(project_counts),
            'avg_session_length': sum(session_lengths) / len(session_lengths) if session_lengths else 0,
            'top_projects': project_counts.most_common(10)
        }

    def _build_hourly_activity(self) -> Dict[int, int]:
        """Build activity by hour of day."""
        hourly = defaultdict(int)
        for entry in self.entries:
            timestamp = entry.get('timestamp', 0)
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                hourly[dt.hour] += 1
            except:
                pass
        return dict(hourly)

    def _build_daily_activity(self) -> Dict[str, int]:
        """Build activity by date."""
        daily = defaultdict(int)
        for entry in self.entries:
            timestamp = entry.get('timestamp', 0)
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                daily[dt.strftime('%Y-%m-%d')] += 1
            except:
                pass
        return dict(daily)


class HistoryHTMLGenerator:
    """Generate HTML visualization from parsed history data."""

    def __init__(self, parsed_data: Dict[str, Any]):
        self.data = parsed_data
        self.metadata = parsed_data.get('metadata', {})
        self.timeline = parsed_data.get('timeline', [])
        self.sessions = parsed_data.get('sessions', {})
        self.projects = parsed_data.get('projects', {})
        self.commands = parsed_data.get('commands', {})
        self.statistics = parsed_data.get('statistics', {})
        self.hourly_activity = parsed_data.get('hourly_activity', {})
        self.daily_activity = parsed_data.get('daily_activity', {})

    def generate(self, output_path: str) -> str:
        """Generate the HTML file."""
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code History Viewer</title>
    <style>
{self._generate_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Claude Code History Viewer</h1>
            <div class="meta-cards">
                <div class="meta-card">
                    <span class="meta-label">Total Entries</span>
                    <span class="meta-value">{self.metadata.get('total_entries', 0):,}</span>
                </div>
                <div class="meta-card">
                    <span class="meta-label">Sessions</span>
                    <span class="meta-value">{self.metadata.get('unique_sessions', 0):,}</span>
                </div>
                <div class="meta-card">
                    <span class="meta-label">Projects</span>
                    <span class="meta-value">{self.metadata.get('unique_projects', 0):,}</span>
                </div>
                <div class="meta-card">
                    <span class="meta-label">Time Span</span>
                    <span class="meta-value">{self.metadata.get('time_span_days', 0):.1f} days</span>
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
            background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e0e0;
        }

        .container {
            max-width: 1400px;
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
            color: #1e3a5f;
        }

        .meta-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }

        .meta-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 16px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            border: 1px solid #dee2e6;
        }

        .meta-label {
            font-size: 11px;
            text-transform: uppercase;
            color: #6c757d;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .meta-value {
            font-size: 22px;
            font-weight: 700;
            color: #1e3a5f;
        }

        .controls {
            display: flex;
            gap: 10px;
        }

        .controls button {
            padding: 10px 20px;
            border: 1px solid #dee2e6;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
            color: #495057;
        }

        .controls button:hover {
            background: #e9ecef;
            border-color: #adb5bd;
        }

        .section {
            background: white;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .section-header {
            padding: 18px 24px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-bottom: 1px solid #dee2e6;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
        }

        .section-header:hover {
            background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
        }

        .section-header h2 {
            font-size: 18px;
            color: #1e3a5f;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .section-header .toggle-icon {
            font-size: 14px;
            transition: transform 0.3s ease;
            color: #6c757d;
        }

        .section.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }

        .section-content {
            padding: 24px;
        }

        .section.collapsed .section-content {
            display: none;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            color: white;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .stat-label {
            font-size: 13px;
            opacity: 0.9;
        }

        /* Command Stats */
        .command-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .command-list {
            background: #f8f9fa;
            border-radius: 10px;
            overflow: hidden;
        }

        .command-list h3 {
            padding: 14px 18px;
            background: #1e3a5f;
            color: white;
            font-size: 15px;
        }

        .command-item {
            padding: 12px 18px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .command-item:last-child {
            border-bottom: none;
        }

        .command-name {
            font-family: 'Consolas', monospace;
            font-size: 13px;
            color: #495057;
        }

        .command-count {
            background: #1e3a5f;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Timeline */
        .timeline {
            position: relative;
        }

        .timeline-item {
            padding: 14px 18px;
            border-left: 3px solid #e9ecef;
            margin-left: 8px;
            position: relative;
            cursor: pointer;
            transition: all 0.2s;
        }

        .timeline-item:hover {
            background: #f8f9fa;
        }

        .timeline-item::before {
            content: '';
            position: absolute;
            left: -6px;
            top: 18px;
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: #6c757d;
            border: 2px solid white;
        }

        .timeline-item.type-slash_command::before {
            background: #17a2b8;
        }

        .timeline-item.type-user_input::before {
            background: #28a745;
        }

        .timeline-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .timeline-time {
            font-family: monospace;
            font-size: 12px;
            color: #6c757d;
        }

        .timeline-type {
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .type-slash_command .timeline-type {
            background: #e0f7fa;
            color: #006064;
        }

        .type-user_input .timeline-type {
            background: #e8f5e9;
            color: #1b5e20;
        }

        .timeline-display {
            color: #212529;
            font-size: 14px;
            font-family: 'Consolas', 'Monaco', monospace;
            word-break: break-word;
            line-height: 1.4;
        }

        .timeline-meta {
            display: flex;
            gap: 16px;
            margin-top: 8px;
            font-size: 11px;
            color: #6c757d;
        }

        .timeline-project {
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Project List */
        .project-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .project-item {
            background: #f8f9fa;
            padding: 16px;
            border-radius: 8px;
            cursor: pointer;
        }

        .project-item:hover {
            background: #e9ecef;
        }

        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .project-path {
            font-family: 'Consolas', monospace;
            font-size: 13px;
            color: #212529;
        }

        .project-count {
            background: #1e3a5f;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Activity Chart */
        .activity-chart {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }

        .chart-title {
            font-size: 14px;
            font-weight: 600;
            color: #495057;
            margin-bottom: 16px;
        }

        .chart-bars {
            display: flex;
            align-items: flex-end;
            gap: 4px;
            height: 150px;
        }

        .chart-bar {
            flex: 1;
            background: linear-gradient(to top, #1e3a5f, #2d5a87);
            border-radius: 4px 4px 0 0;
            min-height: 4px;
            transition: all 0.2s;
            cursor: pointer;
            position: relative;
        }

        .chart-bar:hover {
            background: linear-gradient(to top, #2d5a87, #4a7ba7);
        }

        .chart-bar-label {
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10px;
            color: #6c757d;
        }

        /* Detail Panel */
        .detail-panel {
            display: none;
            padding: 16px;
            background: #1e3a5f;
            color: #e0e0e0;
            border-radius: 8px;
            margin-top: 12px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 300px;
            overflow-y: auto;
        }

        .timeline-item.expanded .detail-panel {
            display: block;
        }

        .show-details {
            color: #1e3a5f;
            cursor: pointer;
            font-size: 12px;
            margin-top: 8px;
        }

        .show-details:hover {
            text-decoration: underline;
        }
'''

    def _generate_html_body(self) -> str:
        """Generate the main HTML body content."""
        parts = []

        # Statistics Section
        parts.append(self._generate_statistics_section())

        # Commands Section
        parts.append(self._generate_commands_section())

        # Activity Section
        parts.append(self._generate_activity_section())

        # Projects Section
        parts.append(self._generate_projects_section())

        # Timeline Section
        parts.append(self._generate_timeline_section())

        return '\n'.join(parts)

    def _generate_statistics_section(self) -> str:
        """Generate the statistics overview section."""
        stats = self.statistics
        commands = self.commands

        return f'''        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▼</span> Overview Statistics</h2>
            </div>
            <div class="section-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats.get('total_entries', 0):,}</div>
                        <div class="stat-label">Total Entries</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats.get('total_sessions', 0):,}</div>
                        <div class="stat-label">Total Sessions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats.get('total_projects', 0):,}</div>
                        <div class="stat-label">Total Projects</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats.get('avg_session_length', 0):.1f}</div>
                        <div class="stat-label">Avg Session Length</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{commands.get('total_slash_commands', 0):,}</div>
                        <div class="stat-label">Slash Commands</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{commands.get('total_user_inputs', 0):,}</div>
                        <div class="stat-label">User Inputs</div>
                    </div>
                </div>
            </div>
        </div>'''

    def _generate_commands_section(self) -> str:
        """Generate the commands analysis section."""
        most_common = self.commands.get('most_common_commands', [])

        commands_html = []
        for cmd, count in most_common:
            commands_html.append(f'''                    <div class="command-item">
                        <span class="command-name">{self._html_escape(cmd)}</span>
                        <span class="command-count">{count}</span>
                    </div>''')

        return f'''        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▼</span> Command Usage</h2>
            </div>
            <div class="section-content">
                <div class="command-stats">
                    <div class="command-list">
                        <h3>Most Used Commands</h3>
{chr(10).join(commands_html) if commands_html else '<p style="padding: 18px; color: #6c757d;">No commands found</p>'}
                    </div>
                </div>
            </div>
        </div>'''

    def _generate_activity_section(self) -> str:
        """Generate the activity charts section."""
        # Hourly chart
        hourly_bars = []
        max_hourly = max(self.hourly_activity.values()) if self.hourly_activity else 1
        for hour in range(24):
            count = self.hourly_activity.get(hour, 0)
            height = (count / max_hourly * 100) if max_hourly > 0 else 0
            hourly_bars.append(f'''                    <div class="chart-bar" style="height: {max(height, 2)}%;" title="{hour}:00 - {count} entries">
                        <span class="chart-bar-label">{hour}</span>
                    </div>''')

        return f'''        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▼</span> Activity Patterns</h2>
            </div>
            <div class="section-content">
                <div class="activity-chart">
                    <div class="chart-title">Activity by Hour of Day</div>
                    <div class="chart-bars">
{chr(10).join(hourly_bars)}
                    </div>
                </div>
            </div>
        </div>'''

    def _generate_projects_section(self) -> str:
        """Generate the projects section (collapsed by default)."""
        top_projects = self.statistics.get('top_projects', [])

        projects_html = []
        for project, count in top_projects:
            projects_html.append(f'''                <div class="project-item">
                    <div class="project-header">
                        <span class="project-path" title="{self._html_escape(project)}">{self._html_escape(project[:80])}...</span>
                        <span class="project-count">{count}</span>
                    </div>
                </div>''')

        return f'''        <div class="section collapsed">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▶</span> Top Projects</h2>
            </div>
            <div class="section-content">
                <div class="project-list">
{chr(10).join(projects_html) if projects_html else '<p style="color: #6c757d;">No projects found</p>'}
                </div>
            </div>
        </div>'''

    def _generate_timeline_section(self) -> str:
        """Generate the timeline section (collapsed by default)."""
        # Show last 100 entries to avoid huge HTML
        recent_timeline = self.timeline[-100:]

        timeline_items = []
        for item in reversed(recent_timeline):
            cmd_type = item.get('command_type', 'user_input')
            timeline_items.append(f'''                <div class="timeline-item type-{cmd_type}" onclick="this.classList.toggle('expanded')">
                    <div class="timeline-header">
                        <span class="timeline-time">{self._html_escape(item.get('time_str', ''))}</span>
                        <span class="timeline-type">{cmd_type}</span>
                    </div>
                    <div class="timeline-display">{self._html_escape(item.get('display', ''))}</div>
                    <div class="timeline-meta">
                        <span class="timeline-project" title="{self._html_escape(item.get('project', ''))}">{self._html_escape(item.get('project', '')[:60])}...</span>
                    </div>
                    <div class="show-details">Show details</div>
                    <div class="detail-panel">{self._html_escape(json.dumps(item.get('raw'), indent=2, ensure_ascii=False))}</div>
                </div>''')

        return f'''        <div class="section collapsed">
            <div class="section-header" onclick="toggleSection(this)">
                <h2><span class="toggle-icon">▶</span> Timeline (Last 100 Entries)</h2>
            </div>
            <div class="section-content">
                <div class="timeline">
{chr(10).join(timeline_items)}
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
        }

        function collapseAll() {
            document.querySelectorAll('.section').forEach(section => {
                section.classList.add('collapsed');
                const icon = section.querySelector('.toggle-icon');
                if (icon) icon.textContent = '▶';
            });
            document.querySelectorAll('.timeline-item').forEach(item => {
                item.classList.remove('expanded');
            });
        }
'''

    def _html_escape(self, text: str) -> str:
        """Escape HTML special characters."""
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def main():
    parser = argparse.ArgumentParser(
        description='Visualize Claude Code history.jsonl as HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python history_visualizer.py history.jsonl
  python history_visualizer.py history.jsonl -o report.html
  python history_visualizer.py history.jsonl --open
        '''
    )
    parser.add_argument('input', help='Input history.jsonl file path')
    parser.add_argument('-o', '--output', help='Output HTML file path (default: input_name.html)')
    parser.add_argument('--open', action='store_true', help='Open the generated HTML in browser')

    args = parser.parse_args()

    # Determine output path
    input_path = Path(args.input)
    if args.output:
        output_path = args.output
    else:
        output_path = str(input_path.with_suffix('.html'))

    # Parse history file
    print(f"Parsing history file: {args.input}")
    log_parser = HistoryParser(args.input)
    parsed_data = log_parser.parse()

    print(f"  - Total entries: {parsed_data['statistics']['total_entries']}")
    print(f"  - Total sessions: {parsed_data['statistics']['total_sessions']}")
    print(f"  - Total projects: {parsed_data['statistics']['total_projects']}")
    print(f"  - Time span: {parsed_data['metadata']['time_span_days']:.1f} days")

    # Generate HTML
    print(f"Generating HTML report: {output_path}")
    generator = HistoryHTMLGenerator(parsed_data)
    generator.generate(output_path)

    # Open in browser if requested
    if args.open:
        import webbrowser
        file_url = f"file:///{Path(output_path).absolute()}".replace('\\', '/')
        webbrowser.open(file_url)

    print(f"Done! Report saved to: {output_path}")


if __name__ == '__main__':
    main()
