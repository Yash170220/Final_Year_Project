"""AI ESG Reporting System - Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI ESG Reporting System",
    description="Automated ESG reporting with AI-powered data processing",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI ESG Reporting System", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
