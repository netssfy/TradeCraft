from app.engine.core import Engine
from app.core.logging import setup_logging

setup_logging(level="INFO", log_file="data/logs/tradecraft.log")

engine = Engine.from_config("config.yaml")
engine.start()