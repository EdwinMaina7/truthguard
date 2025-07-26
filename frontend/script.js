// DOM Elements
const form = document.getElementById("newsForm");
const resultDiv = document.getElementById("result");
const submitBtn = document.querySelector(".verify-btn");
const testConnectionBtn = document.getElementById("testConnection");
const btnText = document.querySelector(".btn-text");
const btnLoader = document.querySelector(".btn-loader");
const resultIcon = document.querySelector(".result-icon");
const resultText = document.querySelector(".result-text");
const resultConfidence = document.querySelector(".result-confidence");

// Add input animations
document.addEventListener('DOMContentLoaded', function() {
    // Add focus/blur effects for inputs
    const inputs = document.querySelectorAll('input, textarea');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
        
        // Add typing animation
        input.addEventListener('input', function() {
            this.style.transform = 'scale(1.02)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
        });
    });
    
    // Add page load animation
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
});

// Add connection test functionality
testConnectionBtn.addEventListener('click', async function() {
    const originalText = this.innerHTML;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    this.disabled = true;
    
    try {
        console.log("Testing server connection...");
        
        // Try to reach the root endpoint first
        const response = await fetch("http://127.0.0.1:8000/", {
            method: "GET",
            mode: 'cors'
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log("Server response:", data);
            
            // Test the health endpoint
            const healthResponse = await fetch("http://127.0.0.1:8000/health");
            const healthData = await healthResponse.json();
            
            showError(`
                ✅ <strong>Server is running!</strong><br><br>
                📊 Status: ${data.message}<br>
                🏥 Health: ${healthData.status}<br>
                🔗 Server URL: <a href="http://127.0.0.1:8000" target="_blank">http://127.0.0.1:8000</a><br>
                📚 API Docs: <a href="http://127.0.0.1:8000/docs" target="_blank">http://127.0.0.1:8000/docs</a>
            `);
            
            // Change colors to success
            resultDiv.style.background = 'linear-gradient(135deg, #c6f6d5, #9ae6b4)';
            resultDiv.style.borderColor = '#68d391';
            resultDiv.style.color = '#2f855a';
            resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
            resultText.textContent = 'CONNECTION SUCCESS';
            
        } else {
            throw new Error(`Server responded with status ${response.status}`);
        }
        
    } catch (error) {
        console.error("Connection test failed:", error);
        
        if (error.message.includes('Failed to fetch')) {
            showError(`
                🔌 <strong>Cannot connect to server!</strong><br><br>
                <strong>The server is not running. Please:</strong><br>
                1. Navigate to your project directory<br>
                2. Run: <code>python simple_test_backend.py</code><br>
                3. Or run: <code>uvicorn main:app --reload</code><br>
                4. Make sure port 8000 is not blocked<br><br>
                Expected URL: <a href="http://127.0.0.1:8000" target="_blank">http://127.0.0.1:8000</a>
            `);
        } else {
            showError(`Connection failed: ${error.message}`);
        }
    } finally {
        this.innerHTML = originalText;
        this.disabled = false;
    }
});

// Form submission handler
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = document.getElementById("title").value.trim();
    const content = document.getElementById("content").value.trim();

    // Validation
    if (!title || !content) {
        showError("Please fill in both title and content fields.");
        return;
    }

    // Start loading state
    setLoadingState(true);
    hideResult();

    try {
        // First, test if server is reachable
        console.log("Testing server connection...");
        
        const response = await fetch("http://127.0.0.1:8000/verify_news/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ title, content }),
        });

        console.log("Response status:", response.status);
        console.log("Response ok:", response.ok);

        if (!response.ok) {
            let errorMessage;
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || `HTTP ${response.status}`;
                console.log("Error data:", errorData);
            } catch {
                const errorText = await response.text();
                errorMessage = errorText || `HTTP ${response.status}`;
                console.log("Error text:", errorText);
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log("Success data:", data);
        
        // Enhanced result display
        resultDiv.classList.remove('hidden');
        
        // Calculate confidence percentage
        const confidencePercent = (data.confidence * 100).toFixed(1);
        
        // Determine verdict class and icon
        const verdictClass = data.verdict.toLowerCase();
        const verdictIcon = verdictClass === 'fake' ? '⚠️' : '✓';
        
        // Format model sources
        const modelList = data.model_sources.join(', ');
        
        // Format processing time
        const processTime = data.processing_time.toFixed(2);

        resultDiv.innerHTML = `
            <div class="result-header ${verdictClass}">
                <div class="verdict">
                    <span class="verdict-icon">${verdictIcon}</span>
                    ${data.verdict}
                </div>
                <div class="confidence-meter">
                    <div class="confidence-bar" style="width: ${confidencePercent}%"></div>
                    <div class="confidence-value">${confidencePercent}% Confidence</div>
                </div>
            </div>
            <div class="analysis-details">
                <div class="explanation">
                    <h3>Analysis Explanation:</h3>
                    <p>${data.explanation}</p>
                </div>
                <div class="model-sources">
                    <h3>AI Models Used:</h3>
                    <p>${modelList}</p>
                </div>
                <div class="processing-info">
                    <p>Analysis completed in ${processTime} seconds</p>
                    <p>Timestamp: ${new Date(data.timestamp).toLocaleString()}</p>
                </div>
            </div>
        `;
    } catch (error) {
        resultDiv.classList.remove('hidden');
        resultDiv.innerHTML = `
            <div class="error">
                <span class="error-icon">❌</span>
                <h3>Analysis Error</h3>
                <p>${error.message}</p>
                <p>Please try again with different content or URL.</p>
            </div>
        `;
    } finally {
        setLoadingState(false);
    }
});

// Set loading state
function setLoadingState(isLoading) {
    if (isLoading) {
        btnText.classList.add('hidden');
        btnLoader.classList.remove('hidden');
        submitBtn.disabled = true;
        submitBtn.style.cursor = 'not-allowed';
        submitBtn.style.transform = 'none';
    } else {
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
        submitBtn.disabled = false;
        submitBtn.style.cursor = 'pointer';
    }
}

// Display result with enhanced styling
function displayResult(data) {
    const decision = data.final_decision.toLowerCase();
    const confidence = data.confidence || 75; // Use API confidence or fallback
    
    // Reset classes
    resultDiv.className = 'result';
    
    // Add appropriate class based on result
    if (decision.includes('fake')) {
        resultDiv.classList.add('fake');
        resultIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        resultText.textContent = 'FAKE NEWS DETECTED';
        resultConfidence.textContent = `Confidence: ${confidence}% - This appears to be misleading information`;
    } else if (decision.includes('real')) {
        resultDiv.classList.add('real');
        resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
        resultText.textContent = 'LEGITIMATE NEWS';
        resultConfidence.textContent = `Confidence: ${confidence}% - This appears to be reliable information`;
    } else {
        // Neutral/uncertain result
        resultDiv.style.background = 'linear-gradient(135deg, #fef5e7, #fed7aa)';
        resultDiv.style.borderColor = '#f6ad55';
        resultDiv.style.color = '#c05621';
        resultIcon.innerHTML = '<i class="fas fa-question-circle"></i>';
        resultText.textContent = 'UNCERTAIN RESULT';
        resultConfidence.textContent = `Confidence: ${confidence}% - Unable to determine authenticity with high confidence`;
    }
    
    // Add detailed analysis if available
    if (data.local_result || data.hf_result) {
        const details = document.createElement('div');
        details.style.cssText = `
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.3);
            font-size: 0.9rem;
            opacity: 0.8;
        `;
        
        let detailText = 'Analysis Details: ';
        if (data.local_result) detailText += `Local Model: ${data.local_result}`;
        if (data.hf_result) detailText += ` | HuggingFace Model: ${data.hf_result}`;
        
        details.textContent = detailText;
        resultDiv.querySelector('.result-content').appendChild(details);
    }
    
    // Show result with animation
    showResult();
}

// Show result with animation
function showResult() {
    resultDiv.classList.remove('hidden');
    
    // Add shake animation for fake news
    if (resultDiv.classList.contains('fake')) {
        resultDiv.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            resultDiv.style.animation = '';
        }, 500);
    }
    
    // Scroll to result
    setTimeout(() => {
        resultDiv.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }, 100);
}

// Hide result
function hideResult() {
    resultDiv.classList.add('hidden');
}

// Show error message
function showError(message) {
    resultDiv.className = 'result';
    resultDiv.style.background = 'linear-gradient(135deg, #fed7d7, #feb2b2)';
    resultDiv.style.borderColor = '#fc8181';
    resultDiv.style.color = '#c53030';
    
    resultIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
    resultText.textContent = 'ERROR';
    resultConfidence.innerHTML = message; // Use innerHTML to support HTML formatting
    
    showResult();
}

// Add shake animation for errors
const shakeKeyframes = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-10px); }
        20%, 40%, 60%, 80% { transform: translateX(10px); }
    }
`;

// Inject shake animation
const styleSheet = document.createElement('style');
styleSheet.textContent = shakeKeyframes;
document.head.appendChild(styleSheet);

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to submit form
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        form.dispatchEvent(new Event('submit'));
    }
    
    // Escape to clear form
    if (e.key === 'Escape') {
        if (confirm('Clear the form?')) {
            form.reset();
            hideResult();
        }
    }
});

// Add form auto-save (using sessionStorage simulation with variables)
let autoSaveData = {
    title: '',
    content: ''
};

// Auto-save functionality
const titleInput = document.getElementById('title');
const contentInput = document.getElementById('content');

titleInput.addEventListener('input', function() {
    autoSaveData.title = this.value;
});

contentInput.addEventListener('input', function() {
    autoSaveData.content = this.value;
});

// Load auto-saved data on page load
window.addEventListener('load', function() {
    if (autoSaveData.title) titleInput.value = autoSaveData.title;
    if (autoSaveData.content) contentInput.value = autoSaveData.content;
});

// Add character counter for textarea
const maxChars = 5000;
const charCounter = document.createElement('div');
charCounter.style.cssText = `
    text-align: right;
    font-size: 0.8rem;
    color: #718096;
    margin-top: 5px;
`;

contentInput.parentElement.appendChild(charCounter);

contentInput.addEventListener('input', function() {
    const remaining = maxChars - this.value.length;
    charCounter.textContent = `${this.value.length}/${maxChars} characters`;
    
    if (remaining < 100) {
        charCounter.style.color = '#e53e3e';
    } else if (remaining < 500) {
        charCounter.style.color = '#dd6b20';
    } else {
        charCounter.style.color = '#718096';
    }
    
    if (remaining < 0) {
        this.value = this.value.substring(0, maxChars);
        charCounter.textContent = `${maxChars}/${maxChars} characters (limit reached)`;
    }
});

// Initialize character counter
charCounter.textContent = `0/${maxChars} characters`;

// Add smooth transitions for better UX
document.head.insertAdjacentHTML('beforeend', `
    <style>
        * {
            transition: all 0.3s ease;
        }
        
        input:invalid {
            border-color: #fc8181 !important;
            box-shadow: 0 0 0 3px rgba(252, 129, 129, 0.1) !important;
        }
        
        .pulse {
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
            100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0); }
        }
    </style>
`);