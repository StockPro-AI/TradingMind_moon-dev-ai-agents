"""
Position sizing calculator for TradingAgents.
Implements various position sizing strategies.
No external APIs needed - pure calculations.
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PositionSize:
    """Position sizing recommendation."""
    shares: int
    dollar_amount: float
    position_pct: float  # Percentage of portfolio
    risk_amount: float  # Dollar amount at risk
    stop_loss_price: float
    take_profit_price: float
    risk_reward_ratio: float


class PositionSizer:
    """
    Calculate optimal position sizes based on various strategies.

    Supports:
    - Fixed fractional (risk % per trade)
    - Kelly criterion
    - Volatility-based sizing
    - ATR-based stop losses
    """

    def __init__(
        self,
        portfolio_value: float = 100000,
        max_position_pct: float = 0.10,  # Max 10% per position
        default_risk_pct: float = 0.02   # Risk 2% per trade
    ):
        """
        Initialize position sizer.

        Args:
            portfolio_value: Total portfolio value
            max_position_pct: Maximum position size as % of portfolio
            default_risk_pct: Default risk per trade as % of portfolio
        """
        self.portfolio_value = portfolio_value
        self.max_position_pct = max_position_pct
        self.default_risk_pct = default_risk_pct

    def fixed_fractional(
        self,
        entry_price: float,
        stop_loss_pct: float,
        risk_pct: Optional[float] = None
    ) -> PositionSize:
        """
        Calculate position size using fixed fractional method.

        Risk a fixed percentage of portfolio per trade.

        Args:
            entry_price: Entry price per share
            stop_loss_pct: Stop loss as percentage below entry (e.g., 0.05 = 5%)
            risk_pct: Risk per trade (default: self.default_risk_pct)

        Returns:
            PositionSize with recommendation
        """
        risk_pct = risk_pct or self.default_risk_pct

        # Dollar amount we're willing to risk
        risk_amount = self.portfolio_value * risk_pct

        # Stop loss price
        stop_loss_price = entry_price * (1 - stop_loss_pct)

        # Risk per share
        risk_per_share = entry_price - stop_loss_price

        if risk_per_share <= 0:
            return self._zero_position(entry_price)

        # Calculate shares
        shares = int(risk_amount / risk_per_share)

        # Check against max position size
        max_shares = int((self.portfolio_value * self.max_position_pct) / entry_price)
        shares = min(shares, max_shares)

        if shares <= 0:
            return self._zero_position(entry_price)

        # Calculate actual values
        dollar_amount = shares * entry_price
        position_pct = dollar_amount / self.portfolio_value
        actual_risk = shares * risk_per_share

        # Take profit at 2:1 risk/reward
        take_profit_price = entry_price + (2 * risk_per_share)

        return PositionSize(
            shares=shares,
            dollar_amount=round(dollar_amount, 2),
            position_pct=round(position_pct, 4),
            risk_amount=round(actual_risk, 2),
            stop_loss_price=round(stop_loss_price, 2),
            take_profit_price=round(take_profit_price, 2),
            risk_reward_ratio=2.0
        )

    def kelly_criterion(
        self,
        entry_price: float,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        kelly_fraction: float = 0.5  # Half Kelly for safety
    ) -> PositionSize:
        """
        Calculate position size using Kelly criterion.

        Kelly % = W - [(1-W) / R]
        Where W = win rate, R = win/loss ratio

        Args:
            entry_price: Entry price per share
            win_rate: Historical win rate (0-1)
            avg_win_pct: Average winning trade percentage
            avg_loss_pct: Average losing trade percentage (positive number)
            kelly_fraction: Fraction of Kelly to use (0.5 = half Kelly)

        Returns:
            PositionSize with recommendation
        """
        if avg_loss_pct == 0 or win_rate <= 0 or win_rate >= 1:
            return self._zero_position(entry_price)

        # Win/loss ratio
        win_loss_ratio = avg_win_pct / avg_loss_pct

        # Kelly formula
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)

        # Apply fraction and cap
        kelly_pct = max(0, kelly_pct * kelly_fraction)
        kelly_pct = min(kelly_pct, self.max_position_pct)

        # Calculate position
        dollar_amount = self.portfolio_value * kelly_pct
        shares = int(dollar_amount / entry_price)

        if shares <= 0:
            return self._zero_position(entry_price)

        # Use average loss as stop loss
        stop_loss_price = entry_price * (1 - avg_loss_pct / 100)
        take_profit_price = entry_price * (1 + avg_win_pct / 100)
        risk_amount = shares * entry_price * (avg_loss_pct / 100)

        return PositionSize(
            shares=shares,
            dollar_amount=round(shares * entry_price, 2),
            position_pct=round(kelly_pct, 4),
            risk_amount=round(risk_amount, 2),
            stop_loss_price=round(stop_loss_price, 2),
            take_profit_price=round(take_profit_price, 2),
            risk_reward_ratio=round(avg_win_pct / avg_loss_pct, 2)
        )

    def volatility_based(
        self,
        entry_price: float,
        volatility: float,  # Daily volatility as decimal
        vol_multiplier: float = 2.0,  # Stop at 2x daily vol
        target_vol_pct: float = 0.15  # Target 15% portfolio volatility
    ) -> PositionSize:
        """
        Calculate position size based on volatility targeting.

        Adjusts position size to maintain consistent portfolio volatility.

        Args:
            entry_price: Entry price per share
            volatility: Daily volatility as decimal (e.g., 0.02 = 2%)
            vol_multiplier: Multiplier for stop loss (in volatility units)
            target_vol_pct: Target portfolio volatility contribution

        Returns:
            PositionSize with recommendation
        """
        if volatility <= 0:
            return self._zero_position(entry_price)

        # Position size to achieve target volatility
        # Target vol contribution = position_pct * stock_vol
        position_pct = target_vol_pct / (volatility * np.sqrt(252))
        position_pct = min(position_pct, self.max_position_pct)

        dollar_amount = self.portfolio_value * position_pct
        shares = int(dollar_amount / entry_price)

        if shares <= 0:
            return self._zero_position(entry_price)

        # Stop loss based on volatility
        stop_loss_distance = entry_price * volatility * vol_multiplier
        stop_loss_price = entry_price - stop_loss_distance

        # Take profit at same distance
        take_profit_price = entry_price + stop_loss_distance

        risk_amount = shares * stop_loss_distance

        return PositionSize(
            shares=shares,
            dollar_amount=round(shares * entry_price, 2),
            position_pct=round(position_pct, 4),
            risk_amount=round(risk_amount, 2),
            stop_loss_price=round(stop_loss_price, 2),
            take_profit_price=round(take_profit_price, 2),
            risk_reward_ratio=1.0
        )

    def atr_based(
        self,
        entry_price: float,
        atr: float,  # Average True Range
        atr_multiplier: float = 2.0,
        risk_pct: Optional[float] = None
    ) -> PositionSize:
        """
        Calculate position size using ATR for stop loss.

        Args:
            entry_price: Entry price per share
            atr: Average True Range value
            atr_multiplier: Multiplier for stop distance
            risk_pct: Risk per trade (default: self.default_risk_pct)

        Returns:
            PositionSize with recommendation
        """
        risk_pct = risk_pct or self.default_risk_pct

        if atr <= 0:
            return self._zero_position(entry_price)

        # Stop loss based on ATR
        stop_distance = atr * atr_multiplier
        stop_loss_price = entry_price - stop_distance

        # Risk amount
        risk_amount = self.portfolio_value * risk_pct

        # Shares based on risk
        shares = int(risk_amount / stop_distance)

        # Cap at max position
        max_shares = int((self.portfolio_value * self.max_position_pct) / entry_price)
        shares = min(shares, max_shares)

        if shares <= 0:
            return self._zero_position(entry_price)

        # Take profit at 2x ATR (2:1 ratio)
        take_profit_price = entry_price + (2 * stop_distance)

        return PositionSize(
            shares=shares,
            dollar_amount=round(shares * entry_price, 2),
            position_pct=round((shares * entry_price) / self.portfolio_value, 4),
            risk_amount=round(shares * stop_distance, 2),
            stop_loss_price=round(stop_loss_price, 2),
            take_profit_price=round(take_profit_price, 2),
            risk_reward_ratio=2.0
        )

    def calculate_optimal_position(
        self,
        entry_price: float,
        stop_loss_pct: float = 0.05,
        volatility: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win_pct: Optional[float] = None,
        avg_loss_pct: Optional[float] = None,
        confidence: float = 0.5  # 0-1 confidence in the trade
    ) -> Dict[str, PositionSize]:
        """
        Calculate position sizes using multiple methods.

        Args:
            entry_price: Entry price per share
            stop_loss_pct: Stop loss percentage
            volatility: Daily volatility (optional)
            win_rate: Historical win rate (optional)
            avg_win_pct: Average win percentage (optional)
            avg_loss_pct: Average loss percentage (optional)
            confidence: Trade confidence 0-1

        Returns:
            Dict with position sizes from different methods
        """
        # Adjust risk based on confidence
        adjusted_risk = self.default_risk_pct * confidence

        results = {
            "fixed_fractional": self.fixed_fractional(
                entry_price, stop_loss_pct, adjusted_risk
            )
        }

        if volatility:
            results["volatility_based"] = self.volatility_based(
                entry_price, volatility
            )

        if win_rate and avg_win_pct and avg_loss_pct:
            results["kelly"] = self.kelly_criterion(
                entry_price, win_rate, avg_win_pct, avg_loss_pct
            )

        # Calculate recommended (average of methods)
        all_shares = [r.shares for r in results.values() if r.shares > 0]
        if all_shares:
            avg_shares = int(np.mean(all_shares))
            dollar_amount = avg_shares * entry_price
            stop_loss_price = entry_price * (1 - stop_loss_pct)
            take_profit_price = entry_price * (1 + 2 * stop_loss_pct)

            results["recommended"] = PositionSize(
                shares=avg_shares,
                dollar_amount=round(dollar_amount, 2),
                position_pct=round(dollar_amount / self.portfolio_value, 4),
                risk_amount=round(avg_shares * entry_price * stop_loss_pct, 2),
                stop_loss_price=round(stop_loss_price, 2),
                take_profit_price=round(take_profit_price, 2),
                risk_reward_ratio=2.0
            )

        return results

    def _zero_position(self, entry_price: float) -> PositionSize:
        """Return zero position when calculation fails."""
        return PositionSize(
            shares=0,
            dollar_amount=0,
            position_pct=0,
            risk_amount=0,
            stop_loss_price=entry_price * 0.95,
            take_profit_price=entry_price * 1.10,
            risk_reward_ratio=2.0
        )

    def generate_position_report(
        self,
        ticker: str,
        entry_price: float,
        positions: Dict[str, PositionSize]
    ) -> str:
        """
        Generate human-readable position sizing report.

        Args:
            ticker: Stock symbol
            entry_price: Entry price
            positions: Dict of position sizes from different methods

        Returns:
            Formatted report
        """
        report = f"""
## Position Sizing: {ticker}
**Entry Price:** ${entry_price:.2f}
**Portfolio Value:** ${self.portfolio_value:,.2f}

### Recommended Position
"""
        if "recommended" in positions:
            rec = positions["recommended"]
            report += f"""
| Metric | Value |
|--------|-------|
| Shares | {rec.shares} |
| Dollar Amount | ${rec.dollar_amount:,.2f} |
| Portfolio % | {rec.position_pct:.1%} |
| Risk Amount | ${rec.risk_amount:,.2f} |
| Stop Loss | ${rec.stop_loss_price:.2f} |
| Take Profit | ${rec.take_profit_price:.2f} |
| Risk/Reward | {rec.risk_reward_ratio:.1f}:1 |
"""

        report += "\n### Method Comparison\n"
        report += "| Method | Shares | Amount | Risk |\n"
        report += "|--------|--------|--------|------|\n"

        for method, pos in positions.items():
            if method != "recommended":
                report += f"| {method} | {pos.shares} | ${pos.dollar_amount:,.0f} | ${pos.risk_amount:,.0f} |\n"

        return report
