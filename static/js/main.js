class LuminaRAG {
    constructor() {
        this.chatMessages = document.getElementById('chat-messages');
        this.queryInput = document.getElementById('query-input');
        this.sendBtn = document.getElementById('send-btn');
        this.statusBtn = document.getElementById('status-btn');
        this.statusPanel = document.getElementById('status-panel');
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        this.sendBtn.addEventListener('click', () => this.sendQuery());
        this.queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendQuery();
        });
        
        if (this.statusBtn) {
            this.statusBtn.addEventListener('click', () => this.toggleStatus());
        }
    }
    
    async sendQuery() {
        const query = this.queryInput.value.trim();
        if (!query) return;
        
        // Add user message
        this.addMessage(query, 'user');
        this.queryInput.value = '';
        this.setSendingState(true);
        
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addMessage(data.answer, 'bot', data.sources);
            } else {
                this.addMessage(`Sorry, I encountered an error: ${data.error}`, 'bot');
            }
            
        } catch (error) {
            this.addMessage('Sorry, I encountered a connection error. Please try again.', 'bot');
        } finally {
            this.setSendingState(false);
        }
    }
    
    addMessage(content, type, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        let messageHtml = `<div class="message-content"><p>${content}</p>`;
        
        if (sources && sources.length > 0) {
            messageHtml += '<div class="sources"><small><strong>Sources:</strong><ul>';
            sources.forEach((source, index) => {
                const page = source.page_number || 'unknown';
                const confidence = (source.confidence || 0).toFixed(1);
                messageHtml += `<li>Page ${page} (confidence: ${confidence})</li>`;
            });
            messageHtml += '</ul></small></div>';
        }
        
        messageHtml += '</div>';
        messageDiv.innerHTML = messageHtml;
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    setSendingState(sending) {
        this.sendBtn.disabled = sending;
        this.queryInput.disabled = sending;
        this.sendBtn.textContent = sending ? 'Sending...' : 'Send';
    }
    
    async toggleStatus() {
        if (this.statusPanel.classList.contains('hidden')) {
            await this.loadStatus();
            this.statusPanel.classList.remove('hidden');
            this.statusBtn.textContent = '❌ Hide Status';
        } else {
            this.statusPanel.classList.add('hidden');
            this.statusBtn.textContent = '📊 Status';
        }
    }
    
    async loadStatus() {
        const statusContent = document.getElementById('status-content');
        statusContent.innerHTML = 'Loading...';
        
        try {
            const response = await fetch('/status');
            const data = await response.json();
            
            if (data.success) {
                statusContent.innerHTML = `
                    <div class="status-grid">
                        <div><strong>Documents Indexed:</strong> ${data.documents_indexed}</div>
                        <div><strong>Embedding Model:</strong> ${data.embedding_model}</div>
                        <div><strong>Local LLM:</strong> ${data.use_local_llm ? 'Enabled' : 'Disabled'}</div>
                        <div><strong>Status:</strong> ${data.status}</div>
                    </div>
                `;
            } else {
                statusContent.innerHTML = `Error loading status: ${data.error}`;
            }
        } catch (error) {
            statusContent.innerHTML = `Connection error: ${error.message}`;
        }
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new LuminaRAG();
});
