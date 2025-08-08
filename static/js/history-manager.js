// Chat history management
class HistoryManager {
    constructor() {
        this.conversations = [];
        this.currentConversationId = null;
        
        this.initializeHistory();
        this.loadConversations();
    }
    
    initializeHistory() {
        this.historyContainer = document.getElementById('chat-history');
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Load conversation on click
        if (this.historyContainer) {
            this.historyContainer.addEventListener('click', (e) => {
                const historyItem = e.target.closest('.history-item');
                if (historyItem) {
                    const conversationId = historyItem.dataset.conversationId;
                    this.loadConversation(conversationId);
                }
            });
        }
    }
    
    async loadConversations() {
        try {
            const response = await fetch('/chat/history');
            const data = await response.json();
            
            if (data.success) {
                this.conversations = data.conversations;
                this.renderHistory();
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }
    
    renderHistory() {
        if (!this.historyContainer) return;
        
        if (this.conversations.length === 0) {
            this.historyContainer.innerHTML = `
                <div class="empty-history">
                    <p>No conversations yet. Start a new chat to begin!</p>
                </div>
            `;
            return;
        }
        
        const historyHTML = this.conversations.map(conv => {
            const timeAgo = this.formatTimeAgo(conv.updated_at);
            const isActive = conv.conversation_id === this.currentConversationId;
            
            return `
                <div class="history-item ${isActive ? 'active' : ''}" data-conversation-id="${conv.conversation_id}">
                    <div class="history-title">${conv.title}</div>
                    <div class="history-time">${timeAgo} • ${conv.message_count} messages</div>
                </div>
            `;
        }).join('');
        
        this.historyContainer.innerHTML = historyHTML;
    }
    
    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/chat/conversation/${conversationId}`);
            const data = await response.json();
            
            if (data.success) {
                this.currentConversationId = conversationId;
                this.renderConversation(data.messages);
                this.updateActiveHistory();
                
                // Update chat title
                const conversation = this.conversations.find(c => c.conversation_id === conversationId);
                if (conversation && window.modernChat) {
                    window.modernChat.updateChatTitle(conversation.title);
                }
            }
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }
    
    renderConversation(messages) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        messagesContainer.innerHTML = '';
        
        messages.forEach(message => {
            if (window.modernChat) {
                window.modernChat.addMessage(
                    message.role === 'user' ? 'user' : 'bot',
                    message.content,
                    message.metadata?.sources
                );
            }
        });
    }
    
    updateActiveHistory() {
        const historyItems = document.querySelectorAll('.history-item');
        historyItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.conversationId === this.currentConversationId) {
                item.classList.add('active');
            }
        });
    }
    
    addNewConversation(conversation) {
        this.conversations.unshift(conversation);
        this.renderHistory();
    }
    
    updateConversation(conversationId, updates) {
        const index = this.conversations.findIndex(c => c.conversation_id === conversationId);
        if (index !== -1) {
            this.conversations[index] = { ...this.conversations[index], ...updates };
            this.renderHistory();
        }
    }
    
    formatTimeAgo(dateString) {
        const now = new Date();
        const date = new Date(dateString);
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }
}

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-history')) {
        window.historyManager = new HistoryManager();
    }
});
