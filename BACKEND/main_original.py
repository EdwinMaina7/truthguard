import os
import re
import joblib
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="TruthGuard API", description="Fake News Detection API", version="1.0.0")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (optional - for serving the frontend)
# Uncomment the next line if you want to serve HTML/CSS/JS files from a 'static' folder
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize variables
model = None
vectorizer = None
hf_client = None

try:
    # Load local model & vectorizer
    model = joblib.load("fake_news_logreg_model.pkl")
    logger.info("Local model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load local model: {e}")

try:
    vectorizer = joblib.load("tfidf_vectorizer.pkl")
    logger.info("Vectorizer loaded successfully")
except Exception as e:
    logger.error(f"Failed to load vectorizer: {e}")

# Check environment variables
HF_TOKEN = os.getenv("HF_TOKEN")
HF_FAKE_NEWS_MODEL = os.getenv("HF_FAKE_NEWS_MODEL")
HF_HATE_SPEECH_MODEL = os.getenv("HF_HATE_SPEECH_MODEL")

if not HF_TOKEN:
    logger.warning("HF_TOKEN not found in environment variables")
else:
    try:
        hf_client = InferenceClient(api_key=HF_TOKEN)
        logger.info("Hugging Face client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize HF client: {e}")

logger.info(f"HF_FAKE_NEWS_MODEL: {HF_FAKE_NEWS_MODEL}")
logger.info(f"HF_HATE_SPEECH_MODEL: {HF_HATE_SPEECH_MODEL}")

class NewsInput(BaseModel):
    title: str
    content: str

class NewsResponse(BaseModel):
    final_decision: str
    local_result: str = None
    hf_result: str = None
    confidence: int = None

def clean(text):
    try:
        text = re.sub(r"[^a-zA-Z ]", "", text)
        return text.lower()
    except Exception as e:
        logger.error(f"Error in clean function: {e}")
        raise

def run_local_model(text):
    try:
        if model is None or vectorizer is None:
            raise ValueError("Local model or vectorizer not loaded")
        
        cleaned = clean(text)
        features = vectorizer.transform([cleaned])
        prediction = model.predict(features)[0]
        # Get prediction probability for confidence score
        probabilities = model.predict_proba(features)[0]
        confidence = int(max(probabilities) * 100)
        
        result = "real" if prediction == 1 else "fake"
        return result, confidence
    except Exception as e:
        logger.error(f"Error in run_local_model: {e}")
        raise

def run_huggingface_model(text, model_type="fake_news"):
    try:
        if hf_client is None:
            raise ValueError("Hugging Face client not initialized")
        
        if model_type == "fake_news":
            model_name = HF_FAKE_NEWS_MODEL
        elif model_type == "hate_speech":
            model_name = HF_HATE_SPEECH_MODEL
        else:
            return "unsupported model", 0

        if not model_name:
            raise ValueError(f"Model name for {model_type} not found in environment variables")

        result = hf_client.text_classification(text, model=model_name)
        label = result[0]["label"].lower()
        confidence = int(result[0]["score"] * 100)
        return label, confidence
    except Exception as e:
        logger.error(f"Error in run_huggingface_model: {e}")
        raise

@app.get("/")
def read_root():
    return {
        "message": "TruthGuard API is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "verify_news": "/verify_news/",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "local_model_loaded": model is not None,
        "vectorizer_loaded": vectorizer is not None,
        "hf_client_initialized": hf_client is not None,
        "hf_token_present": HF_TOKEN is not None,
        "hf_fake_news_model": HF_FAKE_NEWS_MODEL,
        "hf_hate_speech_model": HF_HATE_SPEECH_MODEL
    }

@app.post("/verify_news/", response_model=NewsResponse)
def verify_news(news: NewsInput):
    try:
        logger.info(f"Received request with title: {news.title[:50]}...")
        
        # Validate input
        if not news.title.strip() or not news.content.strip():
            raise HTTPException(status_code=400, detail="Title and content cannot be empty")
        
        text = f"{news.title} {news.content}"
        
        # Check if we have the necessary components
        if model is None or vectorizer is None:
            raise HTTPException(status_code=500, detail="Local model not available")

        local_result, local_confidence = run_local_model(text)
        logger.info(f"Local model result: {local_result} (confidence: {local_confidence}%)")
        
        # Try HF model if available, otherwise use only local model
        hf_result = None
        hf_confidence = 0
        if hf_client is not None and HF_FAKE_NEWS_MODEL is not None:
            try:
                hf_result, hf_confidence = run_huggingface_model(text, model_type="fake_news")
                logger.info(f"HF model result: {hf_result} (confidence: {hf_confidence}%)")
            except Exception as e:
                logger.warning(f"HF model failed, using local only: {e}")
        
        # Decision logic with confidence calculation
        if hf_result is not None:
            avg_confidence = (local_confidence + hf_confidence) // 2
            if local_result == "fake" and ("fake" in hf_result or "label_1" in hf_result):
                final_decision = "fake"
                confidence = avg_confidence
            elif local_result == "real" and ("real" in hf_result or "label_0" in hf_result):
                final_decision = "real"
                confidence = avg_confidence
            else:
                final_decision = "uncertain"
                confidence = min(local_confidence, hf_confidence)
        else:
            # Use only local model result
            final_decision = local_result
            confidence = local_confidence
        
        logger.info(f"Final decision: {final_decision} (confidence: {confidence}%)")
        
        return NewsResponse(
            final_decision=final_decision,
            local_result=local_result,
            hf_result=hf_result,
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_news endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)