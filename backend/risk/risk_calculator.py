"""
Risk calculator for TradingAgents.
Provides VaR, volatility, and other risk metrics.
All calculations are local - no paid APIs needed.
"""

import numpy as np
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class RiskCalculator:
    """
    Calculate risk metrics for stocks and portfolios.
    Uses free yfinance data for volatility calculations.
    """

    def __init__(self, lookback_days: int = 60):
        """
        Initialize risk calculator.

        Args:
            lookback_days: Days of historical data for calculations
        """
        self.lookback_days = lookback_days

    def get_historical_returns(self, ticker: str) -> pd.Series:
        """
        Get historical daily returns using free yfinance API.

        Args:
            ticker: Stock symbol

        Returns:
            Series of daily returns
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 30)  # Buffer

            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date.strftime("%Y-%m-%d"),
                             end=end_date.strftime("%Y-%m-%d"))

            if df.empty:
                return pd.Series()

            returns = df["Close"].pct_change().dropna()
            return returns

        except Exception as e:
            print(f"Error fetching returns for {ticker}: {e}")
            return pd.Series()

    def calculate_volatility(
        self,
        ticker: str,
        annualize: bool = True
    ) -> float:
        """
        Calculate historical volatility.

        Args:
            ticker: Stock symbol
            annualize: Whether to annualize the volatility

        Returns:
            Volatility as decimal (0.25 = 25%)
        """
        returns = self.get_historical_returns(ticker)
        if returns.empty:
            return 0.0

        vol = returns.std()
        if annualize:
            vol = vol * np.sqrt(252)  # Trading days per year

        return round(vol, 4)

    def calculate_var(
        self,
        ticker: str,
        confidence: float = 0.95,
        position_value: float = 10000
    ) -> Dict[str, float]:
        """
        Calculate Value at Risk (VaR) using historical simulation.

        Args:
            ticker: Stock symbol
            confidence: Confidence level (0.95 = 95%)
            position_value: Dollar value of position

        Returns:
            Dict with VaR metrics
        """
        returns = self.get_historical_returns(ticker)
        if returns.empty:
            return {"var_pct": 0, "var_dollar": 0, "cvar_pct": 0, "cvar_dollar": 0}

        # Historical VaR - percentile of returns
        var_pct = np.percentile(returns, (1 - confidence) * 100)

        # Conditional VaR (Expected Shortfall) - average of worst returns
        worst_returns = returns[returns <= var_pct]
        cvar_pct = worst_returns.mean() if len(worst_returns) > 0 else var_pct

        return {
            "var_pct": round(abs(var_pct) * 100, 2),  # As percentage
            "var_dollar": round(abs(var_pct) * position_value, 2),
            "cvar_pct": round(abs(cvar_pct) * 100, 2),
            "cvar_dollar": round(abs(cvar_pct) * position_value, 2),
            "confidence": confidence
        }

    def calculate_beta(self, ticker: str, benchmark: str = "SPY") -> float:
        """
        Calculate beta relative to benchmark.

        Beta = Covariance(stock, market) / Variance(market)

        Args:
            ticker: Stock symbol
            benchmark: Market benchmark (default SPY)

        Returns:
            Beta coefficient
        """
        stock_returns = self.get_historical_returns(ticker)
        market_returns = self.get_historical_returns(benchmark)

        if stock_returns.empty or market_returns.empty:
            return 1.0

        # Align dates
        aligned = pd.concat([stock_returns, market_returns], axis=1, join="inner")
        if len(aligned) < 20:
            return 1.0

        aligned.columns = ["stock", "market"]

        covariance = aligned["stock"].cov(aligned["market"])
        market_variance = aligned["market"].var()

        if market_variance == 0:
            return 1.0

        beta = covariance / market_variance
        return round(beta, 2)

    def calculate_correlation(self, ticker1: str, ticker2: str) -> float:
        """
        Calculate correlation between two stocks.

        Args:
            ticker1: First stock symbol
            ticker2: Second stock symbol

        Returns:
            Correlation coefficient (-1 to 1)
        """
        returns1 = self.get_historical_returns(ticker1)
        returns2 = self.get_historical_returns(ticker2)

        if returns1.empty or returns2.empty:
            return 0.0

        # Align dates
        aligned = pd.concat([returns1, returns2], axis=1, join="inner")
        if len(aligned) < 20:
            return 0.0

        correlation = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        return round(correlation, 2)

    def calculate_sharpe_ratio(
        self,
        ticker: str,
        risk_free_rate: float = 0.05
    ) -> float:
        """
        Calculate Sharpe ratio from historical returns.

        Args:
            ticker: Stock symbol
            risk_free_rate: Annual risk-free rate

        Returns:
            Annualized Sharpe ratio
        """
        returns = self.get_historical_returns(ticker)
        if returns.empty or len(returns) < 20:
            return 0.0

        # Annualize
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)

        if annual_vol == 0:
            return 0.0

        sharpe = (annual_return - risk_free_rate) / annual_vol
        return round(sharpe, 2)

    def calculate_max_drawdown(self, ticker: str) -> Dict[str, float]:
        """
        Calculate maximum drawdown from historical prices.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with drawdown metrics
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 30)

            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date.strftime("%Y-%m-%d"),
                             end=end_date.strftime("%Y-%m-%d"))

            if df.empty:
                return {"max_drawdown_pct": 0, "current_drawdown_pct": 0}

            prices = df["Close"]

            # Calculate running maximum
            running_max = prices.expanding().max()
            drawdown = (prices - running_max) / running_max

            max_dd = drawdown.min()
            current_dd = drawdown.iloc[-1]

            return {
                "max_drawdown_pct": round(abs(max_dd) * 100, 2),
                "current_drawdown_pct": round(abs(current_dd) * 100, 2)
            }

        except Exception as e:
            print(f"Error calculating drawdown for {ticker}: {e}")
            return {"max_drawdown_pct": 0, "current_drawdown_pct": 0}

    def calculate_risk_metrics(self, ticker: str) -> Dict[str, any]:
        """
        Calculate comprehensive risk metrics for a stock.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with all risk metrics
        """
        volatility = self.calculate_volatility(ticker)
        var = self.calculate_var(ticker)
        beta = self.calculate_beta(ticker)
        sharpe = self.calculate_sharpe_ratio(ticker)
        drawdown = self.calculate_max_drawdown(ticker)

        # Risk rating based on metrics
        risk_score = self._calculate_risk_score(volatility, beta, var["var_pct"])
        risk_rating = self._get_risk_rating(risk_score)

        return {
            "ticker": ticker,
            "volatility_annual": round(volatility * 100, 2),  # As percentage
            "beta": beta,
            "var_95_daily": var["var_pct"],
            "cvar_95_daily": var["cvar_pct"],
            "sharpe_ratio": sharpe,
            "max_drawdown": drawdown["max_drawdown_pct"],
            "current_drawdown": drawdown["current_drawdown_pct"],
            "risk_score": risk_score,
            "risk_rating": risk_rating
        }

    def _calculate_risk_score(
        self,
        volatility: float,
        beta: float,
        var_pct: float
    ) -> int:
        """
        Calculate overall risk score (1-10).

        Args:
            volatility: Annualized volatility
            beta: Beta coefficient
            var_pct: Value at Risk percentage

        Returns:
            Risk score from 1 (lowest) to 10 (highest)
        """
        score = 0

        # Volatility component (0-4 points)
        if volatility > 0.5:
            score += 4
        elif volatility > 0.35:
            score += 3
        elif volatility > 0.25:
            score += 2
        elif volatility > 0.15:
            score += 1

        # Beta component (0-3 points)
        if abs(beta) > 1.5:
            score += 3
        elif abs(beta) > 1.2:
            score += 2
        elif abs(beta) > 1.0:
            score += 1

        # VaR component (0-3 points)
        if var_pct > 5:
            score += 3
        elif var_pct > 3:
            score += 2
        elif var_pct > 2:
            score += 1

        return min(max(score, 1), 10)

    def _get_risk_rating(self, score: int) -> str:
        """Convert risk score to rating."""
        if score <= 3:
            return "LOW"
        elif score <= 6:
            return "MODERATE"
        elif score <= 8:
            return "HIGH"
        else:
            return "VERY HIGH"

    def generate_risk_report(self, ticker: str) -> str:
        """
        Generate a human-readable risk report.

        Args:
            ticker: Stock symbol

        Returns:
            Formatted risk report
        """
        metrics = self.calculate_risk_metrics(ticker)

        report = f"""
## Risk Analysis: {ticker}

### Risk Rating: {metrics['risk_rating']} (Score: {metrics['risk_score']}/10)

### Volatility & Market Sensitivity
| Metric | Value |
|--------|-------|
| Annualized Volatility | {metrics['volatility_annual']:.1f}% |
| Beta (vs SPY) | {metrics['beta']:.2f} |
| Sharpe Ratio | {metrics['sharpe_ratio']:.2f} |

### Value at Risk (95% confidence, 1-day)
| Metric | Value |
|--------|-------|
| VaR | {metrics['var_95_daily']:.2f}% |
| CVaR (Expected Shortfall) | {metrics['cvar_95_daily']:.2f}% |

### Drawdown Analysis
| Metric | Value |
|--------|-------|
| Max Drawdown ({self.lookback_days}d) | {metrics['max_drawdown']:.1f}% |
| Current Drawdown | {metrics['current_drawdown']:.1f}% |

### Interpretation
"""
        # Add interpretation based on metrics
        if metrics['beta'] > 1.2:
            report += "- **High Beta**: Stock is more volatile than the market. Expect amplified moves.\n"
        elif metrics['beta'] < 0.8:
            report += "- **Low Beta**: Stock is less volatile than the market. More defensive.\n"

        if metrics['volatility_annual'] > 40:
            report += "- **High Volatility**: Significant price swings expected. Use wider stop-losses.\n"

        if metrics['sharpe_ratio'] > 1:
            report += "- **Good Risk-Adjusted Returns**: Historical returns compensate for risk taken.\n"
        elif metrics['sharpe_ratio'] < 0:
            report += "- **Poor Risk-Adjusted Returns**: Returns don't justify the risk. Be cautious.\n"

        return report
