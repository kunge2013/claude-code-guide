/**
 * Query page JavaScript
 * Handles path queries, neighbor queries, and statistics
 */

// Path query
document.getElementById('findPathBtn').addEventListener('click', async function() {
    const startTable = document.getElementById('startTable').value.trim();
    const endTable = document.getElementById('endTable').value.trim();
    const maxHops = parseInt(document.getElementById('maxHops').value);
    const useLLM = document.getElementById('useLLM').checked;

    if (!startTable || !endTable) {
        alert('请输入起始表和目标表');
        return;
    }

    const btn = this;
    btn.disabled = true;
    btn.textContent = '查询中...';

    try {
        const response = await fetch('/api/graph/path', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_table: startTable,
                end_table: endTable,
                max_hops: maxHops,
                use_llm_explanation: useLLM
            })
        });

        const result = await response.json();

        const resultDiv = document.getElementById('pathResult');
        const infoDiv = document.getElementById('pathInfo');

        if (result.success && result.data.found) {
            const data = result.data;

            let html = `
                <div class="path-summary">
                    <p><strong>路径长度:</strong> ${data.length} 跳</p>
                </div>
            `;

            // Path visualization
            if (data.path && data.path.nodes) {
                const nodes = data.path.nodes.map(n => n.replace('table:', ''));
                html += `
                    <div class="path-visual">
                        ${nodes.map((n, i) => `
                            ${i > 0 ? '<span class="path-arrow">→</span>' : ''}
                            <span class="path-node">${n}</span>
                        `).join('')}
                    </div>
                `;
            }

            // Explanation
            if (data.explanation) {
                html += `
                    <div class="path-explanation">
                        <strong>路径说明:</strong>
                        <p>${data.explanation.replace(/\n/g, '<br>')}</p>
                    </div>
                `;
            }

            // SQL hint
            if (data.sql_hint) {
                html += `
                    <div class="sql-hint">
                        <strong>SQL 提示:</strong>
                        <pre>${data.sql_hint}</pre>
                    </div>
                `;
            }

            infoDiv.innerHTML = html;
            resultDiv.style.display = 'block';
        } else {
            infoDiv.innerHTML = `<p class="error">${result.data?.message || '未找到路径'}</p>`;
            resultDiv.style.display = 'block';
        }

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('pathInfo').innerHTML = `<p class="error">查询失败: ${error.message}</p>`;
        document.getElementById('pathResult').style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = '查找路径';
    }
});

// Neighbor query
document.getElementById('findNeighborsBtn').addEventListener('click', async function() {
    const tableName = document.getElementById('neighborTable').value.trim();
    const depth = parseInt(document.getElementById('neighborDepth').value);

    if (!tableName) {
        alert('请输入表名');
        return;
    }

    const btn = this;
    btn.disabled = true;
    btn.textContent = '查询中...';

    try {
        const response = await fetch('/api/graph/neighbors', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                table_name: tableName,
                depth: depth,
                include_relations: true
            })
        });

        const result = await response.json();

        const resultDiv = document.getElementById('neighborResult');
        const infoDiv = document.getElementById('neighborInfo');

        if (result.success) {
            const data = result.data;

            let html = `
                <p><strong>中心表:</strong> ${data.center_table}</p>
                <p><strong>邻居数量:</strong> ${data.total_count}</p>
                <p><strong>深度:</strong> ${data.depth}</p>
                <ul class="neighbor-list">
            `;

            data.neighbors.forEach(neighbor => {
                const directionIcon = neighbor.direction === 'out' ? '→' : '←';
                html += `
                    <li class="neighbor-item">
                        <span class="neighbor-table">${neighbor.table}</span>
                        <span class="neighbor-relation">
                            ${directionIcon} ${neighbor.relation} (${neighbor.cardinality})
                        </span>
                    </li>
                `;
            });

            html += '</ul>';
            infoDiv.innerHTML = html;
            resultDiv.style.display = 'block';
        } else {
            infoDiv.innerHTML = `<p class="error">${result.error || '查询失败'}</p>`;
            resultDiv.style.display = 'block';
        }

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('neighborInfo').innerHTML = `<p class="error">查询失败: ${error.message}</p>`;
        document.getElementById('neighborResult').style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = '查找邻居';
    }
});

// Statistics query
document.getElementById('statsBtn').addEventListener('click', async function() {
    const btn = this;
    btn.disabled = true;
    btn.textContent = '加载中...';

    try {
        const response = await fetch('/api/graph/statistics');
        const result = await response.json();

        const resultDiv = document.getElementById('statsResult');
        const infoDiv = document.getElementById('statsInfo');

        if (result.success) {
            const data = result.data;

            let html = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <strong>节点总数:</strong> ${data.node_count}
                    </div>
                    <div class="stat-item">
                        <strong>边总数:</strong> ${data.edge_count}
                    </div>
                    <div class="stat-item">
                        <strong>表节点:</strong> ${data.table_count}
                    </div>
                    <div class="stat-item">
                        <strong>列节点:</strong> ${data.column_count || 0}
                    </div>
                </div>
            `;

            if (data.relation_types && Object.keys(data.relation_types).length > 0) {
                html += `
                    <h5>关系类型分布:</h5>
                    <ul class="relation-types">
                `;
                for (const [type, count] of Object.entries(data.relation_types)) {
                    html += `<li>${type}: ${count}</li>`;
                }
                html += '</ul>';
            }

            infoDiv.innerHTML = html;
            resultDiv.style.display = 'block';
        } else {
            infoDiv.innerHTML = `<p class="error">${result.error || '加载失败'}</p>`;
            resultDiv.style.display = 'block';
        }

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('statsInfo').innerHTML = `<p class="error">加载失败: ${error.message}</p>`;
        document.getElementById('statsResult').style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = '获取统计信息';
    }
});
