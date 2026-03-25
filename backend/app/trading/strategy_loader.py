from __future__ import annotations

import importlib.util
import inspect
import os
from dataclasses import dataclass
from typing import List

from app.trading.strategy import Strategy


@dataclass
class LoadResult:
    success: bool
    strategy: Strategy | None
    error: str | None


class StrategyLoader:
    @staticmethod
    def load(file_path: str, params: dict = {}) -> LoadResult:
        """动态导入策略文件，实例化 Strategy 子类"""
        if not os.path.exists(file_path):
            return LoadResult(success=False, strategy=None, error=f"文件不存在: {file_path}")

        try:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except SyntaxError as e:
            return LoadResult(success=False, strategy=None, error=f"语法错误: {e}")
        except Exception as e:
            return LoadResult(success=False, strategy=None, error=f"加载失败: {e}")

        # 找到 Strategy 的子类（排除 Strategy 本身）
        strategy_classes = [
            obj for _, obj in inspect.getmembers(module, inspect.isclass)
            if issubclass(obj, Strategy) and obj is not Strategy
        ]

        if not strategy_classes:
            return LoadResult(success=False, strategy=None, error="未找到 Strategy 子类")

        try:
            strategy_cls = strategy_classes[0]
            instance = strategy_cls(**params) if params else strategy_cls()
            return LoadResult(success=True, strategy=instance, error=None)
        except Exception as e:
            return LoadResult(success=False, strategy=None, error=f"实例化失败: {e}")

    @staticmethod
    def scan(directory: str) -> List[str]:
        """扫描目录，返回所有 .py 策略文件路径"""
        if not os.path.isdir(directory):
            return []

        return [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.endswith(".py") and os.path.isfile(os.path.join(directory, f))
        ]
