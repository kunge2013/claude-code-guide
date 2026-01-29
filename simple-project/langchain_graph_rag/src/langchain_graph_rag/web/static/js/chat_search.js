/**
 * Chat Search for Table Information
 */

let isChatOpen = false;

/**
 * Initialize chat search functionality
 */
function initChatSearch() {
    const chatToggleBtn = document.getElementById('chatToggleBtn');
    const chatCloseBtn = document.getElementById('chatCloseBtn');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const searchChatBox = document.getElementById('searchChatBox');

    // Toggle chat box
    chatToggleBtn.addEventListener('click', function() {
        isChatOpen = !isChatOpen;
        if (isChatOpen) {
            searchChatBox.classList.add('open');
            chatInput.focus();
        } else {
            searchChatBox.classList.remove('open');
        }
    });

    // Close chat box
    chatCloseBtn.addEventListener('click', function() {
        isChatOpen = false;
        searchChatBox.classList.remove('open');
    });

    // Handle form submit
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (query) {
            handleSearch(query);
            chatInput.value = '';
        }
    });

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isChatOpen) {
            isChatOpen = false;
            searchChatBox.classList.remove('open');
        }
    });
}

/**
 * Handle search query
 */
async function handleSearch(query) {
    const chatMessages = document.getElementById('chatMessages');

    // Add user message
    addChatMessage('user', query);

    // Add loading indicator
    const loadingId = addLoadingIndicator();

    try {
        const response = await fetch('/api/graph/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ q: query })
        });

        const data = await response.json();

        // Remove loading indicator
        removeMessage(loadingId);

        if (data.success && data.data.length > 0) {
            // Display results
            displaySearchResults(data.data, query);
        } else {
            // No results
            addChatMessage('assistant', `未找到与 "${escapeHtml(query)}" 相关的表。`);
        }

    } catch (error) {
        removeMessage(loadingId);
        addChatMessage('assistant', `搜索出错: ${error.message}`);
    }
}

/**
 * Display search results in chat
 */
function displaySearchResults(results, query) {
    const chatMessages = document.getElementById('chatMessages');

    let html = '<div class="chat-message assistant-message"><div class="message-content">';
    html += `<p>找到 ${results.length} 个与 "${escapeHtml(query)}" 相关的表：</p>`;
    html += '<div class="search-results">';

    results.forEach(table => {
        const props = table.properties || {};
        html += `
            <div class="search-result-item" onclick="focusTableNode('${table.id}')">
                <div class="result-header">
                    <strong class="result-table-name">${escapeHtml(table.label)}</strong>
                    <span class="result-database">${escapeHtml(props.database || '')}</span>
                </div>
                <div class="result-body">
                    ${props.comment ? `<p class="result-comment">${escapeHtml(props.comment)}</p>` : ''}
                    ${props.columns && props.columns.length > 0 ? `
                        <div class="result-columns-preview">
                            <strong>字段:</strong>
                            ${props.columns.slice(0, 5).map(col =>
                                `<span class="column-tag">${escapeHtml(col.name)}${col.primary_key ? ' 🔑' : ''}</span>`
                            ).join('')}
                            ${props.columns.length > 5 ? `<span class="column-more">...等 ${props.columns.length} 个字段</span>` : ''}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    html += '</div></div></div>';

    chatMessages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}

/**
 * Focus on a specific table node in the graph
 */
function focusTableNode(nodeId) {
    if (window.cy) {
        const node = cy.getElementById(nodeId);
        if (node.length > 0) {
            // Select the node
            cy.nodes().unselect();
            node.select();

            // Pan and zoom to the node
            cy.animate({
                center: { eles: node },
                zoom: 1.5
            }, {
                duration: 500
            });

            // Show node info
            showNodeInfo(node);
        }
    }

    // Close chat
    isChatOpen = false;
    document.getElementById('searchChatBox').classList.remove('open');
}

/**
 * Add a chat message
 */
function addChatMessage(type, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageId = 'msg-' + Date.now();

    const html = `
        <div class="chat-message ${type}-message" id="${messageId}">
            <div class="message-content">
                <p>${escapeHtml(content)}</p>
            </div>
        </div>
    `;

    chatMessages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();

    return messageId;
}

/**
 * Add loading indicator
 */
function addLoadingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const loadingId = 'loading-' + Date.now();

    const html = `
        <div class="chat-message assistant-message" id="${loadingId}">
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;

    chatMessages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();

    return loadingId;
}

/**
 * Remove a message by ID
 */
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
