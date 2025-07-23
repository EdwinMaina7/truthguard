# ============================
# BACKEND - FastAPI (main.py)
# ============================

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import joblib
import re
import nltk
from nltk.corpus import stopwords

# Download stopwords
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend (React or other clients)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load pre-trained model and vectorizer
model = joblib.load('fake_news_logreg_model.pkl')
vectorizer = joblib.load('tfidf_vectorizer.pkl')

# Request schema
class NewsInput(BaseModel):
    text: str

# Preprocess input text
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z]', ' ', text)
    tokens = text.split()
    tokens = [word for word in tokens if word not in stop_words]
    return ' '.join(tokens)

# Predict endpoint
@app.post("/predict")
def predict(news: NewsInput):
    clean = clean_text(news.text)
    vec = vectorizer.transform([clean])
    pred = model.predict(vec)[0]
    return {"prediction": "Real News" if pred == 1 else "Fake News"}

# Run with: uvicorn main:app --reload
