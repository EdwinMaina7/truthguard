import os
import re
import joblib
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import uvicorn

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Initialize variables
model = None
vectorizer = None
hf_client = None

# Check current working directory and files
current_dir = os.getcwd()
logger.info(f"📁 Current working directory: {current_dir}")
logger.info(f"📂 Files in current directory: {os.listdir(current_dir)}")

# Model file paths
model_file = "fake_news_logreg_model.pkl"
vectorizer_file = "tfidf_vectorizer.pkl"

# Check for model files existence
model_exists = os.path.exists(model_file)
vectorizer_exists = os.path.exists(vectorizer_file)

logger.info(f"🔍 Looking for model file: {model_file}")
logger.info(f"{'✅' if model_exists else '❌'} Model file exists: {model_exists}")
if model_exists:
    logger.info(f"📏 Model file size: {os.path.getsize(model_file)} bytes")

logger.info(f"🔍 Looking for vectorizer file: {vectorizer_file}")
logger.info(f"{'✅' if vectorizer_exists else '❌'} Vectorizer file exists: {vectorizer_exists}")
if vectorizer_exists:
    logger.info(f"📏 Vectorizer file size: {os.path.getsize(vectorizer_file)} bytes")

# Try to load local model with detailed error reporting
try:
    if not model_exists:
        raise FileNotFoundError(f"Model file '{model_file}' not found in {current_dir}")
    
    logger.info("🔄 Attempting to load model...")
    model = joblib.load(model_file)
    logger.info(f"✅ Local model loaded successfully. Type: {type(model)}")
    logger.info(f"🔧 Model has predict method: {hasattr(model, 'predict')}")
    logger.info(f"🔧 Model has predict_proba method: {hasattr(model, 'predict_proba')}")
except FileNotFoundError as e:
    logger.error(f"❌ {e}")
    logger.error("💡 Hint: Make sure your .pkl files are in the same directory as main.py")
except Exception as e:
    logger.error(f"❌ Failed to load local model: {type(e).__name__}: {e}")

# Try to load vectorizer with detailed error reporting
try:
    if not vectorizer_exists:
        raise FileNotFoundError(f"Vectorizer file '{vectorizer_file}' not found in {current_dir}")
    
    logger.info("🔄 Attempting to load vectorizer...")
    vectorizer = joblib.load(vectorizer_file)
    logger.info(f"✅ Vectorizer loaded successfully. Type: {type(vectorizer)}")
    logger.info(f"🔧 Vectorizer has transform method: {hasattr(vectorizer, 'transform')}")
except FileNotFoundError as e:
    logger.error(f"❌ {e}")
    logger.error("💡 Hint: Make sure your .pkl files are in the same directory as main.py")
except Exception as e:
    logger.error(f"❌ Failed to load vectorizer: {type(e).__name__}: {e}")

# Check environment variables
HF_TOKEN = os.getenv("HF_TOKEN")
HF_FAKE_NEWS_MODEL = os.getenv("HF_FAKE_NEWS_MODEL")
HF_HATE_SPEECH_MODEL = os.getenv("HF_HATE_SPEECH_MODEL")

logger.info(f"🔑 HF_TOKEN present: {HF_TOKEN is not None}")
logger.info(f"🤖 HF_FAKE_NEWS_MODEL: {HF_FAKE_NEWS_MODEL}")
logger.info(f"🤖 HF_HATE_SPEECH_MODEL: {HF_HATE_SPEECH_MODEL}")

if not HF_TOKEN:
    logger.warning("⚠️ HF_TOKEN not found in environment variables")
    logger.info("💡 Add HF_TOKEN=your_token to your .env file for Hugging Face models")
else:
    try:
        hf_client = InferenceClient(api_key=HF_TOKEN)
        logger.info("✅ Hugging Face client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize HF client: {e}")

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
        logger.error(f"❌ Error in clean function: {e}")
        raise

def run_local_model(text):
    try:
        if model is None:
            raise ValueError("Local model is None - not loaded properly")
        if vectorizer is None:
            raise ValueError("Vectorizer is None - not loaded properly")
        
        logger.info(f"🔍 Processing text of length: {len(text)}")
        cleaned = clean(text)
        logger.info(f"🧹 Cleaned text length: {len(cleaned)}")
        
        features = vectorizer.transform([cleaned])
        logger.info(f"📊 Features shape: {features.shape}")
        
        prediction = model.predict(features)[0]
        logger.info(f"🎯 Raw prediction: {prediction}")
        
        # Get prediction probability for confidence score
        try:
            probabilities = model.predict_proba(features)[0]
            confidence = int(max(probabilities) * 100)
            logger.info(f"📈 Prediction probabilities: {probabilities}")
            logger.info(f"📊 Confidence: {confidence}%")
        except Exception as e:
            logger.warning(f"⚠️ Could not get probabilities: {e}")
            confidence = 75  # Default confidence
        
        result = "real" if prediction == 1 else "fake"
        logger.info(f"✅ Final local result: {result} (confidence: {confidence}%)")
        
        return result, confidence
    except Exception as e:
        logger.error(f"❌ Error in run_local_model: {type(e).__name__}: {e}")
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

        logger.info(f"🤖 Calling HF model: {model_name}")
        result = hf_client.text_classification(text, model=model_name)
        logger.info(f"📤 HF raw result: {result}")
        
        label = result[0]["label"].lower()
        confidence = int(result[0]["score"] * 100)
        logger.info(f"✅ HF result: {label} (confidence: {confidence}%)")
        
        return label, confidence
    except Exception as e:
        logger.error(f"❌ Error in run_huggingface_model: {e}")
        raise

@app.get("/")
def read_root():
    logger.info("🏠 Root endpoint accessed")
    return {
        "message": "TruthGuard API with ML Models",
        "version": "1.0.0",
        "models_status": {
            "local_model_loaded": model is not None,
            "vectorizer_loaded": vectorizer is not None,
            "hf_client_ready": hf_client is not None,
            "ready_for_analysis": model is not None and vectorizer is not None
        },
        "endpoints": {
            "health": "/health",
            "verify_news": "/verify_news/",
            "debug": "/debug",
            "docs": "/docs"
        }
    }

@app.get("/debug")
def debug_info():
    """Detailed debug information"""
    logger.info("🔍 Debug endpoint accessed")
    return {
        "system_info": {
            "working_directory": current_dir,
            "files_in_directory": os.listdir("."),
            "model_file_exists": os.path.exists(model_file),
            "vectorizer_file_exists": os.path.exists(vectorizer_file)
        },
        "models_status": {
            "model_loaded": model is not None,
            "vectorizer_loaded": vectorizer is not None,
            "model_type": str(type(model)) if model else None,
            "vectorizer_type": str(type(vectorizer)) if vectorizer else None
        },
        "huggingface_status": {
            "hf_client_initialized": hf_client is not None,
            "hf_token_present": HF_TOKEN is not None,
            "hf_fake_news_model": HF_FAKE_NEWS_MODEL,
            "hf_hate_speech_model": HF_HATE_SPEECH_MODEL
        }
    }

@app.get("/health")
def health_check():
    logger.info("🏥 Health check accessed")
    can_process = model is not None and vectorizer is not None
    
    return {
        "status": "healthy" if can_process else "degraded",
        "local_model_loaded": model is not None,
        "vectorizer_loaded": vectorizer is not None,
        "hf_client_initialized": hf_client is not None,
        "can_process_requests": can_process,
        "message": "Ready for news analysis" if can_process else "Local models not loaded - check server logs"
    }

@app.post("/verify_news/", response_model=NewsResponse)
def verify_news(news: NewsInput):
    logger.info("📰 === New News Verification Request ===")
    logger.info(f"📝 Title: {news.title[:100]}{'...' if len(news.title) > 100 else ''}")
    logger.info(f"📄 Content length: {len(news.content)} characters")
    
    try:
        # Validate input
        if not news.title.strip() or not news.content.strip():
            logger.warning("❌ Empty title or content provided")
            raise HTTPException(status_code=400, detail="Title and content cannot be empty")
        
        text = f"{news.title} {news.content}"
        logger.info(f"🔗 Combined text length: {len(text)} characters")
        
        # Check if we have the necessary components for local model
        if model is None or vectorizer is None:
            error_msg = "Local ML models not loaded. Check server logs for model loading errors."
            logger.error(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        # Run local model
        logger.info("🚀 Running local model analysis...")
        local_result, local_confidence = run_local_model(text)
        logger.info(f"✅ Local model result: {local_result} ({local_confidence}% confidence)")
        
        # Try HF model if available, otherwise use only local model
        hf_result = None
        hf_confidence = 0
        if hf_client is not None and HF_FAKE_NEWS_MODEL is not None:
            try:
                logger.info("🚀 Running Hugging Face model analysis...")
                hf_result, hf_confidence = run_huggingface_model(text, model_type="fake_news")
                logger.info(f"✅ HF model result: {hf_result} ({hf_confidence}% confidence)")
            except Exception as e:
                logger.warning(f"⚠️ HF model failed, using local only: {e}")
        else:
            logger.info("ℹ️ Hugging Face model not available, using local model only")
        
        # Decision logic with confidence calculation
        if hf_result is not None:
            avg_confidence = (local_confidence + hf_confidence) // 2
            logger.info(f"🧮 Combining results - Local: {local_result}, HF: {hf_result}")
            
            # Map HF labels to our format
            hf_normalized = "fake" if "fake" in hf_result.lower() or "label_1" in hf_result.lower() else "real"
            
            if local_result == "fake" and hf_normalized == "fake":
                final_decision = "fake"
                confidence = avg_confidence
            elif local_result == "real" and hf_normalized == "real":
                final_decision = "real"
                confidence = avg_confidence
            else:
                final_decision = "uncertain"
                confidence = min(local_confidence, hf_confidence)
        else:
            # Use only local model result
            final_decision = local_result
            confidence = local_confidence
        
        logger.info(f"🎯 Final decision: {final_decision} (confidence: {confidence}%)")
        logger.info("📰 === Analysis Complete ===")
        
        return NewsResponse(
            final_decision=final_decision,
            local_result=local_result,
            hf_result=hf_result,
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in verify_news endpoint: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 TruthGuard Server Starting Up...")
    logger.info(f"🤖 Local Model Status: {'✅ Loaded' if model else '❌ Not Loaded'}")
    logger.info(f"🔧 Vectorizer Status: {'✅ Loaded' if vectorizer else '❌ Not Loaded'}")
    logger.info(f"🌐 HuggingFace Client: {'✅ Ready' if hf_client else '❌ Not Available'}")
    
    if model and vectorizer:
        logger.info("✅ Server ready for news analysis!")
    else:
        logger.warning("⚠️ Server started but ML models not loaded - check your .pkl files")

def start_server():
    """Start the server"""
    print("=" * 60)
    print("🚀 TruthGuard - Fake News Detection API")
    print("🤖 Using your trained models + HuggingFace APIs")
    print("🌐 Server URL: http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("🔍 Debug Info: http://127.0.0.1:8000/debug")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()