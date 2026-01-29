/**
 * Graph visualization using Cytoscape.js
 */

// Global cytoscape instance
let cy = null;

/**
 * Initialize the graph visualization
 */
async function initGraph() {
    const cyContainer = document.getElementById('cy');

    // Initialize with empty graph
    cy = cytoscape({
        container: cyContainer,
        elements: [],
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': 'data(color)',
                    'label': 'data(label)',
                    'width': 'data(size)',
                    'height': 'data(size)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'color': '#fff',
                    'text-outline-color': '#000',
                    'text-outline-width': '2px',
                    'border-width': 2,
                    'border-color': '#fff'
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'border-width': 4,
                    'border-color': '#f39c12'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 'data(width)',
                    'line-color': 'data(color)',
                    'target-arrow-color': 'data(color)',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'font-size': '10px',
                    'text-rotation': 'autorotate',
                    'text-margin-y': -10,
                    'color': '#7f8c8d',
                    'text-background-color': '#fff',
                    'text-background-opacity': 0.8,
                    'text-background-padding': '2px'
                }
            },
            {
                selector: 'edge:selected',
                style: {
                    'line-color': '#f39c12',
                    'target-arrow-color': '#f39c12'
                }
            }
        ],
        layout: {
            name: 'cose',
            animate: true,
            animationDuration: 500,
            fit: true,
            padding: 50
        },
        minZoom: 0.1,
        maxZoom: 3
    });

    // Add event listeners
    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        showNodeInfo(node);
    });

    cy.on('tap', function(evt) {
        if (evt.target === cy) {
            hideNodeInfo();
        }
    });

    // Load graph data
    await loadGraphData();
}

/**
 * Load graph data from the server
 */
async function loadGraphData() {
    updateStatus('加载中...');

    try {
        // Fetch nodes and edges
        const [nodesRes, edgesRes] = await Promise.all([
            fetch('/api/graph/nodes'),
            fetch('/api/graph/edges')
        ]);

        if (!nodesRes.ok || !edgesRes.ok) {
            throw new Error('Failed to load graph data');
        }

        const nodesData = await nodesRes.json();
        const edgesData = await edgesRes.json();

        if (!nodesData.success || !edgesData.success) {
            throw new Error('Invalid response from server');
        }

        // Update stats
        document.getElementById('nodeCount').textContent = nodesData.count;
        document.getElementById('edgeCount').textContent = edgesData.count;

        // Convert to Cytoscape format
        const elements = {
            nodes: nodesData.data.map(node => ({
                data: node
            })),
            edges: edgesData.data.map(edge => ({
                data: edge
            }))
        };

        // Update graph
        cy.json({ elements: elements });

        // Apply layout
        const layout = cy.layout({
            name: 'cose',
            animate: true,
            animationDuration: 500,
            fit: true,
            padding: 50
        });
        layout.run();

        updateStatus('就绪', 'success');

    } catch (error) {
        console.error('Error loading graph:', error);
        updateStatus('加载失败: ' + error.message, 'error');
    }
}

/**
 * Update graph status
 */
function updateStatus(text, type = 'info') {
    const statusEl = document.getElementById('graphStatus');
    statusEl.textContent = text;

    statusEl.className = 'stat-value';
    if (type === 'error') {
        statusEl.style.color = '#e74c3c';
    } else if (type === 'success') {
        statusEl.style.color = '#27ae60';
    } else {
        statusEl.style.color = '#2c3e50';
    }
}

/**
 * Show node information panel
 */
function showNodeInfo(node) {
    const panel = document.getElementById('infoPanel');
    const infoEl = document.getElementById('nodeInfo');

    const data = node.data();
    const props = data.properties || {};

    let html = `
        <div class="node-detail">
            <strong>表名:</strong> ${data.label}
        </div>
    `;

    if (props.database) {
        html += `
            <div class="node-detail">
                <strong>数据库:</strong> ${props.database}
            </div>
        `;
    }

    if (props.comment) {
        html += `
            <div class="node-detail">
                <strong>注释:</strong> ${props.comment}
            </div>
        `;
    }

    if (props.row_count !== undefined) {
        html += `
            <div class="node-detail">
                <strong>行数:</strong> ${props.row_count.toLocaleString()}
            </div>
        `;
    }

    if (props.primary_keys && props.primary_keys.length > 0) {
        html += `
            <div class="node-detail">
                <strong>主键:</strong> ${props.primary_keys.join(', ')}
            </div>
        `;
    }

    if (props.semantic_labels && props.semantic_labels.length > 0) {
        html += `
            <div class="node-detail">
                <strong>语义标签:</strong> ${props.semantic_labels.join(', ')}
            </div>
        `;
    }

    // Display columns information
    if (props.columns && props.columns.length > 0) {
        html += `
            <div class="node-detail-section">
                <strong>字段列表 (${props.columns.length}):</strong>
                <table class="columns-table">
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>类型</th>
                            <th>主键</th>
                            <th>可空</th>
                            <th>注释</th>
                            <th>别名</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        props.columns.forEach(col => {
            const aliases = col.aliases && col.aliases.length > 0
                ? col.aliases.map(a => escapeHtml(a)).join(', ')
                : '';
            html += `
                <tr>
                    <td>${escapeHtml(col.name)}</td>
                    <td>${escapeHtml(col.type)}</td>
                    <td>${col.primary_key ? '✓' : ''}</td>
                    <td>${col.nullable ? '✓' : ''}</td>
                    <td>${escapeHtml(col.comment || '')}</td>
                    <td class="aliases-cell">${aliases}</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;
    }

    infoEl.innerHTML = html;
    panel.style.display = 'block';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Hide node information panel
 */
function hideNodeInfo() {
    const panel = document.getElementById('infoPanel');
    panel.style.display = 'none';
}
