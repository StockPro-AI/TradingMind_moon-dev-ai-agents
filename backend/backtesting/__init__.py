"""
Backtesting module for TradingAgents.
Validates strategy performance using historical data.
"""

from .backtest_engine import BacktestEngine
from .metrics import PerformanceMetrics

__all__ = ["BacktestEngine", "PerformanceMetrics"]
