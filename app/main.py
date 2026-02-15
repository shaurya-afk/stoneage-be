from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from app.api.v1 import extract_router
from app.api.v1.auth_router import auth_router

app = FastAPI(title="Data Extraction API", description="API for extracting data from documents")

app.include_router(extract_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

