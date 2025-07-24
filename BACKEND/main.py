import os
import re
import joblib
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

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
        return "real" if prediction == 1 else "fake"
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
            return "unsupported model"

        if not model_name:
            raise ValueError(f"Model name for {model_type} not found in environment variables")

        result = hf_client.text_classification(text, model=model_name)
        return result[0]["label"].lower()
    except Exception as e:
        logger.error(f"Error in run_huggingface_model: {e}")
        raise

@app.get("/")
def read_root():
    return {"message": "FastAPI server is running"}

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

@app.post("/verify_news/")
def verify_news(news: NewsInput):
    try:
        logger.info(f"Received request with title: {news.title[:50]}...")
        
        text = f"{news.title} {news.content}"
        
        # Check if we have the necessary components
        if model is None or vectorizer is None:
            raise HTTPException(status_code=500, detail="Local model not available")

        local_result = run_local_model(text)
        logger.info(f"Local model result: {local_result}")
        
        # Try HF model if available, otherwise use only local model
        hf_result = None
        if hf_client is not None and HF_FAKE_NEWS_MODEL is not None:
            try:
                hf_result = run_huggingface_model(text, model_type="fake_news")
                logger.info(f"HF model result: {hf_result}")
            except Exception as e:
                logger.warning(f"HF model failed, using local only: {e}")
        
        # Decision logic
        if hf_result is not None:
            if local_result == "fake" and hf_result == "fake":
                final_decision = "likely fake"
            elif local_result == "real" and hf_result == "real":
                final_decision = "likely real"
            else:
                final_decision = "inconclusive"
        else:
            # Use only local model result
            final_decision = f"likely {local_result} (local model only)"
        
        logger.info(f"Final decision: {final_decision}")
        
        return {
            "final_decision": final_decision,
            "local_result": local_result,
            "hf_result": hf_result
        }
        
    except Exception as e:
        logger.error(f"Error in verify_news endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")