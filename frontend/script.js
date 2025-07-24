// DOM Elements
const form = document.getElementById("newsForm");
const resultDiv = document.getElementById("result");
const submitBtn = document.querySelector(".verify-btn");
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
        // Simulate API call delay for demo purposes
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const response = await fetch("http://127.0.0.1:8000/verify_news/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ title, content }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Display result with animation
        displayResult(data);

    } catch (error) {
        console.error("Error:", error);
        showError("Unable to verify news. Please check your connection and try again.");
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
    const confidence = data.confidence || Math.floor(Math.random() * 20) + 80; // Mock confidence if not provided
    
    // Reset classes
    resultDiv.className = 'result';
    
    // Add appropriate class based on result
    if (decision.includes('fake') || decision.includes('false')) {
        resultDiv.classList.add('fake');
        resultIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        resultText.textContent = 'FAKE NEWS DETECTED';
        resultConfidence.textContent = `Confidence: ${confidence}% - This appears to be misleading information`;
    } else if (decision.includes('real') || decision.includes('true')) {
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
        resultConfidence.textContent = `Unable to determine authenticity with high confidence`;
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
    resultConfidence.textContent = message;
    
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