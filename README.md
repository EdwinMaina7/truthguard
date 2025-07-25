
# 🛡️ TruthGuard

**TruthGuard** is an AI-powered fake news detection system built using **FastAPI**, **machine learning models**, and a simple **HTML/CSS/JavaScript frontend**. It provides a user-friendly interface to verify the credibility of news articles in real time.

## 🚀 Features

- RESTful API built with FastAPI
- Integrated machine learning model for news verification
- `/verify_news/` endpoint to check text authenticity
- Simple HTML/CSS/JS frontend for interaction
- Hugging Face & sklearn model support
- Environment-based config with `.env`

## 📂 Project Structure

```

truthguard/
├── BACKEND/              # FastAPI app with ML model
│   ├── main.py
│   ├── model/            # Your model, vectorizer, etc.
│   └── .env              # (ignored) contains Hugging Face token
├── frontend/             # Static frontend files
│   ├── index.html
│   ├── script.js
│   └── style.css
├── FAKE NEWS/            # Large CSV datasets (ignored from Git)
│   ├── Fake.csv
│   └── True.csv
├── .gitignore
└── README.md

````

## ⚙️ Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
````

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> Required packages include:
> fastapi, uvicorn, scikit-learn, transformers, pydantic, python-dotenv

### 3. Run the App

```bash
uvicorn main:app --reload
```

Visit: [http://localhost:8000](http://localhost:8000)

## 📡 API Endpoints

| Endpoint        | Method | Description                   |
| --------------- | ------ | ----------------------------- |
| `/health`       | GET    | Health check                  |
| `/verify_news/` | POST   | Submit news text for analysis |
| `/docs`         | GET    | Swagger UI (interactive docs) |

## 🧪 Example Usage

**POST** `/verify_news/`

Request body:

```json
{
  "text": "The government has approved a new policy..."
}
```

Response:

```json
{
  "label": "REAL",
  "confidence": 0.92
}
```

## 🔐 Environment Variables

Create a `.env` file in `BACKEND/`:

```env
HF_TOKEN=your_huggingface_token_here
```

> ⚠️ Do not commit real tokens. Add `.env` to `.gitignore` and use a `.env.example` for safe sharing.

## ⚠️ Notes

* Large files (`Fake.csv`, `True.csv`) are ignored from Git — consider using Git LFS or external hosting.
* GitHub blocks pushes with secrets — remove them from commit history before pushing.
* Use `git filter-repo` or `BFG` to clean secrets and large files from your repo history if needed.

## ✅ TODO / Improvements

* [ ] Add user authentication 
* [ ] Log and analyze prediction history

## 📄 License

MIT License

## 👨‍💻 Author

**Edwin Maina**
GitHub: [@EdwinMaina7](https://github.com/EdwinMaina7)

```

