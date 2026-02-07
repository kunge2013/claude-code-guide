// SQL Query Tool - JavaScript

// Date/time column names that should be formatted
const DATE_COLUMNS = [
    'BEGIN_DATE', 'INPUT_DATE', 'MOD_DATE', 'AUD_DATE',
    'START_DATE', 'END_DATE', 'STOP_RENT_DATE', 'BEGIN_RENT_CD',
    'STOP_RENT_CD', 'CREATE_DATE', 'UPDATE_DATE', 'OPER_TIME',
    'CREATE_TIME', 'UPDATE_TIME', 'MOD_TIME'
];

// Color palette for ACCT_ITEM_TYPE_ID groups - golden yellow base with distinguishable variations
const COLOR_PALETTE = [
    '#fef3c7', // Golden yellow (primary)
    '#ffedd5', // Light orange
    '#fef9c3', // Light yellow
    '#fce7f3', // Light pink
    '#e0f2fe', // Light blue
    '#dcfce7', // Light green
    '#f3e8ff', // Light purple
    '#fee2e2', // Light red
    '#ecfccb', // Lime
    '#cffafe', // Cyan
    '#ffe4e6', // Rose
    '#fef08a', // Yellow
    '#fed7aa', // Orange
    '#ddd6fe', // Violet
    '#bbf7d0', // Green
    '#a5f3fc', // Sky
    '#fbcfe8', // Pink
    '#e9d5ff', // Purple
    '#fdde6d', // Gold
    '#fcd34d'  // Amber
];

// Get color for ACCT_ITEM_TYPE_ID
function getColorForAcctItemTypeId(id) {
    // Use a better hash function with prime multiplier for better distribution
    let hash = 0;
    const str = String(id);
    for (let i = 0; i < str.length; i++) {
        hash = (hash * 31 + str.charCodeAt(i)) & 0xFFFFFFFF; // Prime multiplier 31
    }
    const index = Math.abs(hash) % COLOR_PALETTE.length;
    return COLOR_PALETTE[index];
}

// Format datetime to YYYY-MM-DD HH:MM:SS
function formatDateTime(value) {
    if (!value) return value;

    // If it's already a string in the right format, return as is
    if (typeof value === 'string') {
        // Check if it matches datetime pattern with space or colon separator
        const dateMatch = value.match(/(\d{4})-(\d{2})-(\d{2})(?:\s|T)(\d{2}):(\d{2}):(\d{2})/);
        if (dateMatch) {
            const [, year, month, day, hour, minute, second] = dateMatch;
            return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
        }
        return value;
    }

    // Handle Date object
    if (value instanceof Date) {
        const year = value.getFullYear();
        const month = String(value.getMonth() + 1).padStart(2, '0');
        const day = String(value.getDate()).padStart(2, '0');
        const hour = String(value.getHours()).padStart(2, '0');
        const minute = String(value.getMinutes()).padStart(2, '0');
        const second = String(value.getSeconds()).padStart(2, '0');
        return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
    }

    return value;
}

// SQL Syntax Highlighting
function highlightSQL(sql) {
    if (!sql) return '';

    // Escape HTML first
    let escaped = sql
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // SQL Keywords
    const keywords = ['UPDATE', 'SET', 'WHERE', 'AND', 'OR', 'NOT', 'NULL', 'IS', 'IN', 'LIKE', 'BETWEEN', 'SELECT', 'FROM', 'INSERT', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'INDEX', 'VIEW', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET'];
    const keywordPattern = new RegExp('\\b(' + keywords.join('|') + ')\\b', 'gi');

    // Comments (-- to end of line)
    const commentPattern = /(--[^\n]*)/g;

    // Strings (single and double quoted)
    const stringPattern = /('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")/g;

    // Numbers
    const numberPattern = /\b\d+(\.\d+)?\b/g;

    // Table names (after common SQL keywords)
    const tablePattern = /\b(FROM|JOIN|UPDATE|INSERT|INTO|DELETE\s+FROM)\s+([a-zA-Z_][a-zA-Z0-9_]*)/gi;

    let result = escaped;
    let processed = new Set();

    // Process comments first (to avoid highlighting inside them)
    result = result.replace(commentPattern, '<span class="sql-comment">$1</span>');

    // Process strings (to avoid highlighting inside them)
    result = result.replace(stringPattern, (match) => {
        return `<span class="sql-string">${match}</span>`;
    });

    // Process keywords (only if not inside a span)
    result = result.replace(keywordPattern, (match) => {
        return `<span class="sql-keyword">${match}</span>`;
    });

    // Process table names
    result = result.replace(/<span class="sql-keyword">(FROM|JOIN|UPDATE|INTO)<\/span>\s+([a-zA-Z_][a-zA-Z0-9_]*)/gi, '$1 <span class="sql-table">$2</span>');

    return result;
}

// Check if a column name is a date column
function isDateColumn(columnName) {
    const upperName = columnName.toUpperCase();
    return DATE_COLUMNS.some(col => upperName.includes(col)) ||
           upperName.includes('DATE') ||
           upperName.includes('TIME') ||
           upperName.endsWith('_TIME') ||
           upperName.endsWith('_DATE');
}

class SQLQueryTool {
    constructor() {
        this.apiUrl = '/api';
        this.currentConfig = {};
        this.acctTypeColorMap = new Map(); // Track colors assigned to each ACCT_ITEM_TYPE_ID
        this.invalidGroups = new Map(); // Track invalid groups with their assigned color
        this.currentFilter = null; // Current filter state (groupKey or null)
        this.changeRecordData = []; // Store change record data for SQL generation
        this.contextMenuTarget = null; // Track which row triggered the context menu
        this.changeLogData = []; // Store change log data for filtering
        this.currentViolationData = null; // Store current violation data for LLM SQL generation
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadConfig();
    }

    getColorForAcctType(acctTypeId) {
        // Return existing color if already assigned
        if (this.acctTypeColorMap.has(acctTypeId)) {
            return this.acctTypeColorMap.get(acctTypeId);
        }

        // Assign a new color using sequential distribution
        const nextIndex = this.acctTypeColorMap.size % COLOR_PALETTE.length;
        const color = COLOR_PALETTE[nextIndex];
        this.acctTypeColorMap.set(acctTypeId, color);
        return color;
    }

    resetColorMap() {
        // Reset color map for new query
        this.acctTypeColorMap.clear();
        this.invalidGroups.clear();
        this.currentFilter = null;
    }

    bindEvents() {
        // Query buttons
        document.getElementById('queryAllBtn').addEventListener('click', () => this.runAllQueries());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearResults());

        // Enter key in input field
        document.getElementById('prodInstId').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.runAllQueries();
            }
        });

        // Configuration modal
        document.getElementById('configBtn').addEventListener('click', () => this.openConfigModal());
        document.getElementById('closeModal').addEventListener('click', () => this.closeConfigModal());
        document.getElementById('cancelConfigBtn').addEventListener('click', () => this.closeConfigModal());

        // Test connection
        document.getElementById('testConnBtn').addEventListener('click', () => this.testConnection());

        // Save configuration
        document.getElementById('saveConfigBtn').addEventListener('click', () => this.saveConfig());

        // Close modal on outside click
        document.getElementById('configModal').addEventListener('click', (e) => {
            if (e.target.id === 'configModal') {
                this.closeConfigModal();
            }
        });

        // Copy SQL buttons
        document.querySelectorAll('.copy-sql-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = e.target.dataset.type;
                this.copySql(type);
            });
        });

        // SQL Fix modal
        document.getElementById('closeSqlModal').addEventListener('click', () => this.closeSqlFixModal());
        document.getElementById('closeSqlModalBtn').addEventListener('click', () => this.closeSqlFixModal());
        document.getElementById('maximizeSqlModal').addEventListener('click', () => this.toggleMaximizeSqlModal());
        document.getElementById('copySqlBtn').addEventListener('click', () => this.copyFixSql());

        // LLM SQL generation
        document.getElementById('generateLlmSqlBtn').addEventListener('click', () => this.generateLlmSql());
        document.getElementById('copyLlmSqlBtn').addEventListener('click', () => this.copyLlmSql());

        // Close SQL modal on outside click
        document.getElementById('sqlFixModal').addEventListener('click', (e) => {
            if (e.target.id === 'sqlFixModal') {
                this.closeSqlFixModal();
            }
        });

        // Context menu
        document.getElementById('generateSqlMenuItem').addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent document click handler from firing
            if (this.contextMenuTarget) {
                const groupKey = this.contextMenuTarget.dataset.groupKey;
                const color = this.contextMenuTarget.dataset.invalidColor;
                this.hideContextMenu();
                this.showSqlFixModal(groupKey, color);
            }
        });

        // Hide context menu on click elsewhere (use mousedown to catch before menu item click)
        document.addEventListener('mousedown', (e) => {
            const contextMenu = document.getElementById('contextMenu');
            if (contextMenu.style.display === 'block' && !contextMenu.contains(e.target)) {
                this.hideContextMenu();
            }
        });

        // ATTR_NAME filter for Change Log
        document.getElementById('attrNameFilter').addEventListener('change', (e) => {
            const trimmedValue = e.target.value.trim();
            e.target.value = trimmedValue; // Update input with trimmed value
            this.filterChangeLog(trimmedValue);
        });

        // Allow Enter key to trigger filter
        document.getElementById('attrNameFilter').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const trimmedValue = e.target.value.trim();
                e.target.value = trimmedValue;
                this.filterChangeLog(trimmedValue);
            }
        });

        // Drawer toggle
        document.getElementById('drawerToggle').addEventListener('click', () => this.toggleDrawer());
        document.getElementById('closeDrawer').addEventListener('click', () => this.closeDrawer());
    }

    setStatus(message, type = '') {
        const statusEl = document.getElementById('statusText');
        statusEl.textContent = message;
        statusEl.className = type;
    }

    getProdInstId() {
        return document.getElementById('prodInstId').value.trim();
    }

    async runAllQueries() {
        const prodInstId = this.getProdInstId();
        if (!prodInstId) {
            this.setStatus('Please enter a PROD_INST_ID', 'error');
            return;
        }

        this.setStatus('Running queries...');
        this.setLoading(true);

        // Reset color map for new query
        this.resetColorMap();

        try {
            const response = await fetch(`${this.apiUrl}/query/all`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prod_inst_id: prodInstId })
            });

            const result = await response.json();

            if (result.success) {
                // Get validation data for change-record
                const validationData = result.validation || null;

                // Store change record data for SQL generation
                this.changeRecordData = result.data.change_record || [];

                // Store change log data for filtering
                this.changeLogData = result.data.change_log || [];

                // Display results and SQL in two columns + drawer
                this.displayResults('instance-info', result.data.instance_info, result.sql.instance_info);
                this.displayResults('change-log', result.data.change_log, result.sql.change_log);
                this.displayResults('change-record', result.data.change_record, result.sql.change_record, validationData);

                const totalRows = result.counts.instance_info + result.counts.change_log + result.counts.change_record;
                let statusMsg = `Queries completed: ${totalRows} total rows`;
                if (validationData && validationData.invalid_groups.length > 0) {
                    statusMsg += ` | ${validationData.summary}`;
                }
                this.setStatus(statusMsg, 'success');
            } else {
                this.setStatus(`Error: ${result.message}`, 'error');
            }
        } catch (error) {
            this.setStatus(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    }

    async querySingle(type) {
        const prodInstId = this.getProdInstId();
        if (!prodInstId) {
            this.setStatus('Please enter a PROD_INST_ID', 'error');
            return;
        }

        this.setStatus(`Querying ${type}...`);
        this.setLoading(true);

        try {
            const response = await fetch(`${this.apiUrl}/query/${type}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prod_inst_id: prodInstId })
            });

            const result = await response.json();

            if (result.success) {
                this.displayResults(type, result.data);
                this.setStatus(`Query completed: ${result.count} rows`, 'success');
            } else {
                this.setStatus(`Error: ${result.message}`, 'error');
            }
        } catch (error) {
            this.setStatus(`Error: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(type, data, sql = null, validationData = null) {
        // Handle instance-info specially - display in drawer
        if (type === 'instance-info') {
            this.displayInstanceInfo(data, sql);
            return;
        }

        const column = document.querySelector(`[data-query="${type}"]`);
        if (!column) return;

        const table = column.querySelector('.result-table');
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        const countEl = column.querySelector('.result-count');
        const sqlContent = column.querySelector('.sql-content');

        // Clear existing data
        thead.innerHTML = '';
        tbody.innerHTML = '';

        // Display SQL with actual parameter value
        if (sql) {
            // Replace %s with actual PROD_INST_ID value
            const prodInstId = this.getProdInstId();
            const formattedSql = sql.replace(/%s/g, `'${prodInstId}'`);
            sqlContent.textContent = formattedSql;
        }

        // Show/hide color legend for change-record
        const legendEl = document.getElementById('colorLegend');
        if (type === 'change-record') {
            legendEl.style.display = 'flex';
        } else if (type === 'instance-info') {
            // Hide legend when instance-info is displayed (last query)
            const hasChangeRecord = document.querySelector('[data-query="change-record"] tbody tr');
            if (!hasChangeRecord) {
                legendEl.style.display = 'none';
            }
        }

        // For change-log, apply current filter if exists
        if (type === 'change-log' && data.length > 0) {
            const filterValue = document.getElementById('attrNameFilter').value.trim();
            if (filterValue) {
                data = data.filter(row => {
                    const attrName = row.ATTR_NAME || '';
                    return attrName.toLowerCase().includes(filterValue.toLowerCase());
                });
            }
        }

        if (!data || data.length === 0) {
            countEl.textContent = '0 rows';
            if (type === 'change-record') {
                legendEl.style.display = 'none';
            }
            return;
        }

        // Get column names from first row
        const columns = Object.keys(data[0]);

        // Define fixed column order for change-record table (matching SQL SELECT order)
        const CHANGE_RECORD_COLUMN_ORDER = [
            'ACCT_ITEM_TYPE_ID',
            'ID',
            'PROD_INST_ID',
            'NAME',
            'START_DATE',
            'END_DATE',
            'START_FLAG',
            'LATEST_FLAG',
            'LOOP_MONEY',
            'CAL_ACCT_RECORD_ID',
            'ACCT_ID',
            'CREATE_DATE',
            'UPDATE_DATE'
        ];

        // Use fixed order for change-record, otherwise use dynamic order
        const orderedColumns = (type === 'change-record')
            ? CHANGE_RECORD_COLUMN_ORDER.filter(col => columns.includes(col))
            : columns;

        // Create header row
        const headerRow = document.createElement('tr');
        orderedColumns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        // Check if this is change-record table (for color coding and validation)
        const isChangeRecord = type === 'change-record';

        // Get invalid groups set for quick lookup
        const invalidGroupsSet = new Set();
        if (isChangeRecord && validationData && validationData.invalid_groups) {
            validationData.invalid_groups.forEach(group => invalidGroupsSet.add(group));
        }

        // Assign alternating colors to invalid groups (red/purple)
        if (isChangeRecord && validationData && validationData.invalid_groups) {
            let colorIndex = 0;
            validationData.invalid_groups.forEach(groupKey => {
                if (!this.invalidGroups.has(groupKey)) {
                    // Alternate between 'red' and 'purple'
                    const color = colorIndex % 2 === 0 ? 'red' : 'purple';
                    this.invalidGroups.set(groupKey, color);
                    colorIndex++;
                }
            });
        }

        // Track unique ACCT_ITEM_TYPE_IDs for legend
        const uniqueAcctTypes = new Set();

        // Create data rows
        data.forEach(row => {
            const tr = document.createElement('tr');

            // Apply color coding for change-record based on ACCT_ITEM_TYPE_ID
            if (isChangeRecord && row.ACCT_ITEM_TYPE_ID) {
                uniqueAcctTypes.add(row.ACCT_ITEM_TYPE_ID);

                // Check if this row belongs to an invalid group
                const groupKey = `${row.ACCT_ITEM_TYPE_ID}_${row.PROD_INST_ID}`;
                if (invalidGroupsSet.has(groupKey)) {
                    // Apply alternating colors for invalid rows (red/purple)
                    const color = this.invalidGroups.get(groupKey) || 'red';
                    tr.classList.add('row-invalid');
                    tr.classList.add(`row-invalid-${color}`);
                    tr.dataset.groupKey = groupKey;
                    tr.dataset.invalidColor = color;

                    // Store row data in the element for SQL generation
                    tr.rowData = row;

                    // Add click handler for filtering
                    tr.addEventListener('click', (e) => {
                        // Always call toggleFilter - it will handle clearing if clicking same group
                        this.toggleFilter(groupKey, color);
                    });

                    // Add right-click context menu for SQL generation
                    tr.addEventListener('contextmenu', (e) => {
                        e.preventDefault();
                        this.showContextMenu(e, groupKey, color);
                    });
                } else {
                    // Apply color coding for valid rows using sequential assignment
                    const color = this.getColorForAcctType(row.ACCT_ITEM_TYPE_ID);
                    tr.style.backgroundColor = color;
                    tr.dataset.groupKey = groupKey;
                }
            }

            orderedColumns.forEach(col => {
                const td = document.createElement('td');
                let value = row[col];

                // Format datetime columns
                if (value !== null && value !== undefined && isDateColumn(col)) {
                    value = formatDateTime(value);
                }

                const displayValue = value !== null && value !== undefined ? String(value) : '';
                td.textContent = displayValue;
                td.title = displayValue;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        // Update legend with dynamic account type info
        if (isChangeRecord && uniqueAcctTypes.size > 0) {
            this.updateLegend(uniqueAcctTypes, invalidGroupsSet);
        }

        countEl.textContent = `${data.length} rows`;
    }

    toggleFilter(groupKey, color) {
        const tbody = document.querySelector('[data-query="change-record"] tbody');
        const allRows = tbody.querySelectorAll('tr');

        // If clicking the same filter, clear it
        if (this.currentFilter === groupKey) {
            this.currentFilter = null;
            allRows.forEach(row => {
                row.classList.remove('filtered', 'filtered-out');
            });
            this.setStatus('Filter cleared');
            return;
        }

        // Set new filter
        this.currentFilter = groupKey;
        allRows.forEach(row => {
            const rowGroupKey = row.dataset.groupKey;
            if (rowGroupKey === groupKey) {
                row.classList.add('filtered');
                row.classList.remove('filtered-out');
            } else {
                row.classList.remove('filtered');
                row.classList.add('filtered-out');
            }
        });

        this.setStatus(`Filtered by ${color} group - Click again to clear`, 'success');
    }

    updateLegend(uniqueAcctTypes, invalidGroups) {
        const legendEl = document.getElementById('colorLegend');
        legendEl.style.display = 'flex';
    }

    clearResults() {
        const columns = document.querySelectorAll('[data-query]');
        columns.forEach(column => {
            const table = column.querySelector('.result-table');
            table.querySelector('thead').innerHTML = '';
            table.querySelector('tbody').innerHTML = '';
            column.querySelector('.result-count').textContent = '0 rows';
            column.querySelector('.sql-content').textContent = '-- SQL query will appear here after execution';
        });

        // Clear instance info drawer
        const drawer = document.getElementById('instanceDrawer');
        const drawerTable = drawer.querySelector('.result-table');
        const drawerTbody = drawerTable.querySelector('tbody');
        const drawerThead = drawerTable.querySelector('thead');
        const drawerEmptyState = drawer.querySelector('.empty-state');
        drawerThead.innerHTML = '';
        drawerTbody.innerHTML = '';
        drawerEmptyState.style.display = 'flex';
        drawerTable.style.display = 'none';
        drawer.querySelector('.sql-content').textContent = '-- SQL query will appear here after execution';

        // Hide color legend when clearing
        const legendEl = document.getElementById('colorLegend');
        legendEl.style.display = 'none';

        // Clear filter input and count
        document.getElementById('attrNameFilter').value = '';
        document.getElementById('filterCount').textContent = '';

        // Reset color map
        this.resetColorMap();

        document.getElementById('prodInstId').value = '';
        this.setStatus('Results cleared');
    }

    copySql(type) {
        const column = document.querySelector(`[data-query="${type}"]`);
        const sqlContent = column.querySelector('.sql-content');
        const sql = sqlContent.textContent;

        if (sql && sql !== '-- SQL query will appear here after execution') {
            navigator.clipboard.writeText(sql).then(() => {
                // Show copied feedback
                const btn = column.querySelector('.copy-sql-btn');
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.classList.remove('copied');
                }, 2000);
                this.setStatus('SQL copied to clipboard', 'success');
            }).catch(err => {
                this.setStatus('Failed to copy SQL', 'error');
            });
        }
    }

    setLoading(loading) {
        const columns = document.querySelectorAll('.result-column');
        columns.forEach(column => {
            if (loading) {
                column.classList.add('loading');
            } else {
                column.classList.remove('loading');
            }
        });

        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(btn => {
            btn.disabled = loading;
        });
    }

    async loadConfig() {
        try {
            const response = await fetch(`${this.apiUrl}/config`);
            this.currentConfig = await response.json();
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    openConfigModal() {
        const modal = document.getElementById('configModal');

        // Populate form with current config
        document.getElementById('dbHost').value = this.currentConfig.host || '';
        document.getElementById('dbPort').value = this.currentConfig.port || 3306;
        document.getElementById('dbUser').value = this.currentConfig.user || '';
        document.getElementById('dbPassword').value = ''; // Don't show password
        document.getElementById('dbDatabase').value = this.currentConfig.database || '';

        modal.classList.add('show');
    }

    closeConfigModal() {
        document.getElementById('configModal').classList.remove('show');
    }

    async testConnection() {
        const config = this.getFormConfig();

        this.setStatus('Testing connection...');
        const btn = document.getElementById('testConnBtn');
        const originalText = btn.textContent;
        btn.textContent = 'Testing...';
        btn.disabled = true;

        try {
            const response = await fetch(`${this.apiUrl}/test-connection`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.success) {
                alert('Connection successful!');
            } else {
                alert(`Connection failed: ${result.message}`);
            }
        } catch (error) {
            alert(`Connection failed: ${error.message}`);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
            this.setStatus('Ready');
        }
    }

    async saveConfig() {
        const config = this.getFormConfig();

        try {
            const response = await fetch(`${this.apiUrl}/config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.success) {
                this.currentConfig = { ...this.currentConfig, ...config };
                this.closeConfigModal();
                this.setStatus('Configuration saved', 'success');
            } else {
                alert(`Failed to save config: ${result.message}`);
            }
        } catch (error) {
            alert(`Failed to save config: ${error.message}`);
        }
    }

    getFormConfig() {
        return {
            host: document.getElementById('dbHost').value,
            port: parseInt(document.getElementById('dbPort').value),
            user: document.getElementById('dbUser').value,
            password: document.getElementById('dbPassword').value,
            database: document.getElementById('dbDatabase').value,
            charset: 'utf8mb4'
        };
    }

    showSqlFixModal(groupKey, color) {
        // Get all rows for this invalid group
        const [acctTypeId, prodInstId] = groupKey.split('_');
        const groupRows = this.changeRecordData.filter(row =>
            row.ACCT_ITEM_TYPE_ID == acctTypeId && row.PROD_INST_ID == prodInstId
        );

        // Sort by START_DATE
        const sortedRows = [...groupRows].sort((a, b) => {
            const dateA = new Date(a.START_DATE || 0);
            const dateB = new Date(b.START_DATE || 0);
            return dateA - dateB;
        });

        // Analyze the violation
        const analysis = this.analyzeViolation(sortedRows);

        // Store current violation data for LLM SQL generation
        this.currentViolationData = {
            rows: sortedRows,
            description: `${analysis.violationType}: ${analysis.description}`,
            groupKey: groupKey,
            color: color
        };

        // Display violation info
        const violationInfo = document.getElementById('violationInfo');
        violationInfo.innerHTML = `<strong>违规类型:</strong> ${analysis.violationType}<br><strong>说明:</strong> ${analysis.description}`;
        violationInfo.style.cssText = 'margin-bottom: 20px; padding: 12px; background-color: #fee2e2; border-radius: 6px; border-left: 4px solid #dc2626;';

        // Display current data as table
        const currentDataDiv = document.getElementById('currentData');
        currentDataDiv.innerHTML = this.createDataTable(sortedRows);

        // Display fixed data
        const fixedDataDiv = document.getElementById('fixedData');
        fixedDataDiv.innerHTML = this.createDataTable(analysis.fixedRows, true);
        fixedDataDiv.style.cssText = 'margin-bottom: 20px; padding: 12px; background-color: #dcfce7; border-radius: 6px;';

        // Display SQL with syntax highlighting
        const sqlStatement = document.getElementById('sqlStatement');
        sqlStatement.innerHTML = highlightSQL(analysis.sql);

        // Reset LLM SQL display
        document.getElementById('llmSqlResult').style.display = 'none';
        document.getElementById('llmSqlStatement').textContent = '';
        document.getElementById('generateLlmSqlBtn').disabled = false;
        document.getElementById('generateLlmSqlBtn').innerHTML = '<span class="icon">🤖</span> 生成大模型修复SQL';

        // Clear other tab contents
        document.getElementById('llmMetadata').innerHTML = '';
        document.getElementById('promptContainer').innerHTML = '';
        document.getElementById('fixStepsList').innerHTML = '';
        document.getElementById('timelineSvg').innerHTML = '';

        // Show modal
        document.getElementById('sqlFixModal').classList.add('show');

        // Initialize tabs
        this.initTabs();

        // Pre-render timeline with current data
        this.renderTimeline(sortedRows);
    }

    closeSqlFixModal() {
        document.getElementById('sqlFixModal').classList.remove('show');
        // 关闭时重置最大化状态
        this.resetMaximizeState();
    }

    toggleMaximizeSqlModal() {
        const modal = document.getElementById('sqlFixModal');
        const maximizeBtn = document.getElementById('maximizeSqlModal');

        if (modal.classList.contains('maximized')) {
            // 还原
            modal.classList.remove('maximized');
            maximizeBtn.textContent = '□';
            maximizeBtn.title = '最大化';
        } else {
            // 最大化
            modal.classList.add('maximized');
            maximizeBtn.textContent = '❐';
            maximizeBtn.title = '还原';
        }
    }

    resetMaximizeState() {
        const modal = document.getElementById('sqlFixModal');
        const maximizeBtn = document.getElementById('maximizeSqlModal');
        modal.classList.remove('maximized');
        maximizeBtn.textContent = '□';
        maximizeBtn.title = '最大化';
    }

    copyFixSql() {
        const sqlStatement = document.getElementById('sqlStatement');
        const sql = sqlStatement.textContent;

        navigator.clipboard.writeText(sql).then(() => {
            const btn = document.getElementById('copySqlBtn');
            const originalText = btn.textContent;
            btn.textContent = '已复制!';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
            this.setStatus('SQL 已复制到剪贴板', 'success');
        }).catch(err => {
            this.setStatus('复制 SQL 失败', 'error');
        });
    }

    async generateLlmSql() {
        if (!this.currentViolationData) {
            alert('没有可用的异常数据');
            return;
        }

        const btn = document.getElementById('generateLlmSqlBtn');
        const resultDiv = document.getElementById('llmSqlResult');
        const sqlPre = document.getElementById('llmSqlStatement');

        btn.disabled = true;
        btn.innerHTML = '<span class="icon">⏳</span> 正在生成...';

        try {
            // Get PROD_INST_ID from current violation data
            const prodInstId = this.currentViolationData.rows[0]?.PROD_INST_ID;
            // Filter change log data for this PROD_INST_ID
            const logData = prodInstId
                ? (this.changeLogData || []).filter(log => log.PROD_INST_ID == prodInstId)
                : [];

            const response = await fetch('/api/generate-llm-sql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    currentData: this.currentViolationData.rows,
                    violationInfo: this.currentViolationData.description,
                    logData: logData
                })
            });

            const data = await response.json();

            if (data.success) {
                sqlPre.innerHTML = highlightSQL(data.sql);
                resultDiv.style.display = 'block';
                this.setStatus('大模型 SQL 生成成功', 'success');

                // 新增：渲染推理信息
                this.renderLlmReasoning(data);

                // 新增：渲染修复可视化
                this.renderFixVisualization(data.sql);

                // 新增：初始化 Tabs
                this.initTabs();
            } else {
                alert('生成失败: ' + (data.message || '未知错误'));
                btn.disabled = false;
                btn.innerHTML = '<span class="icon">🤖</span> 生成大模型修复SQL';
            }
        } catch (error) {
            alert('生成失败: ' + error.message);
            btn.disabled = false;
            btn.innerHTML = '<span class="icon">🤖</span> 生成大模型修复SQL';
        } finally {
            if (btn.innerHTML.includes('正在生成')) {
                btn.disabled = false;
                btn.innerHTML = '<span class="icon">🤖</span> 重新生成';
            }
        }
    }

    copyLlmSql() {
        const sqlElement = document.getElementById('llmSqlStatement');
        // Get plain text from innerHTML by stripping HTML tags
        const sqlText = sqlElement.textContent || sqlElement.innerText;

        if (!sqlText || sqlText.trim() === '') {
            alert('没有可复制的 SQL');
            return;
        }

        navigator.clipboard.writeText(sqlText).then(() => {
            const btn = document.getElementById('copyLlmSqlBtn');
            const originalText = btn.textContent;
            btn.textContent = '已复制!';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
            this.setStatus('大模型 SQL 已复制到剪贴板', 'success');
        }).catch(err => {
            this.setStatus('复制失败', 'error');
        });
    }

    analyzeViolation(rows) {
        // Check for continuity violation (END_DATE != next.START_DATE)
        // Collect all continuity violations
        const continuityViolations = [];
        const fixedRowsMap = new Map(); // Track which rows need fixing

        for (let i = 0; i < rows.length - 1; i++) {
            const current = rows[i];
            const nextRow = rows[i + 1];

            const endDate = current.END_DATE ? new Date(current.END_DATE) : null;
            const nextStartDate = nextRow.START_DATE ? new Date(nextRow.START_DATE) : null;

            if (endDate && nextStartDate && endDate.getTime() !== nextStartDate.getTime()) {
                continuityViolations.push({
                    index: i,
                    current,
                    nextRow,
                    currentEndDate: current.END_DATE,
                    nextStartDate: nextRow.START_DATE
                });

                // Mark this row for fixing
                fixedRowsMap.set(current.ID, { ...current, END_DATE: nextRow.START_DATE });
            }
        }

        // If we have continuity violations, generate SQL for all of them
        if (continuityViolations.length > 0) {
            // Build fixedRows array
            const fixedRows = rows.map(row => {
                if (fixedRowsMap.has(row.ID)) {
                    return fixedRowsMap.get(row.ID);
                }
                return row;
            });

            // Generate SQL for each violation
            const sqlStatements = continuityViolations.map(v =>
                `update cal_acct_record set END_DATE = '${v.nextStartDate}' where prod_inst_id = ${v.current.PROD_INST_ID} and id = ${v.current.ID} and (END_DATE = '${v.currentEndDate}');`
            );

            const description = continuityViolations.length === 1
                ? `第 ${continuityViolations[0].index + 1} 行的 END_DATE (${continuityViolations[0].currentEndDate}) 与第 ${continuityViolations[0].index + 2} 行的 START_DATE (${continuityViolations[0].nextStartDate}) 不匹配`
                : `发现 ${continuityViolations.length} 处连续性违规，需要修复 ${continuityViolations.length} 行数据`;

            return {
                violationType: '连续性违规',
                description,
                fixedRows,
                sql: sqlStatements.join('\n\n')
            };
        }

        // Check for START_FLAG violation
        const startFlagRows = rows.filter(r => r.START_FLAG == 1);
        if (startFlagRows.length !== 1) {
            // Fix: keep the first row's START_FLAG = 1, set others to 0
            const sortedByStartDate = [...rows].sort((a, b) =>
                new Date(a.START_DATE || 0) - new Date(b.START_DATE || 0)
            );

            const fixedRows = rows.map(row => {
                const isEarliest = row.ID === sortedByStartDate[0].ID;
                return { ...row, START_FLAG: isEarliest ? 1 : 0 };
            });

            const sqlStatements = rows
                .filter(r => r.START_FLAG != (r.ID === sortedByStartDate[0].ID ? 1 : 0))
                .map(r =>
                    `update cal_acct_record set START_FLAG = ${r.ID === sortedByStartDate[0].ID ? 1 : 0} where prod_inst_id = ${r.PROD_INST_ID} and id = ${r.ID};`
                )
                .join('\n');

            return {
                violationType: '唯一性违规',
                description: `应该只有一行 START_FLAG = 1，当前有 ${startFlagRows.length} 行`,
                fixedRows,
                sql: sqlStatements
            };
        }

        // Check for LATEST_FLAG violation
        const nullEndDateRows = rows.filter(r => !r.END_DATE);
        if (nullEndDateRows.length > 0) {
            // Rows with NULL END_DATE must have LATEST_FLAG = 1
            const invalidLatestFlag = nullEndDateRows.filter(r => r.LATEST_FLAG != 1);
            if (invalidLatestFlag.length > 0) {
                const fixedRows = rows.map(row => {
                    if (!row.END_DATE && row.LATEST_FLAG != 1) {
                        return { ...row, LATEST_FLAG: 1 };
                    }
                    return row;
                });

                const sql = invalidLatestFlag
                    .map(r => `update cal_acct_record set LATEST_FLAG = 1 where prod_inst_id = ${r.PROD_INST_ID} and id = ${r.ID};`)
                    .join('\n');

                return {
                    violationType: '最新标志违规',
                    description: 'END_DATE 为 NULL 的行必须设置 LATEST_FLAG = 1',
                    fixedRows,
                    sql
                };
            }
        } else {
            // Find row with max END_DATE, it should have LATEST_FLAG = 1
            const maxEndDate = rows.reduce((max, r) => {
                const endDate = new Date(r.END_DATE || 0);
                const maxDate = new Date(max.END_DATE || 0);
                return endDate > maxDate ? r : max;
            });

            if (maxEndDate.LATEST_FLAG != 1) {
                const fixedRows = rows.map(row => {
                    const isMax = row.ID === maxEndDate.ID;
                    return { ...row, LATEST_FLAG: isMax ? 1 : 0 };
                });

                const sqlStatements = [];

                // Set LATEST_FLAG = 1 for max END_DATE row
                sqlStatements.push(`update cal_acct_record set LATEST_FLAG = 1 where prod_inst_id = ${maxEndDate.PROD_INST_ID} and id = ${maxEndDate.ID};`);

                // Set LATEST_FLAG = 0 for other rows that have LATEST_FLAG = 1
                rows.forEach(r => {
                    if (r.ID !== maxEndDate.ID && r.LATEST_FLAG == 1) {
                        sqlStatements.push(`update cal_acct_record set LATEST_FLAG = 0 where prod_inst_id = ${r.PROD_INST_ID} and id = ${r.ID};`);
                    }
                });

                return {
                    violationType: '最新标志违规',
                    description: `END_DATE 最大的行 (ID=${maxEndDate.ID}) 应该设置 LATEST_FLAG = 1`,
                    fixedRows,
                    sql: sqlStatements.join('\n')
                };
            }
        }

        return {
            violationType: '未知违规',
            description: '无法自动分析',
            fixedRows: rows,
            sql: '-- 请手动检查数据'
        };
    }

    createDataTable(rows, showChanges = false) {
        if (!rows || rows.length === 0) return '<p>无数据</p>';

        const columns = ['ACCT_ITEM_TYPE_ID', 'ID', 'PROD_INST_ID', 'NAME', 'START_DATE', 'END_DATE', 'START_FLAG', 'LATEST_FLAG'];

        let html = '<table class="data-table"><thead><tr>';
        columns.forEach(col => {
            html += `<th>${col}</th>`;
        });
        html += '</tr></thead><tbody>';

        const originalRows = showChanges ? this.changeRecordData : [];

        rows.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                const value = row[col];
                let cellClass = '';

                // Check if this value changed (for fixed data display)
                if (showChanges) {
                    const originalRow = originalRows.find(r => r.ID === row.ID);
                    if (originalRow && originalRow[col] !== value) {
                        cellClass = 'changed-cell';
                    }
                }

                html += `<td class="${cellClass}">${value !== null && value !== undefined ? value : ''}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    }

    showContextMenu(event, groupKey, color) {
        const contextMenu = document.getElementById('contextMenu');

        // Store the target row
        this.contextMenuTarget = event.currentTarget;

        // Get menu dimensions
        const menuWidth = 180; // approximate width
        const menuHeight = 50; // approximate height

        // Calculate position (viewport coordinates)
        let x = event.clientX;
        let y = event.clientY;

        // Adjust if menu would go off screen
        if (x + menuWidth > window.innerWidth) {
            x = window.innerWidth - menuWidth - 10;
        }
        if (y + menuHeight > window.innerHeight) {
            y = window.innerHeight - menuHeight - 10;
        }

        // Position the menu at cursor location
        contextMenu.style.left = `${x}px`;
        contextMenu.style.top = `${y}px`;
        contextMenu.style.display = 'block';

        // Prevent default context menu
        event.preventDefault();
        event.stopPropagation();
    }

    hideContextMenu() {
        const contextMenu = document.getElementById('contextMenu');
        contextMenu.style.display = 'none';
        this.contextMenuTarget = null;
    }

    filterChangeLog(filterValue) {
        // Re-display change-log with filter applied
        const changeLogColumn = document.querySelector('[data-query="change-log"]');
        const sqlContent = changeLogColumn.querySelector('.sql-content');
        const sql = sqlContent.textContent;

        // Get filtered data
        let filteredData = this.changeLogData;
        if (filterValue) {
            filteredData = this.changeLogData.filter(row => {
                const attrName = row.ATTR_NAME || '';
                return attrName.toLowerCase().includes(filterValue.toLowerCase());
            });
        }

        // Update filter count display
        const filterCountEl = document.getElementById('filterCount');
        if (filterValue) {
            filterCountEl.textContent = `${filteredData.length} / ${this.changeLogData.length}`;
        } else {
            filterCountEl.textContent = '';
        }

        // Re-display with filtered data (get the SQL from the element)
        this.displayResults('change-log', filteredData, sql !== '-- SQL query will appear here after execution' ? sql : null);
    }

    toggleDrawer() {
        const drawer = document.getElementById('instanceDrawer');
        const isOpen = drawer.classList.contains('open');

        if (isOpen) {
            drawer.classList.remove('open');
        } else {
            drawer.classList.add('open');
        }
    }

    closeDrawer() {
        document.getElementById('instanceDrawer').classList.remove('open');
    }

    displayInstanceInfo(data, sql = null) {
        const drawer = document.getElementById('instanceDrawer');
        const table = drawer.querySelector('.result-table');
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        const emptyState = drawer.querySelector('.empty-state');
        const sqlContent = drawer.querySelector('.sql-content');

        // Clear existing data
        thead.innerHTML = '';
        tbody.innerHTML = '';

        // Display SQL with actual parameter value
        if (sql) {
            const prodInstId = this.getProdInstId();
            const formattedSql = sql.replace(/%s/g, `'${prodInstId}'`);
            sqlContent.textContent = formattedSql;
        }

        if (!data || data.length === 0) {
            emptyState.style.display = 'flex';
            table.style.display = 'none';
            return;
        }

        emptyState.style.display = 'none';
        table.style.display = 'table';

        // Get column names from first row
        const columns = Object.keys(data[0]);

        // Create header row
        const headerRow = document.createElement('tr');
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        // Create data rows
        data.forEach(row => {
            const tr = document.createElement('tr');
            columns.forEach(col => {
                const td = document.createElement('td');
                let value = row[col];

                // Format datetime columns
                if (value !== null && value !== undefined && isDateColumn(col)) {
                    value = formatDateTime(value);
                }

                const displayValue = value !== null && value !== undefined ? String(value) : '';
                td.textContent = displayValue;
                td.title = displayValue;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }

    // ==================== Tab 管理 ====================
    initTabs() {
        const modal = document.getElementById('sqlFixModal');
        if (!modal) return;

        // Check if tabs are already initialized
        if (modal._tabsInitialized) return;

        const tabBtns = modal.querySelectorAll('.tab-btn');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;
                const allBtns = modal.querySelectorAll('.tab-btn');
                const allContents = modal.querySelectorAll('.tab-content');

                allBtns.forEach(b => b.classList.remove('active'));
                allContents.forEach(c => c.classList.remove('active'));

                btn.classList.add('active');
                const contentEl = document.getElementById(`tab-${tabName}`);
                if (contentEl) {
                    contentEl.classList.add('active');
                }

                // Render timeline when switching to timeline tab
                if (tabName === 'timeline' && this.currentViolationData) {
                    this.renderTimeline(this.currentViolationData.rows);
                }
            });
        });

        modal._tabsInitialized = true;
    }

    // ==================== 时间线渲染 ====================
    renderTimeline(originalRows) {
        const svg = document.getElementById('timelineSvg');
        if (!svg || !originalRows || originalRows.length === 0) return;

        // 获取修复后的数据
        const fixedRows = this.currentViolationData?.fixedRows || null;
        const hasChanges = fixedRows && this.hasDataChanged(originalRows, fixedRows);

        // 计算时间范围
        const allRows = fixedRows ? [...originalRows, ...fixedRows] : originalRows;
        const dates = allRows.flatMap(r => [
            new Date(r.START_DATE || 0),
            r.END_DATE ? new Date(r.END_DATE) : new Date()
        ]);
        const minDate = new Date(Math.min(...dates));
        const maxDate = new Date(Math.max(...dates));
        minDate.setHours(0, 0, 0, 0);
        maxDate.setHours(23, 59, 59, 999);

        // 按年显示时间轴
        const yearMs = 365 * 24 * 60 * 60 * 1000;
        const totalYears = Math.max(8, Math.ceil((maxDate - minDate) / yearMs) + 1);

        // 配置 - 使用固定大宽度，通过CSS自适应
        const labelWidth = 200;
        const yearWidth = 150;  // 每年的固定宽度
        const rowHeight = 70;
        const rowGap = 10;
        const headerHeight = 80;
        const sectionGap = hasChanges ? 50 : 0;
        const width = labelWidth + totalYears * yearWidth + 100;
        const section1Height = originalRows.length * (rowHeight + rowGap);
        const section2Height = hasChanges && fixedRows ? fixedRows.length * (rowHeight + rowGap) : 0;
        const height = headerHeight + section1Height + sectionGap + section2Height + 70;

        let svgContent = `<svg viewBox="0 0 ${width} ${height}" class="timeline-gantt">`;

        // 样式定义
        svgContent += `
            <defs>
                <style>
                    .timeline-title { font-size: 16px; font-weight: 700; fill: #1e293b; }
                    .timeline-year { font-size: 13px; fill: #64748b; text-anchor: middle; font-weight: 600; }
                    .timeline-grid { stroke: #e2e8f0; stroke-width: 1; }
                    .timeline-row-id { font-size: 13px; fill: #334155; font-weight: 600; }
                    .timeline-row-name { font-size: 11px; fill: #64748b; }
                    .timeline-bar { cursor: pointer; }
                    .timeline-bar-normal { fill: #3b82f6; }
                    .timeline-bar-changed { fill: #f59e0b; }
                    .timeline-bar-fixed { fill: #22c55e; }
                    .timeline-bar-overlap { fill: #ef4444; opacity: 0.85; }
                    .timeline-bar:hover { opacity: 0.8; }
                    .timeline-date-text { font-size: 11px; fill: #ffffff; font-weight: 600; text-anchor: middle; }
                    .timeline-date-outside { font-size: 10px; fill: #475569; font-weight: 600; }
                    .timeline-change-text { font-size: 11px; fill: #b45309; font-weight: 700; }
                    .timeline-arrow { stroke: #64748b; stroke-width: 2; fill: none; marker-end: url(#arrow); }
                    .timeline-section-divider { stroke: #e2e8f0; stroke-width: 2; stroke-dasharray: 6,4; }
                </style>
                <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                    <path d="M0,0 L8,3 L0,6" fill="#64748b"/>
                </marker>
            </defs>
        `;

        // 背景
        svgContent += `<rect width="${width}" height="${height}" fill="#ffffff"/>`;

        // 计算X坐标
        const getDateX = (date) => {
            const d = new Date(date);
            const offset = d - minDate;
            return labelWidth + (offset / yearMs) * yearWidth;
        };

        const formatDate = (d) => {
            const date = new Date(d);
            return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        };

        // 绘制时间轴（年份）
        svgContent += `<line x1="${labelWidth}" y1="${headerHeight}" x2="${width - 30}" y2="${headerHeight}" stroke="#cbd5e1" stroke-width="2"/>`;
        for (let y = 0; y <= totalYears; y++) {
            const x = labelWidth + y * yearWidth;
            const yearDate = new Date(minDate.getTime() + y * yearMs);
            const year = yearDate.getFullYear();

            svgContent += `<line x1="${x}" y1="${headerHeight - 10}" x2="${x}" y2="${height - 60}" class="timeline-grid"/>`;
            svgContent += `<text x="${x + yearWidth / 2}" y="${headerHeight - 20}" class="timeline-year">${year}年</text>`;
        }

        // 绘制一行数据
        const drawRow = (row, y, isFixed = false, originalRow = null) => {
            const startDate = new Date(row.START_DATE);
            const endDate = row.END_DATE ? new Date(row.END_DATE) : maxDate;
            const x1 = getDateX(startDate);
            const x2 = getDateX(endDate);
            const barWidth = Math.max(x2 - x1, 3);

            // 检查是否有变化
            let hasChange = false;
            let changeInfo = '';
            if (originalRow) {
                if (String(originalRow.START_DATE) !== String(row.START_DATE)) {
                    hasChange = true;
                    changeInfo = `START_DATE: ${formatDate(originalRow.START_DATE)} → ${formatDate(row.START_DATE)}`;
                }
                if (String(originalRow.END_DATE) !== String(row.END_DATE)) {
                    hasChange = true;
                    changeInfo = `END_DATE: ${formatDate(originalRow.END_DATE)} → ${formatDate(row.END_DATE)}`;
                }
            }

            const barClass = isFixed && hasChange ? 'timeline-bar-fixed' : hasChange ? 'timeline-bar-changed' : 'timeline-bar-normal';

            // 标签
            svgContent += `<text x="15" y="${y + 25}" class="timeline-row-id">#${row.ID}</text>`;
            svgContent += `<text x="15" y="${y + 45}" class="timeline-row-name">${row.NAME || '未命名'}</text>`;

            // 时间条
            svgContent += `<g class="timeline-bar" data-id="${row.ID}">
                <rect x="${x1}" y="${y + 5}" width="${barWidth}" height="${rowHeight - 10}" rx="5" class="${barClass}"/>`;

            // 日期标签 - 根据宽度决定位置
            if (barWidth > 100) {
                svgContent += `<text x="${x1 + barWidth / 2}" y="${y + rowHeight / 2 + 4}" class="timeline-date-text">${formatDate(startDate)} ~ ${formatDate(endDate)}</text>`;
            } else {
                svgContent += `<text x="${x1 - 5}" y="${y + 22}" class="timeline-date-outside" text-anchor="end">${formatDate(startDate)}</text>`;
                svgContent += `<text x="${x2 + 5}" y="${y + 22}" class="timeline-date-outside">${formatDate(endDate)}</text>`;
            }

            svgContent += `</g>`;

            // 变化标记
            if (hasChange) {
                const tagY = y + rowHeight / 2;
                const tagX = isFixed ? x2 + 10 : x1 - 10;
                const tagAnchor = isFixed ? 'start' : 'end';
                svgContent += `<text x="${tagX}" y="${tagY + 4}" class="timeline-change-text" text-anchor="${tagAnchor}">⚡ ${changeInfo}</text>`;
            }
        };

        // 绘制重叠高亮
        const drawOverlapHighlight = (rows, startY) => {
            rows.forEach((row, i) => {
                const y = startY + i * (rowHeight + rowGap) + 5;
                const startDate = new Date(row.START_DATE);
                const endDate = row.END_DATE ? new Date(row.END_DATE) : maxDate;

                rows.forEach((otherRow, j) => {
                    if (i >= j) return;
                    const otherStart = new Date(otherRow.START_DATE);
                    const otherEnd = otherRow.END_DATE ? new Date(otherRow.END_DATE) : maxDate;

                    // 找出重叠区间
                    const overlapStart = otherStart < endDate ? otherStart : null;
                    const overlapEnd = startDate < otherEnd ? startDate : null;

                    if (overlapStart && overlapEnd && overlapStart < overlapEnd) {
                        const x1 = getDateX(overlapStart);
                        const x2 = getDateX(overlapEnd);
                        svgContent += `<rect x="${x1}" y="${y}" width="${Math.max(x2 - x1, 2)}" height="${rowHeight - 10}" class="timeline-bar-overlap" rx="5"/>`;
                        svgContent += `<text x="${(x1 + x2) / 2}" y="${y + rowHeight / 2 + 4}" class="timeline-date-text">⚠️ 重叠!</text>`;
                    }
                });
            });
        };

        // 修复前section
        const section1Y = headerHeight;
        svgContent += `<text x="15" y="${section1Y - 15}" class="timeline-title">❌ 修复前 (当前数据) - 红色区域表示时间重叠</text>`;
        drawOverlapHighlight(originalRows, section1Y);
        originalRows.forEach((row, i) => {
            const y = section1Y + i * (rowHeight + rowGap);
            drawRow(row, y, false, fixedRows?.find(r => r.ID === row.ID));
        });

        // 修复后section
        if (fixedRows && hasChanges) {
            const section2Y = section1Y + section1Height + sectionGap;
            svgContent += `<line x1="0" y1="${section2Y - sectionGap / 2}" x2="${width}" y2="${section2Y - sectionGap / 2}" class="timeline-section-divider"/>`;
            svgContent += `<text x="15" y="${section2Y - 15}" class="timeline-title">✅ 修复后 (预期数据) - 已消除重叠</text>`;

            // 绘制箭头连接
            originalRows.forEach((row, i) => {
                const fixedRow = fixedRows.find(r => r.ID === row.ID);
                if (fixedRow && this.hasRowChanged(row, fixedRow)) {
                    const y1 = section1Y + i * (rowHeight + rowGap) + rowHeight / 2;
                    const y2 = section2Y + fixedRows.indexOf(fixedRow) * (rowHeight + rowGap) + rowHeight / 2;
                    svgContent += `<path d="M ${labelWidth - 40} ${y1} L ${labelWidth - 40} ${y2}" class="timeline-arrow"/>`;
                }
            });

            fixedRows.forEach((row, i) => {
                const y = section2Y + i * (rowHeight + rowGap);
                drawRow(row, y, true, originalRows.find(r => r.ID === row.ID));
            });
        }

        // 图例
        const legendY = height - 45;
        svgContent += `
            <g transform="translate(${labelWidth}, ${legendY})">
                <rect width="24" height="16" rx="4" class="timeline-bar-normal"/>
                <text x="30" y="13" font-size="12" fill="#475569" font-weight="600">正常记录</text>

                <rect x="130" width="24" height="16" rx="4" class="timeline-bar-changed"/>
                <text x="160" y="13" font-size="12" fill="#475569" font-weight="600">需要修改</text>

                <rect x="270" width="24" height="16" rx="4" class="timeline-bar-fixed"/>
                <text x="300" y="13" font-size="12" fill="#475569" font-weight="600">已修复</text>

                <rect x="390" width="24" height="16" rx="4" class="timeline-bar-overlap"/>
                <text x="420" y="13" font-size="12" fill="#475569" font-weight="600">重叠异常</text>

                <path d="M 520 8 L 550 8" class="timeline-arrow"/>
                <text x="560" y="13" font-size="12" fill="#475569" font-weight="600">对应关系</text>
            </g>
        `;

        svgContent += '</svg>';
        svg.innerHTML = svgContent;
    }

    // 检查数据是否有变化
    hasDataChanged(original, fixed) {
        if (!original || !fixed || original.length !== fixed.length) return false;
        return original.some((orig, i) => this.hasRowChanged(orig, fixed[i]));
    }

    // 检查单行是否有变化
    hasRowChanged(original, fixed) {
        if (!original || !fixed) return false;
        return String(original.START_DATE) !== String(fixed.START_DATE) ||
               String(original.END_DATE) !== String(fixed.END_DATE) ||
               String(original.START_FLAG) !== String(fixed.START_FLAG) ||
               String(original.LATEST_FLAG) !== String(fixed.LATEST_FLAG);
    }

    // 工具方法：截断文本
    truncateText(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    // ==================== LLM 推理展示 ====================
    renderLlmReasoning(data) {
        // 元数据
        const metadata = document.getElementById('llmMetadata');
        if (metadata) {
            metadata.innerHTML = `
                <div class="metadata-item">
                    <label>模型</label>
                    <value>${this.escapeHtml(data.model || '-')}</value>
                </div>
                <div class="metadata-item">
                    <label>提供商</label>
                    <value>${this.escapeHtml(data.provider || '-')}</value>
                </div>
                <div class="metadata-item">
                    <label>数据行数</label>
                    <value>${data.debug?.dataRowCount || '-'}</value>
                </div>
                <div class="metadata-item">
                    <label>日志行数</label>
                    <value>${data.debug?.logRowCount || '-'}</value>
                </div>
            `;
        }

        // Prompt 展示
        if (data.debug?.prompt) {
            const container = document.getElementById('promptContainer');
            if (container) {
                const promptPreview = data.debug.prompt.substring(0, 500) + (data.debug.prompt.length > 500 ? '...' : '');
                container.innerHTML = `
                    <div class="prompt-section">
                        <div class="section-header" onclick="this.nextElementSibling.classList.toggle('collapsed')">
                            <strong>完整 Prompt</strong>
                            <button class="toggle-btn">▼</button>
                        </div>
                        <div class="section-content collapsed">
                            <pre class="sql-content">${this.escapeHtml(data.debug.prompt)}</pre>
                        </div>
                    </div>
                `;
            }
        }
    }

    // ==================== 修复可视化 ====================
    renderFixVisualization(sql) {
        const stepsList = document.getElementById('fixStepsList');
        if (!stepsList) return;

        // 解析 SQL 语句
        const statements = sql.match(/UPDATE.*?;/gis) || [];

        let stepsHtml = '';
        statements.forEach((stmt, i) => {
            const match = stmt.match(/UPDATE\s+(\w+)\s+SET\s+(.+?)\s+WHERE/i);
            if (match) {
                const [, table, sets] = match;
                const fields = sets.split(',').map(s => {
                    const [f, v] = s.split('=').map(x => x.trim().replace(/^['"]|['"]$/g, ''));
                    return `<span class="field-badge">${this.escapeHtml(f)} ← ${this.escapeHtml(v)}</span>`;
                }).join('');

                const isLast = i === statements.length - 1;
                stepsHtml += `
                    <div class="fix-step-item">
                        <div class="step-indicator">
                            <span class="step-number">${i + 1}</span>
                            ${!isLast ? '<div class="step-connector"></div>' : ''}
                        </div>
                        <div class="step-detail">
                            <div><strong>更新</strong> ${this.escapeHtml(table)}</div>
                            <div style="margin-top: 8px;">${fields}</div>
                            <pre class="sql-content" style="margin-top: 8px;">${this.escapeHtml(stmt.trim())}</pre>
                        </div>
                    </div>
                `;
            }
        });

        stepsList.innerHTML = stepsHtml || '<p style="color: var(--text-secondary);">未找到修复步骤</p>';
    }

    // ==================== 工具方法 ====================
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SQLQueryTool();
});
