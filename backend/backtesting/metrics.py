"""
Performance metrics for backtesting.
Pure calculations - no external API calls needed.
"""

import numpy as np
from typing import List, Optional


class PerformanceMetrics:
    """
    Calculate various performance metrics for trading strategies.
    All calculations are done locally - no API calls required.
    """

    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default 5%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 52  # Weekly trading
    ) -> float:
        """
        Calculate annualized Sharpe ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns

        Args:
            returns: List of period returns (in percentage)
            periods_per_year: Number of trading periods per year

        Returns:
            Annualized Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        returns_decimal = [r / 100 for r in returns]
        mean_return = np.mean(returns_decimal)
        std_return = np.std(returns_decimal, ddof=1)

        if std_return == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * periods_per_year
        annual_std = std_return * np.sqrt(periods_per_year)

        sharpe = (annual_return - self.risk_free_rate) / annual_std
        return round(sharpe, 2)

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 52
    ) -> float:
        """
        Calculate Sortino ratio (uses downside deviation only).

        Sortino = (Mean Return - Risk Free Rate) / Downside Deviation

        Args:
            returns: List of period returns (in percentage)
            periods_per_year: Number of trading periods per year

        Returns:
            Annualized Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        returns_decimal = [r / 100 for r in returns]
        mean_return = np.mean(returns_decimal)

        # Calculate downside deviation (only negative returns)
        negative_returns = [r for r in returns_decimal if r < 0]
        if not negative_returns:
            return float('inf') if mean_return > 0 else 0.0

        downside_std = np.std(negative_returns, ddof=1)
        if downside_std == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * periods_per_year
        annual_downside = downside_std * np.sqrt(periods_per_year)

        sortino = (annual_return - self.risk_free_rate) / annual_downside
        return round(sortino, 2)

    def calculate_max_drawdown(self, returns: List[float]) -> float:
        """
        Calculate maximum drawdown from peak.

        Args:
            returns: List of period returns (in percentage)

        Returns:
            Maximum drawdown as percentage
        """
        if not returns:
            return 0.0

        # Convert to cumulative returns
        cumulative = [100]  # Start with $100
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r / 100))

        # Calculate drawdown at each point
        peak = cumulative[0]
        max_dd = 0

        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_dd = max(max_dd, drawdown)

        return round(max_dd, 2)

    def calculate_calmar_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 52
    ) -> float:
        """
        Calculate Calmar ratio (return / max drawdown).

        Args:
            returns: List of period returns (in percentage)
            periods_per_year: Number of trading periods per year

        Returns:
            Calmar ratio
        """
        if not returns:
            return 0.0

        total_return = sum(returns)
        # Annualize return
        annual_return = (total_return / len(returns)) * periods_per_year

        max_dd = self.calculate_max_drawdown(returns)
        if max_dd == 0:
            return float('inf') if annual_return > 0 else 0.0

        return round(annual_return / max_dd, 2)

    def calculate_win_rate(self, returns: List[float]) -> float:
        """
        Calculate percentage of winning trades.

        Args:
            returns: List of trade returns

        Returns:
            Win rate as percentage
        """
        if not returns:
            return 0.0

        winners = sum(1 for r in returns if r > 0)
        return round((winners / len(returns)) * 100, 1)

    def calculate_profit_factor(self, returns: List[float]) -> float:
        """
        Calculate profit factor (gross profit / gross loss).

        Args:
            returns: List of trade returns

        Returns:
            Profit factor
        """
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return round(gross_profit / gross_loss, 2)

    def calculate_expectancy(self, returns: List[float]) -> float:
        """
        Calculate expectancy (average profit per trade).

        Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

        Args:
            returns: List of trade returns

        Returns:
            Expectancy per trade
        """
        if not returns:
            return 0.0

        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r < 0]

        win_rate = len(winners) / len(returns)
        loss_rate = len(losers) / len(returns)

        avg_win = np.mean(winners) if winners else 0
        avg_loss = abs(np.mean(losers)) if losers else 0

        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        return round(expectancy, 2)

    def calculate_all_metrics(self, returns: List[float]) -> dict:
        """
        Calculate all available metrics.

        Args:
            returns: List of trade returns

        Returns:
            Dictionary of all metrics
        """
        return {
            "total_return": round(sum(returns), 2) if returns else 0,
            "avg_return": round(np.mean(returns), 2) if returns else 0,
            "std_dev": round(np.std(returns), 2) if len(returns) > 1 else 0,
            "sharpe_ratio": self.calculate_sharpe_ratio(returns),
            "sortino_ratio": self.calculate_sortino_ratio(returns),
            "max_drawdown": self.calculate_max_drawdown(returns),
            "calmar_ratio": self.calculate_calmar_ratio(returns),
            "win_rate": self.calculate_win_rate(returns),
            "profit_factor": self.calculate_profit_factor(returns),
            "expectancy": self.calculate_expectancy(returns),
            "total_trades": len(returns),
            "winning_trades": sum(1 for r in returns if r > 0),
            "losing_trades": sum(1 for r in returns if r < 0),
        }
