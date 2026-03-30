from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.market import router as market_router
from app.api.traders import router as traders_router
from app.core.config import load_config
from app.core.logging import setup_logging

try:
    cfg = load_config("config.yaml")
    setup_logging(level=cfg.logging.level, log_file=cfg.logging.file)
except Exception:
    # Fallback so API still has visible logs even when config loading fails.
    setup_logging(level="INFO", log_file="data/logs/tradecraft.log")

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

app.include_router(market_router)
app.include_router(traders_router)
