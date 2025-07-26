# TruthGuard - AI-Powered Fake News Detection

TruthGuard is a sophisticated fake news detection platform that leverages multiple AI models and natural language processing to analyze and verify news content.

## Features

- Real-time news content analysis
- URL and text-based input support
- Multiple AI model ensemble for improved accuracy
- Dark/Light theme support
- Responsive design
- Detailed analysis with recommendations

## Tech Stack

### Frontend
- HTML5, CSS3, JavaScript
- Font Awesome icons
- Responsive design with CSS Grid/Flexbox
- Theme persistence using localStorage

### Backend
- FastAPI (Python)
- Multiple AI Models:
  - Local trained model (RandomForest)
  - HuggingFace models ensemble
  - Google Gemini for detailed analysis
- NLTK for text processing
- scikit-learn for machine learning

## Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd news
```

2. **Set up Python virtual environment**
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file in the project root:
```
HUGGINGFACE_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

5. **Run the backend server**
```bash
cd backend
python main.py
```

6. **Serve the frontend**
```bash
cd frontend
python -m http.server 3000
```

7. **Access the application**
Open your browser and navigate to:
```
http://localhost:3000
```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /analyze` - Analyze news content
- `POST /analyze/batch` - Batch analysis (max 10 requests)

## Development

### Prerequisites
- Python 3.8+
- Node.js (optional, for development tools)
- API keys for HuggingFace and Google Gemini

### Local Development
1. Start the backend in development mode:
```bash
uvicorn main:app --reload
```

2. Open frontend/index.html in your browser or use a local server

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Developer

Edwin Maina @EdwinMaina7

