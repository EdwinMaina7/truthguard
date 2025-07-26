from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator, model_validator
from typing import Optional, List, Dict, Any
import httpx
import asyncio
import logging
from datetime import datetime
import re
import os
from urllib.parse import urlparse
import json
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import google.generativeai as genai
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import warnings

warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TruthGuard API",
    description="AI-powered fake news detection platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_PATH = os.getenv("MODEL_PATH", "./models/")
MODEL_FILE = os.getenv("MODEL_FILE", "fake_news_logreg_model.pkl")
VECTORIZER_FILE = os.getenv("VECTORIZER_FILE", "tfidf_vectorizer.pkl")

# Configure Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except:
    logger.warning("Could not download NLTK data")

# Global variables for model components
local_model = None
vectorizer = None
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

class NewsRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[HttpUrl] = None
    
    @model_validator(mode='after')
    def validate_input(self):
        if not self.text and not self.url:
            raise ValueError('Either text or url must be provided')
        return self

class PredictionResponse(BaseModel):
    verdict: str
    explanation: str
    timestamp: datetime
    processing_time: float
    model_sources: List[str]
    article_metadata: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None  # Make confidence optional

class HealthResponse(BaseModel):
    status: str
    models_loaded: Dict[str, bool]
    api_status: Dict[str, str]

# Text preprocessing utilities
def preprocess_text(text: str) -> str:
    """Clean and preprocess text for analysis"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Less aggressive cleaning for short texts
    if len(text.split()) < 20:
        # Only remove special characters but keep more context
        text = re.sub(r'[^\w\s.,!?]', '', text)
        return text.strip()
    
    # Regular cleaning for longer texts
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    try:
        tokens = word_tokenize(text)
        # Keep more words for context in short texts
        tokens = [lemmatizer.lemmatize(token) for token in tokens 
                 if len(token) > 1]  # Less strict filtering
        return ' '.join(tokens)
    except:
        words = text.split()
        return ' '.join([word for word in words if len(word) > 1])

# Model loading functions
async def load_local_model():
    """Load or create an improved local model"""
    global local_model, vectorizer
    
    try:
        model_file = os.path.join(MODEL_PATH, MODEL_FILE)
        vectorizer_file = os.path.join(MODEL_PATH, VECTORIZER_FILE)
        
        logger.info(f"Looking for model files:")
        logger.info(f"  Model file: {model_file} (exists: {os.path.exists(model_file)})")
        logger.info(f"  Vectorizer file: {vectorizer_file} (exists: {os.path.exists(vectorizer_file)})")
        
        if os.path.exists(model_file) and os.path.exists(vectorizer_file):
            try:
                # Try loading the model
                logger.info(f"Attempting to load model from {model_file}")
                with open(model_file, 'rb') as f:
                    local_model = pickle.load(f)
                logger.info(f"Model loaded successfully: {type(local_model)}")
                
                # Try loading the vectorizer
                logger.info(f"Attempting to load vectorizer from {vectorizer_file}")
                with open(vectorizer_file, 'rb') as f:
                    vectorizer = pickle.load(f)
                logger.info(f"Vectorizer loaded successfully: {type(vectorizer)}")
                
                return
                
            except (pickle.UnpicklingError, EOFError, ValueError) as pickle_error:
                logger.error(f"Pickle loading error: {str(pickle_error)}")
                logger.info("Attempting to load with different pickle protocols...")
                
                # Try alternative loading methods
                try:
                    import joblib
                    logger.info("Trying joblib to load model...")
                    local_model = joblib.load(model_file)
                    vectorizer = joblib.load(vectorizer_file)
                    logger.info("Successfully loaded using joblib!")
                    return
                except Exception as joblib_error:
                    logger.error(f"Joblib loading failed: {str(joblib_error)}")
                
                # Try different pickle protocols
                for protocol in [0, 1, 2, 3, 4, 5]:
                    try:
                        logger.info(f"Trying pickle protocol {protocol}...")
                        with open(model_file, 'rb') as f:
                            local_model = pickle.load(f)
                        with open(vectorizer_file, 'rb') as f:
                            vectorizer = pickle.load(f)
                        logger.info(f"Successfully loaded with protocol {protocol}!")
                        return
                    except:
                        continue
                
                logger.error("All loading methods failed, creating fallback model")
                raise pickle_error
                
        else:
            logger.warning(f"One or both model files not found, creating fallback model")
            
    except Exception as e:
        logger.error(f"Error loading local model: {str(e)}")
        logger.info("Creating fallback model for demonstration...")
        
    # Create fallback model
    try:
        logger.info("Creating enhanced fallback model...")
        vectorizer = TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 3),
            stop_words='english',
            min_df=2
        )
        
        # Use a more sophisticated model
        from sklearn.ensemble import RandomForestClassifier
        local_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        # Enhanced training data with more examples
        sample_texts = [
            # Real news examples
            "According to a peer-reviewed study published in Nature, researchers found...",
            "The government released official statistics showing economic growth...",
            "In yesterday's press conference, the health minister announced...",
            "Scientists at the university conducted experiments demonstrating...",
            "Local authorities confirmed three cases of...",
            
            # Fake news examples
            "Doctors don't want you to know this miracle cure...",
            "Share this before they take it down! Government conspiracy exposed...",
            "You won't believe what celebrities are doing to stay young...",
            "This shocking revelation will change everything you know about...",
            "Secret document reveals what the media isn't telling you..."
        ]
        sample_labels = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]  # 0=real, 1=fake
        
        X = vectorizer.fit_transform(sample_texts)
        local_model.fit(X, sample_labels)
        
        logger.info("Fallback model created and trained successfully")
        logger.info(f"Model type: {type(local_model)}")
        logger.info(f"Vectorizer type: {type(vectorizer)}")
        logger.info(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
        
    except Exception as fallback_error:
        logger.error(f"Failed to create fallback model: {str(fallback_error)}")
        local_model = None
        vectorizer = None

# Web scraping utilities
async def extract_article_content(url: str) -> Dict[str, Any]:
    """Extract article content and metadata from URL"""
    try:
        # Headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        async with httpx.AsyncClient(
            timeout=15.0,
            headers=headers,
            follow_redirects=True,
            verify=False  # Skip SSL verification for problematic sites
        ) as client:
            response = await client.get(str(url))
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside", "advertisement"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title = title.get_text().strip() if title else ""
            
            # Extract main content with multiple strategies
            content = ""
            
            # Strategy 1: Look for common article content selectors
            content_selectors = [
                'article', 
                '[role="main"]',
                '.article-content', 
                '.post-content', 
                '.entry-content',
                '.story-body',
                '.article-body',
                '.content-body',
                '.post-body',
                'main', 
                '.content',
                '.main-content',
                '#content',
                '#main-content'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text().strip() for elem in elements])
                    if len(content) > 200:  # Only use if substantial content
                        break
            
            # Strategy 2: Look for paragraphs if no main content found
            if not content or len(content) < 100:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
            
            # Strategy 3: Extract from div elements as last resort
            if not content or len(content) < 100:
                divs = soup.find_all('div', class_=lambda x: x and any(word in x.lower() for word in ['content', 'article', 'story', 'post', 'body']))
                content = ' '.join([div.get_text().strip() for div in divs])
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content).strip()
            
            if not content:
                raise ValueError("No content could be extracted from the page")
            
            # Extract metadata
            metadata = {
                'title': title,
                'url': str(url),
                'content_length': len(content),
                'domain': urlparse(str(url)).netloc,
                'extraction_method': 'web_scraping'
            }
            
            # Try to extract author
            author_selectors = [
                'meta[name="author"]',
                'meta[property="article:author"]',
                '.author',
                '.byline',
                '[rel="author"]'
            ]
            
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    if author_elem.name == 'meta':
                        metadata['author'] = author_elem.get('content', '').strip()
                    else:
                        metadata['author'] = author_elem.get_text().strip()
                    break
                
            # Try to extract publish date
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="publish_date"]',
                'meta[name="date"]',
                '.publish-date',
                '.date',
                'time[datetime]'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    if date_elem.name == 'meta':
                        metadata['published_date'] = date_elem.get('content', '').strip()
                    elif date_elem.name == 'time':
                        metadata['published_date'] = date_elem.get('datetime', date_elem.get_text()).strip()
                    else:
                        metadata['published_date'] = date_elem.get_text().strip()
                    break
            
            return {'content': content, 'metadata': metadata}
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            # Try alternative approach for 403 errors
            logger.warning(f"403 Forbidden for {url}, trying alternative method...")
            try:
                return await extract_with_fallback_method(url)
            except:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Access denied to URL (403 Forbidden). The website may be blocking automated requests. Try providing the article text directly instead."
                )
        else:
            raise HTTPException(status_code=400, detail=f"HTTP error {e.response.status_code}: {str(e)}")
    except Exception as e:
        logger.error(f"Error extracting content from URL: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Could not extract content from URL: {str(e)}")

async def extract_with_fallback_method(url: str) -> Dict[str, Any]:
    """Fallback method for difficult websites"""
    try:
        # Use requests as fallback with session
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Even more browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Cache-Control': 'max-age=0'
        }
        
        response = session.get(str(url), headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract content
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
            
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
        content = re.sub(r'\s+', ' ', content).strip()
        
        if not content:
            raise ValueError("No content extracted")
            
        title = soup.find('title')
        title = title.get_text().strip() if title else ""
        
        return {
            'content': content,
            'metadata': {
                'title': title,
                'url': str(url),
                'content_length': len(content),
                'domain': urlparse(str(url)).netloc,
                'extraction_method': 'fallback_requests'
            }
        }
        
    except Exception as e:
        raise Exception(f"Fallback extraction failed: {str(e)}")

# AI model prediction functions
async def predict_with_local_model(text: str) -> Dict[str, Any]:
    """Improved prediction using local model"""
    if not local_model or not vectorizer:
        return None
    
    try:
        # Enhanced text preprocessing
        processed_text = preprocess_text(text)
        if not processed_text:
            return None
        
        # Look for common fake news indicators
        fake_indicators = [
            'miracle cure', 'share before', 'won\'t believe',
            'doctors hate', 'secret remedy', 'conspiracy',
            'shocking truth', 'they don\'t want you'
        ]
        
        indicator_score = sum(1 for indicator in fake_indicators 
                            if indicator in processed_text.lower())
        
        # Get model prediction
        X = vectorizer.transform([processed_text])
        prediction = local_model.predict(X)[0]
        confidence = max(local_model.predict_proba(X)[0])
        
        # Adjust prediction based on indicators
        if indicator_score >= 2:
            confidence = max(confidence, 0.75)
            prediction = 1
        
        return {
            'prediction': int(prediction),
            'confidence': float(confidence),
            'model': 'local_trained'
        }
    except Exception as e:
        logger.error(f"Local model prediction error: {str(e)}")
        return None

HUGGINGFACE_MODELS = [
    {
        "name": "roberta-fake-news",
        "url": "https://api-inference.huggingface.co/models/hamzab/roberta-fake-news-classification",
        "weight": 0.3
    },
    {
        "name": "fake-news-bert",
        "url": "https://api-inference.huggingface.co/models/arifhamed/fake-news-bert-base-uncased",
        "weight": 0.25
    },
    {
        "name": "fake-news-detector",
        "url": "https://api-inference.huggingface.co/models/jy46604790/fake-news-detector-roberta",
        "weight": 0.25
    },
    {
        "name": "covid-twitter",
        "url": "https://api-inference.huggingface.co/models/LiYuan/twitter-covid19-fake-news-detection",
        "weight": 0.2
    }
]

async def predict_with_huggingface(text: str) -> List[Dict[str, Any]]:
    """Make predictions using multiple Hugging Face models"""
    if not HUGGINGFACE_API_KEY:
        return None
    
    predictions = []
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    
    async def query_model(model_info):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    model_info["url"],
                    headers=headers,
                    json={"inputs": text[:512]}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        scores = result[0]
                        fake_score = next((item['score'] for item in scores if 'fake' in item['label'].lower()), 0)
                        real_score = next((item['score'] for item in scores if 'real' in item['label'].lower()), 0)
                        
                        return {
                            'prediction': 1 if fake_score > real_score else 0,
                            'confidence': max(fake_score, real_score),
                            'model': f"huggingface_{model_info['name']}",
                            'weight': model_info['weight']
                        }
            return None
        except Exception as e:
            logger.error(f"Error with {model_info['name']}: {str(e)}")
            return None
    
    # Query all models concurrently
    tasks = [query_model(model) for model in HUGGINGFACE_MODELS]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed predictions
    predictions = [pred for pred in results if pred is not None]
    
    return predictions if predictions else None

async def generate_explanation_with_gemini(text: str, verdict: str, confidence: float) -> str:
    """Generate concise fact-checking analysis using Google Gemini"""
    if not GEMINI_API_KEY:
        return f"Content appears to be {verdict.lower()} based on our analysis."
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        As a fact-checker, analyze this content briefly. The ML model classified it as {verdict}.
        
        Content: "{text[:800]}..."

        Provide a very concise analysis (2-3 sentences) focusing on:
        - Key indicators of reliability/unreliability
        - Main points that support the classification
        - Brief guidance for readers

        Keep the response short and avoid mentioning confidence scores or percentages.
        """
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                top_p=0.8,
                top_k=40,
                max_output_tokens=200
            )
        )
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return f"Content shows characteristics typical of {verdict.lower()} news articles."

# Main prediction logic
async def analyze_news_content(text: str) -> PredictionResponse:
    """Enhanced news analysis with multiple models"""
    start_time = datetime.now()
    
    # Improved validation
    cleaned_text = text.strip()
    word_count = len(cleaned_text.split())
    
    if word_count < 10:
        text = f"{text}\n\nNote: This is a short statement requiring additional context and verification."
    
    predictions = []
    model_sources = []
    
    # Get local model prediction
    local_result = await predict_with_local_model(text)
    if local_result:
        local_result['weight'] = 0.4  # Weight for local model
        predictions.append(local_result)
        model_sources.append(local_result['model'])
    
    # Get Hugging Face predictions
    hf_results = await predict_with_huggingface(text)
    if hf_results:
        predictions.extend(hf_results)
        model_sources.extend([pred['model'] for pred in hf_results])
    
    if not predictions:
        raise HTTPException(status_code=503, detail="No models available for prediction")
    
    # Calculate weighted ensemble prediction
    total_weight = sum(pred['weight'] for pred in predictions)
    final_prediction = sum(pred['prediction'] * (pred['weight'] / total_weight) 
                         for pred in predictions)
    final_confidence = sum(pred['confidence'] * (pred['weight'] / total_weight) 
                         for pred in predictions)
    
    # More conservative threshold for fake news classification
    verdict = "FAKE" if final_prediction > 0.55 else "REAL"
    
    # Get Gemini analysis
    explanation = await generate_explanation_with_gemini(text, verdict, final_confidence)
    
    processing_time = (datetime.now() - start_time).total_seconds()
    return PredictionResponse(
        verdict=verdict,
        explanation=explanation,
        timestamp=datetime.now(),
        processing_time=processing_time,
        model_sources=model_sources
    )

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize models and services on startup"""
    logger.info("Starting TruthGuard API...")
    await load_local_model()
    logger.info("TruthGuard API ready!")

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "TruthGuard API - AI-powered fake news detection",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        models_loaded={
            "local_model": local_model is not None,
            "vectorizer": vectorizer is not None
        },
        api_status={
            "huggingface": "configured" if HUGGINGFACE_API_KEY else "not_configured",
            "gemini": "configured" if GEMINI_API_KEY else "not_configured"
        }
    )

@app.post("/analyze", response_model=PredictionResponse)
async def analyze_news(request: NewsRequest):
    """Main endpoint to analyze news content"""
    try:
        text_content = ""
        metadata = None
        
        if request.url:
            # Extract content from URL
            extracted = await extract_article_content(request.url)
            text_content = extracted['content']
            metadata = extracted['metadata']
        elif request.text:
            text_content = request.text
        else:
            raise HTTPException(status_code=400, detail="Either text or url must be provided")
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No content found to analyze")
        
        # Analyze the content
        result = await analyze_news_content(text_content)
        
        # Add metadata if available
        if metadata:
            result.article_metadata = metadata
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_news: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during analysis")

@app.post("/analyze/batch")
async def analyze_batch(requests: List[NewsRequest]):
    """Batch analysis endpoint"""
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 requests per batch")
    
    results = []
    for req in requests:
        try:
            result = await analyze_news(req)
            results.append(result)
        except Exception as e:
            results.append({
                "error": str(e),
                "timestamp": datetime.now()
            })
    
    return {"results": results}

@app.get("/models/info")
async def model_info():
    """Get information about loaded models"""
    return {
        "local_model": {
            "loaded": local_model is not None,
            "type": type(local_model).__name__ if local_model else None
        },
        "vectorizer": {
            "loaded": vectorizer is not None,
            "type": type(vectorizer).__name__ if vectorizer else None
        },
        "external_apis": {
            "huggingface": bool(HUGGINGFACE_API_KEY),
            "gemini": bool(GEMINI_API_KEY)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )