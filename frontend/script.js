class FakeNewsDetector {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.statusText = document.getElementById('statusText');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.isProcessing = false;
        
        // Configuration - Update this to match your backend URL
        this.API_ENDPOINT = 'http://localhost:8000'; // FastAPI default port
        
        this.initializeEventListeners();
        this.autoResizeTextarea();
        this.checkBackendConnection();
    }

    async checkBackendConnection() {
        try {
            const response = await fetch(`${this.API_ENDPOINT}/health`);
            if (response.ok) {
                const health = await response.json();
                this.connectionStatus.textContent = 'Connected';
                this.connectionStatus.className = 'connection-status connected';
                this.statusText.textContent = 'Online & Ready';
                console.log('Backend health:', health);
            } else {
                throw new Error('Backend not responding');
            }
        } catch (error) {
            this.connectionStatus.textContent = 'Disconnected';
            this.connectionStatus.className = 'connection-status disconnected';
            this.statusText.textContent = 'Backend Offline';
            console.error('Backend connection failed:', error);
        }
    }

    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
    }

    autoResizeTextarea() {
        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
        });
    }

    async handleSendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isProcessing) return;

        this.addUserMessage(message);
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';
        this.isProcessing = true;
        this.sendButton.disabled = true;

        this.showTypingIndicator();
        
        await this.addBotResponse(message);
        
        this.hideTypingIndicator();
        this.isProcessing = false;
        this.sendButton.disabled = false;
        this.chatInput.focus();
    }

    addUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user';
        messageElement.innerHTML = `
            <div class="message-avatar user-avatar">U</div>
            <div class="message-content user-message">
                ${this.escapeHtml(message)}
            </div>
        `;
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    async addBotResponse(userMessage) {
        const analysis = await this.analyzeMessage(userMessage);
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message bot';
        
        if (analysis.error) {
            messageElement.innerHTML = `
                <div class="message-avatar bot-avatar">🛡️</div>
                <div class="message-content bot-message">
                    <p>⚠️ ${analysis.explanation}</p>
                    <p style="margin-top: 15px; font-size: 14px; color: #666;">
                        💡 ${analysis.tip}
                    </p>
                </div>
            `;
        } else {
            messageElement.innerHTML = `
                <div class="message-avatar bot-avatar">🛡️</div>
                <div class="message-content bot-message">
                    <p>I've analyzed your message using AI models. Here's the assessment:</p>
                    <div class="fact-check-result ${analysis.category}">
                        <div class="fact-check-label">${analysis.label}</div>
                        <p>${analysis.explanation}</p>
                        <div class="confidence-score">
                            <span>Confidence:</span>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: 0%; background: ${analysis.color};"></div>
                            </div>
                            <span>${analysis.confidence}%</span>
                        </div>
                    </div>
                    <p style="margin-top: 15px; font-size: 14px; color: #666;">
                        💡 ${analysis.tip}
                    </p>
                    ${analysis.details ? `<details style="margin-top: 10px; font-size: 12px; color: #666;"><summary>Technical Details</summary><pre>${JSON.stringify(analysis.details, null, 2)}</pre></details>` : ''}
                </div>
            `;
        }
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();

        // Animate confidence bar (only if not an error)
        if (!analysis.error) {
            setTimeout(() => {
                const confidenceFill = messageElement.querySelector('.confidence-fill');
                if (confidenceFill) {
                    setTimeout(() => {
                        confidenceFill.style.width = `${analysis.confidence}%`;
                    }, 100);
                }
            }, 500);
        }
    }

    async analyzeMessage(message) {
        try {
            // Split message into title and content (simple approach)
            const sentences = message.split('. ');
            const title = sentences[0] || message.substring(0, 100);
            const content = sentences.slice(1).join('. ') || message;

            const response = await fetch(`${this.API_ENDPOINT}/verify_news/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title,
                    content: content
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return this.formatBackendResponse(result);
            
        } catch (error) {
            console.error('Error calling backend API:', error);
            
            // Fallback response when API is unavailable
            return {
                category: 'mixed',
                label: 'Analysis Unavailable',
                explanation: 'Unable to connect to the fact-checking backend. Please check if the server is running and try again.',
                confidence: 0,
                color: '#6b7280',
                tip: 'The AI model is currently unavailable. Please verify information manually through credible sources.',
                error: true
            };
        }
    }

    formatBackendResponse(backendResult) {
        let category, label, explanation, confidence, color, tip;
        
        console.log('Backend response:', backendResult);
        
        // Parse the final_decision from your backend
        const decision = backendResult.final_decision.toLowerCase();
        
        if (decision.includes('likely fake') || decision.includes('fake')) {
            category = 'false';
            label = 'Likely Misinformation';
            explanation = `AI analysis indicates this content is likely false or misleading. Local model: ${backendResult.local_result}, HF model: ${backendResult.hf_result || 'N/A'}`;
            color = '#ef4444';
            confidence = 85;
            tip = 'Always verify information through multiple credible sources before sharing.';
        } else if (decision.includes('likely real') || decision.includes('real')) {
            category = 'true';
            label = 'Appears Credible';
            explanation = `AI analysis suggests this content appears to be credible. Local model: ${backendResult.local_result}, HF model: ${backendResult.hf_result || 'N/A'}`;
            color = '#22c55e';
            confidence = 85;
            tip = 'While this appears credible, consider checking the original sources for complete context.';
        } else {
            category = 'mixed';
            label = 'Inconclusive Analysis';
            explanation = `The AI models provided mixed results or couldn't make a definitive determination. Local model: ${backendResult.local_result}, HF model: ${backendResult.hf_result || 'N/A'}`;
            color = '#f59e0b';
            confidence = 50;
            tip = 'Look for corroborating evidence from multiple independent, credible sources.';
        }

        return {
            category,
            label,
            explanation,
            confidence,
            color,
            tip,
            details: backendResult // Include raw response for debugging
        };
    }

    showTypingIndicator() {
        const typingElement = document.createElement('div');
        typingElement.className = 'message bot';
        typingElement.id = 'typingIndicator';
        typingElement.innerHTML = `
            <div class="message-avatar bot-avatar">🛡️</div>
            <div class="message-content bot-message">
                <div class="typing-indicator">
                    <span>Analyzing content with AI models</span>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        this.chatMessages.appendChild(typingElement);
        this.scrollToBottom();
    }

        hideTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
    }