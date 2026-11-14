
from fastapi import FastAPI

app = FastAPI(
    title="AtmoGraph API",
    description="Supply Chain Ripple Effect Predictor",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "Welcome to AtmoGraph API",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
