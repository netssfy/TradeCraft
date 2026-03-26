from app.engine.core import Engine
from app.core.logging import setup_logging

setup_logging(level="INFO", log_file="data/logs/tradecraft.log")

engine = Engine.from_traders_dir(config_path="config.yaml", traders_dir="data/traders")
engine.start()
