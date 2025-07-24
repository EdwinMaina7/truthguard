import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import re

def check_existing_models():
    """Check if model files exist and are loadable"""
    print("=== Checking Your Trained Models ===")
    
    model_file = "fake_news_logreg_model.pkl"
    vectorizer_file = "tfidf_vectorizer.pkl"
    
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"📂 Files in directory: {[f for f in os.listdir('.') if f.endswith('.pkl')]}")
    print()
    
    models_working = True
    
    # Check model file
    if os.path.exists(model_file):
        print(f"✅ {model_file} exists ({os.path.getsize(model_file):,} bytes)")
        try:
            model = joblib.load(model_file)
            print(f"✅ Model loaded successfully - Type: {type(model)}")
            print(f"✅ Has predict method: {hasattr(model, 'predict')}")
            print(f"✅ Has predict_proba method: {hasattr(model, 'predict_proba')}")
            
            # Test model with dummy data
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                dummy_vectorizer = TfidfVectorizer()
                dummy_features = dummy_vectorizer.fit_transform(["test text"])
                # This might fail if model expects different input shape, that's ok
            except:
                pass  # Expected to fail, just checking model loads
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            models_working = False
    else:
        print(f"❌ {model_file} not found")
        models_working = False
    
    print()
    
    # Check vectorizer file
    if os.path.exists(vectorizer_file):
        print(f"✅ {vectorizer_file} exists ({os.path.getsize(vectorizer_file):,} bytes)")
        try:
            vectorizer = joblib.load(vectorizer_file)
            print(f"✅ Vectorizer loaded successfully - Type: {type(vectorizer)}")
            print(f"✅ Has transform method: {hasattr(vectorizer, 'transform')}")
            
            # Test vectorizer
            test_text = "This is a test news article"
            features = vectorizer.transform([test_text])
            print(f"✅ Vectorizer test successful - Feature shape: {features.shape}")
            
        except Exception as e:
            print(f"❌ Error loading vectorizer: {e}")
            models_working = False
    else:
        print(f"❌ {vectorizer_file} not found")
        models_working = False
    
    print()
    return models_working

def test_models_together():
    """Test if your models work together"""
    print("=== Testing Your Models Together ===")
    
    try:
        model = joblib.load("fake_news_logreg_model.pkl")
        vectorizer = joblib.load("tfidf_vectorizer.pkl")
        
        # Test with sample texts
        test_cases = [
            "Breaking news: Government announces new policy changes",
            "You won't believe this shocking discovery that doctors hate",
            "University researchers publish peer-reviewed study on climate change",
            "This one weird trick will make you rich overnight"
        ]
        
        print("🧪 Testing with sample texts:")
        print("-" * 50)
        
        for text in test_cases:
            # Clean text (same as in your backend)
            cleaned = re.sub(r"[^a-zA-Z ]", "", text).lower()
            
            # Transform and predict
            features = vectorizer.transform([cleaned])
            prediction = model.predict(features)[0]
            probabilities = model.predict_proba(features)[0]
            confidence = int(max(probabilities) * 100)
            
            result = "REAL" if prediction == 1 else "FAKE"
            
            print(f"📰 Text: {text[:60]}{'...' if len(text) > 60 else ''}")
            print(f"🎯 Prediction: {result} (Confidence: {confidence}%)")
            print()
        
        print("✅ Your models are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing models together: {e}")
        return False

def check_environment():
    """Check environment setup"""
    print("=== Checking Environment Setup ===")
    
    # Check .env file
    if os.path.exists(".env"):
        print("✅ .env file found")
        with open(".env", "r") as f:
            env_content = f.read()
            has_hf_token = "HF_TOKEN" in env_content
            has_fake_model = "HF_FAKE_NEWS_MODEL" in env_content
            
            print(f"🔑 HF_TOKEN present: {'✅' if has_hf_token else '❌'}")
            print(f"🤖 HF_FAKE_NEWS_MODEL present: {'✅' if has_fake_model else '❌'}")
    else:
        print("❌ .env file not found")
        print("💡 Create a .env file with your HuggingFace token:")
        print("   HF_TOKEN=your_token_here")
        print("   HF_FAKE_NEWS_MODEL=your_model_name")
    
    print()
    
    # Check required packages
    required_packages = [
        "fastapi", "uvicorn", "scikit-learn", "joblib", 
        "huggingface_hub", "python-dotenv", "pandas"
    ]
    
    print("📦 Checking required packages:")
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Run: pip install {package}")

def create_sample_env():
    """Create a sample .env file"""
    if not os.path.exists(".env"):
        env_content = """# HuggingFace API Token
HF_TOKEN=your_huggingface_token_here

# Your HuggingFace model names
HF_FAKE_NEWS_MODEL=your_fake_news_model_name
HF_HATE_SPEECH_MODEL=your_hate_speech_model_name

# Example models you could use:
# HF_FAKE_NEWS_MODEL=hamzab/roberta-fake-news-classification
# HF_FAKE_NEWS_MODEL=jy46604790/Fake-News-Bert-Detect
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("✅ Sample .env file created!")
        print("🔧 Please edit .env and add your actual tokens and model names")
    else:
        print("ℹ️ .env file already exists")

def main():
    print("🔍 TruthGuard Model & Environment Checker")
    print("=" * 50)
    
    # Check models
    models_ok = check_existing_models()
    
    if models_ok:
        # Test models working together
        test_models_together()
    else:
        print("❌ Your model files have issues. Please check:")
        print("   1. Are the .pkl files in the same directory as main.py?")
        print("   2. Were they created with the same Python/scikit-learn version?")
        print("   3. Are the files corrupted?")
        print()
    
    # Check environment
    check_environment()
    
    # Offer to create .env
    if not os.path.exists(".env"):
        create_env = input("\n🔧 Create sample .env file? (y/n): ").lower().strip()
        if create_env == 'y':
            create_sample_env()
    
    print("\n" + "=" * 50)
    if models_ok:
        print("✅ Your setup looks good! You can run:")
        print("   python main.py")
    else:
        print("❌ Fix the model issues first, then run:")
        print("   python main.py")

if __name__ == "__main__":
    main()