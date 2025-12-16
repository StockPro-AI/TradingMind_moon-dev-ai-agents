"""
Backtesting engine for TradingAgents.
Uses free yfinance data to validate strategy performance.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from .metrics import PerformanceMetrics


@dataclass
class TradeResult:
    """Result of a single trade recommendation."""
    date: str
    ticker: str
    decision: str  # BUY, SELL, HOLD
    entry_price: float
    exit_price: float  # Price after holding_days
    return_pct: float
    holding_days: int
    actual_direction: str  # UP, DOWN, FLAT


@dataclass
class BacktestResult:
    """Complete backtest results."""
    ticker: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    avg_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[TradeResult]
    benchmark_return: float  # SPY return for comparison
    alpha: float  # Return above benchmark


class BacktestEngine:
    """
    Backtesting engine for validating trading recommendations.

    Uses free yfinance data to test strategy performance over
    a configurable lookback period (default: 3 months for short-term trading).
    """

    def __init__(
        self,
        lookback_months: int = 3,
        holding_days: int = 5,
        benchmark_ticker: str = "SPY"
    ):
        """
        Initialize backtesting engine.

        Args:
            lookback_months: How many months of historical data to test (default 3)
            holding_days: How long to hold after each recommendation (default 5 days)
            benchmark_ticker: Ticker to compare against (default SPY)
        """
        self.lookback_months = lookback_months
        self.holding_days = holding_days
        self.benchmark_ticker = benchmark_ticker
        self.metrics = PerformanceMetrics()

    def get_historical_prices(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical price data using free yfinance API.

        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            stock = yf.Ticker(ticker)
            # Add buffer days for holding period calculations
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=self.holding_days + 10)
            df = stock.history(start=start_date, end=end_dt.strftime("%Y-%m-%d"))

            if df.empty:
                print(f"Warning: No data found for {ticker}")
                return pd.DataFrame()

            # Clean up index
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df

        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    def simulate_trade(
        self,
        df: pd.DataFrame,
        trade_date: str,
        decision: str
    ) -> Optional[TradeResult]:
        """
        Simulate a single trade based on a recommendation.

        Args:
            df: Price DataFrame
            trade_date: Date of recommendation
            decision: BUY, SELL, or HOLD

        Returns:
            TradeResult or None if data unavailable
        """
        try:
            trade_dt = pd.to_datetime(trade_date)

            # Find the actual trading day (may be weekend/holiday)
            available_dates = df.index[df.index >= trade_dt]
            if len(available_dates) == 0:
                return None

            entry_date = available_dates[0]
            entry_idx = df.index.get_loc(entry_date)

            # Get exit date (holding_days later)
            exit_idx = min(entry_idx + self.holding_days, len(df) - 1)
            exit_date = df.index[exit_idx]

            entry_price = df.loc[entry_date, "Close"]
            exit_price = df.loc[exit_date, "Close"]

            # Calculate return based on decision
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100

            if decision == "BUY":
                return_pct = price_change_pct  # Long position
            elif decision == "SELL":
                return_pct = -price_change_pct  # Short position (inverse)
            else:  # HOLD
                return_pct = 0  # No position

            # Determine actual direction
            if price_change_pct > 0.5:
                actual_direction = "UP"
            elif price_change_pct < -0.5:
                actual_direction = "DOWN"
            else:
                actual_direction = "FLAT"

            return TradeResult(
                date=trade_date,
                ticker=df.name if hasattr(df, 'name') else "UNKNOWN",
                decision=decision,
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=return_pct,
                holding_days=exit_idx - entry_idx,
                actual_direction=actual_direction
            )

        except Exception as e:
            print(f"Error simulating trade on {trade_date}: {e}")
            return None

    def run_backtest(
        self,
        ticker: str,
        recommendations: List[Dict[str, str]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> BacktestResult:
        """
        Run backtest on a series of recommendations.

        Args:
            ticker: Stock symbol
            recommendations: List of {"date": "YYYY-MM-DD", "decision": "BUY/SELL/HOLD"}
            start_date: Override start date
            end_date: Override end date

        Returns:
            BacktestResult with performance metrics
        """
        # Calculate date range
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_dt = datetime.now() - timedelta(days=self.lookback_months * 30)
            start_date = start_dt.strftime("%Y-%m-%d")

        # Fetch price data
        df = self.get_historical_prices(ticker, start_date, end_date)
        if df.empty:
            return self._empty_result(ticker, start_date, end_date)

        # Simulate each trade
        trades = []
        for rec in recommendations:
            result = self.simulate_trade(df, rec["date"], rec["decision"])
            if result:
                result.ticker = ticker
                trades.append(result)

        if not trades:
            return self._empty_result(ticker, start_date, end_date)

        # Calculate metrics
        returns = [t.return_pct for t in trades]
        winning = [t for t in trades if t.return_pct > 0]
        losing = [t for t in trades if t.return_pct < 0]

        # Get benchmark return
        benchmark_return = self._get_benchmark_return(start_date, end_date)

        # Calculate performance metrics
        total_return = sum(returns)
        avg_return = np.mean(returns) if returns else 0
        win_rate = len(winning) / len(trades) if trades else 0
        max_drawdown = self.metrics.calculate_max_drawdown(returns)
        sharpe_ratio = self.metrics.calculate_sharpe_ratio(returns)
        alpha = total_return - benchmark_return

        return BacktestResult(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            total_return=total_return,
            avg_return=avg_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            benchmark_return=benchmark_return,
            alpha=alpha
        )

    def run_walk_forward_test(
        self,
        ticker: str,
        trading_graph,
        test_dates: Optional[List[str]] = None
    ) -> BacktestResult:
        """
        Run walk-forward backtest by generating recommendations for each date.

        This simulates real trading by generating recommendations at each
        test date using only data available up to that point.

        Args:
            ticker: Stock symbol
            trading_graph: TradingAgentsGraph instance
            test_dates: List of dates to test (default: weekly for past 3 months)

        Returns:
            BacktestResult with performance metrics
        """
        if test_dates is None:
            # Generate weekly test dates for past 3 months
            test_dates = self._generate_test_dates()

        recommendations = []
        for date in test_dates:
            try:
                print(f"Testing {ticker} on {date}...")
                _, decision = trading_graph.propagate(ticker, date)
                recommendations.append({
                    "date": date,
                    "decision": decision
                })
            except Exception as e:
                print(f"Error on {date}: {e}")
                continue

        return self.run_backtest(ticker, recommendations)

    def _generate_test_dates(self) -> List[str]:
        """Generate weekly test dates for the lookback period."""
        dates = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_months * 30)

        current = start_date
        while current < end_date:
            # Skip weekends
            if current.weekday() < 5:
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=7)

        return dates

    def _get_benchmark_return(self, start_date: str, end_date: str) -> float:
        """Get benchmark (SPY) return for comparison."""
        try:
            df = self.get_historical_prices(self.benchmark_ticker, start_date, end_date)
            if df.empty:
                return 0.0

            start_price = df.iloc[0]["Close"]
            end_price = df.iloc[-1]["Close"]
            return ((end_price - start_price) / start_price) * 100

        except Exception:
            return 0.0

    def _empty_result(self, ticker: str, start_date: str, end_date: str) -> BacktestResult:
        """Return empty result when no data available."""
        return BacktestResult(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_return=0.0,
            avg_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            trades=[],
            benchmark_return=0.0,
            alpha=0.0
        )

    def generate_report(self, result: BacktestResult) -> str:
        """
        Generate a human-readable backtest report.

        Args:
            result: BacktestResult from run_backtest

        Returns:
            Formatted report string
        """
        report = f"""
## Backtest Report: {result.ticker}
**Period:** {result.start_date} to {result.end_date}

### Performance Summary
| Metric | Value |
|--------|-------|
| Total Trades | {result.total_trades} |
| Winning Trades | {result.winning_trades} |
| Losing Trades | {result.losing_trades} |
| Win Rate | {result.win_rate:.1%} |
| Total Return | {result.total_return:.2f}% |
| Average Return | {result.avg_return:.2f}% |
| Max Drawdown | {result.max_drawdown:.2f}% |
| Sharpe Ratio | {result.sharpe_ratio:.2f} |

### Benchmark Comparison
| Metric | Strategy | Benchmark (SPY) |
|--------|----------|-----------------|
| Return | {result.total_return:.2f}% | {result.benchmark_return:.2f}% |
| Alpha | {result.alpha:.2f}% | - |

### Trade History
"""
        for trade in result.trades[-10:]:  # Show last 10 trades
            emoji = "✅" if trade.return_pct > 0 else "❌" if trade.return_pct < 0 else "➖"
            report += f"| {trade.date} | {trade.decision} | {trade.return_pct:+.2f}% | {emoji} |\n"

        return report
