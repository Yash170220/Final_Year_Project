"""AI ESG Reporting System - Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.ingestion import router as ingestion_router
from src.api.matching import router as matching_router
from src.api.normalization import router as normalization_router
from src.api.validation import router as validation_router
from src.api.generation import router as generation_router
from src.api.provenance import router as provenance_router

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

# Include routers
app.include_router(ingestion_router)
app.include_router(matching_router)
app.include_router(normalization_router)
app.include_router(validation_router)
app.include_router(generation_router)
app.include_router(provenance_router)

@app.get("/")
async def root():
    return {"message": "AI ESG Reporting System", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
