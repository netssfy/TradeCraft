from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.traders import router as traders_router

app = FastAPI(
    title="TradeCraft API",
    description="TradeCraft 量化交易系统 REST API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traders_router)
