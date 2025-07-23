class FakeNewsDetector {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.isProcessing = false;
        
        // Configuration
        this.API_ENDPOINT = 'http://localhost:3000'; // Change this to your model's URL
        
        this.initializeEventListeners();
        this.autoResizeTextarea();
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
        
        // Add realistic processing delay
        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
        
        this.hideTypingIndicator();
        await this.addBotResponse(message);
        
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
                    <p>I've analyzed your message using my trained AI model. Here's the assessment:</p>
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
            const response = await fetch(this.API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return this.formatModelResponse(result);
            
        } catch (error) {
            console.error('Error calling model API:', error);
            
            // Fallback response when API is unavailable
            return {
                category: 'mixed',
                label: 'Analysis Unavailable',
                explanation: 'Unable to connect to the fact-checking model. Please check your internet connection and try again.',
                confidence: 0,
                color: '#6b7280',
                tip: 'The AI model is currently unavailable. Please verify information manually through credible sources.',
                error: true
            };
        }
    }

    formatModelResponse(modelResult) {
        // Adapt this function based on your model's response format
        let category, label, explanation, confidence, color, tip;
        
        // Example adaptations for common model response formats:
        
        // Format 1: {prediction: "fake", confidence: 0.85}
        if (modelResult.prediction === 'fake' || modelResult.label === 'FAKE') {
            category = 'false';
            label = 'Likely Misinformation';
            explanation = `AI analysis indicates this content is likely false or misleading. ${modelResult.reason || 'The model detected patterns commonly associated with misinformation.'}`;
            color = '#ef4444';
            tip = 'Always verify information through multiple credible sources before sharing.';
        } 
        // Format 2: {prediction: "real", confidence: 0.90}
        else if (modelResult.prediction === 'real' || modelResult.label === 'REAL') {
            category = 'true';
            label = 'Appears Credible';
            explanation = `AI analysis suggests this content appears to be credible. ${modelResult.reason || 'The model found indicators of reliable information.'}`;
            color = '#22c55e';
            tip = 'While this appears credible, consider checking the original sources for complete context.';
        } 
        // Format 3: Uncertain or mixed results
        else {
            category = 'mixed';
            label = 'Uncertain Classification';
            explanation = `The AI model couldn't make a definitive determination. ${modelResult.reason || 'The content may need human review for accurate classification.'}`;
            color = '#f59e0b';
            tip = 'Look for corroborating evidence from multiple independent, credible sources.';
        }

        // Extract confidence score (adapt field name as needed)
        // Common field names: confidence, score, probability
        confidence = Math.round((modelResult.confidence || modelResult.score || modelResult.probability || 0.5) * 100);

        return {
            category,
            label,
            explanation,
            confidence,
            color,
            tip
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
                    <span>Analyzing content</span>
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

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the chatbot when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FakeNewsDetector();
});

// Optional: Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FakeNewsDetector;
}