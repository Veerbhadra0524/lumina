// Modern chat interface functionality
class ModernChat {
    constructor() {
        this.currentConversationId = null;
        this.messages = [];
        this.isTyping = false;
        
        this.initializeChat();
        this.setupEventListeners();
        this.setupSidebarToggle(); // Add this line
    }
    
    initializeChat() {
        this.messagesContainer = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.chatTitle = document.getElementById('chat-title');
        
        // Auto-resize textarea
        if (this.chatInput) {
            this.chatInput.addEventListener('input', () => {
                this.autoResizeTextarea();
            });
        }
    }
    
    setupEventListeners() {
        // Send button
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        // Enter key to send (Shift+Enter for new line)
        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // New chat button
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.startNewChat());
        }
        
        // Quick actions
        const quickActions = document.querySelectorAll('.quick-action');
        quickActions.forEach(action => {
            action.addEventListener('click', (e) => {
                this.handleQuickAction(e.target.dataset.action);
            });
        });
    }

    setupSidebarToggle() {
        // Create toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'sidebar-toggle';
        toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
        toggleBtn.title = 'Toggle Sidebar';
    
        document.body.appendChild(toggleBtn);
    
        // Toggle functionality
        toggleBtn.addEventListener('click', () => {
            const chatLayout = document.querySelector('.chat-layout');
            const sidebar = document.querySelector('.chat-sidebar');
    
            if (chatLayout && sidebar) {
                chatLayout.classList.toggle('sidebar-collapsed');
                sidebar.classList.toggle('collapsed');
    
                // Change icon
                const icon = toggleBtn.querySelector('i');
                if (chatLayout.classList.contains('sidebar-collapsed')) {
                    icon.className = 'fas fa-chevron-right';
                } else {
                    icon.className = 'fas fa-chevron-left';
                }
            }
        });
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message to UI
        this.addMessage('user', message);
        this.chatInput.value = '';
        this.autoResizeTextarea();
        this.toggleSendButton(false);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: message,
                    conversation_id: this.currentConversationId
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            if (data.success) {
                this.addMessage('assistant', data.response, data.sources);
                this.currentConversationId = data.conversation_id;

                // Update sidebar history
                if (window.historyManager) {
                    window.historyManager.loadConversations();
                }
            } else {
                this.addMessage('assistant', `Sorry, I encountered an error: ${data.error}`);
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('assistant', 'Sorry, I encountered a connection error. Please try again.');
            console.error('Chat error:', error);
        }
        
        this.toggleSendButton(true);
    }
    
    addMessage(type, content, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = type === 'user' ? 'You' : '🧠';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = this.formatMessage(content);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        // Add sources if available
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            
            let sourcesHTML = '<strong>Sources:</strong><br>';
            sources.forEach((source, index) => {
                const confidence = (source.confidence || 0).toFixed(1);
                const page = source.page_number || 'unknown';
                sourcesHTML += `• Page ${page} (confidence: ${confidence})<br>`;
            });
            
            sourcesDiv.innerHTML = sourcesHTML;
            messageContent.appendChild(sourcesDiv);
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Update conversation title if first message
        if (type === 'user' && !this.currentConversationId) {
            const title = content.length > 50 ? content.substring(0, 50) + '...' : content;
            this.updateChatTitle(title);
        }
    }
    
    formatMessage(content) {
        // Basic markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }
    
    showTypingIndicator() {
        if (this.isTyping) return;
        
        this.isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '🧠';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = '<span class="typing-dots">Thinking...</span>';
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(messageContent);
        
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        this.isTyping = false;
    }
    
    autoResizeTextarea() {
        if (!this.chatInput) return;
        
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
        
        // Enable/disable send button based on content
        const hasContent = this.chatInput.value.trim().length > 0;
        this.toggleSendButton(hasContent);
    }
    
    toggleSendButton(enabled) {
        if (this.sendBtn) {
            this.sendBtn.disabled = !enabled;
        }
    }
    
    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }
    
    updateChatTitle(title) {
        if (this.chatTitle) {
            this.chatTitle.textContent = title;
        }
    }
    
    startNewChat() {
        this.currentConversationId = null;
        this.messages = [];
        
        if (this.messagesContainer) {
            this.messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <div class="ai-avatar">🧠</div>
                    <div class="message-content">
                        <h4>New Conversation Started!</h4>
                        <p>I'm ready to help you with questions about your documents.</p>
                    </div>
                </div>
            `;
        }
        
        this.updateChatTitle('New Conversation');
        
        // Focus on input
        if (this.chatInput) {
            this.chatInput.focus();
        }
    }
    
    handleQuickAction(action) {
        switch (action) {
            case 'upload':
                window.location.href = '/upload';
                break;
            case 'example':
                this.chatInput.value = 'What is this document about?';
                this.autoResizeTextarea();
                this.chatInput.focus();
                break;
        }
    }
}

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-messages')) {
        window.modernChat = new ModernChat();
    }
});