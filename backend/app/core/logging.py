"""
结构化日志初始化模块。

支持 DEBUG / INFO / WARNING / ERROR 级别，可选文件输出。
调用 setup_logging() 完成全局日志配置。
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

# 对外暴露标准 logging 级别常量，方便其他模块直接从此处导入
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    """
    初始化结构化日志。

    Args:
        level:       日志级别字符串，支持 DEBUG / INFO / WARNING / ERROR。
        log_file:    日志文件路径；为 None 时仅输出到 stdout。
        logger_name: 指定 logger 名称；为 None 时配置根 logger。

    Returns:
        配置好的 Logger 实例。
    """
    numeric_level = _LEVEL_MAP.get(level.upper(), logging.INFO)

    logger = logging.getLogger(logger_name)
    logger.setLevel(numeric_level)

    # 避免重复添加 handler（多次调用时幂等）
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（可选）
    if log_file:
        _ensure_dir(log_file)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger。

    应在 setup_logging() 调用之后使用，以继承全局配置。
    """
    return logging.getLogger(name)


def _ensure_dir(file_path: str) -> None:
    """确保日志文件所在目录存在。"""
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
