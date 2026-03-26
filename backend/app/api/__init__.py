from fastapi import FastAPI

from app.api.traders import router as traders_router

app = FastAPI(
    title="TradeCraft API",
    description="TradeCraft 量化交易系统 REST API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.include_router(traders_router)
