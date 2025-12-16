"""
Enhanced output formatter for TradingAgents.
Combines all analysis into a comprehensive decision format.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


@dataclass
class PriceTarget:
    """Price target with ranges."""
    low: float
    mid: float
    high: float
    time_horizon: str  # e.g., "1-3 months"


@dataclass
class RiskParameters:
    """Risk management parameters."""
    stop_loss: float
    take_profit: float
    position_size_pct: float
    max_loss_dollars: float
    risk_reward_ratio: float


@dataclass
class EnhancedDecision:
    """
    Enhanced trading decision with all supporting analysis.

    This is the comprehensive output format that includes:
    - Core decision (BUY/SELL/HOLD)
    - Confidence scoring
    - Price targets
    - Risk parameters
    - Key catalysts and risks
    - Supporting data quality metrics
    """
    # Core decision
    ticker: str
    date: str
    decision: str  # BUY, SELL, HOLD
    confidence: float  # 0-1

    # Price targets
    current_price: float
    price_target: Optional[PriceTarget] = None

    # Risk parameters
    risk_params: Optional[RiskParameters] = None

    # Market context
    market_regime: str = "UNKNOWN"
    sector_strength: str = "NEUTRAL"

    # Key factors
    key_catalysts: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)

    # Data quality
    data_completeness: float = 1.0
    analyst_agreement: float = 0.5
    risk_agreement: float = 0.5

    # Time horizon
    time_horizon: str = "5-20 trading days"

    # Raw reasoning
    reasoning_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "date": self.date,
            "decision": self.decision,
            "confidence": self.confidence,
            "current_price": self.current_price,
            "price_target": {
                "low": self.price_target.low,
                "mid": self.price_target.mid,
                "high": self.price_target.high,
                "time_horizon": self.price_target.time_horizon
            } if self.price_target else None,
            "risk_params": {
                "stop_loss": self.risk_params.stop_loss,
                "take_profit": self.risk_params.take_profit,
                "position_size_pct": self.risk_params.position_size_pct,
                "max_loss_dollars": self.risk_params.max_loss_dollars,
                "risk_reward_ratio": self.risk_params.risk_reward_ratio
            } if self.risk_params else None,
            "market_regime": self.market_regime,
            "sector_strength": self.sector_strength,
            "key_catalysts": self.key_catalysts,
            "key_risks": self.key_risks,
            "data_completeness": self.data_completeness,
            "analyst_agreement": self.analyst_agreement,
            "risk_agreement": self.risk_agreement,
            "time_horizon": self.time_horizon,
            "reasoning_summary": self.reasoning_summary
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def generate_report(self) -> str:
        """Generate comprehensive markdown report."""
        # Confidence emoji
        if self.confidence >= 0.7:
            conf_emoji = "🟢"
        elif self.confidence >= 0.5:
            conf_emoji = "🟡"
        else:
            conf_emoji = "🔴"

        # Decision emoji
        decision_emoji = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(self.decision, "❓")

        report = f"""
# Trading Decision: {self.ticker}
**Date:** {self.date}

## {decision_emoji} Decision: {self.decision}
### {conf_emoji} Confidence: {self.confidence:.0%}

---

## Price Analysis
| Metric | Value |
|--------|-------|
| Current Price | ${self.current_price:.2f} |
"""
        if self.price_target:
            report += f"""| Target (Low) | ${self.price_target.low:.2f} ({((self.price_target.low/self.current_price)-1)*100:+.1f}%) |
| Target (Mid) | ${self.price_target.mid:.2f} ({((self.price_target.mid/self.current_price)-1)*100:+.1f}%) |
| Target (High) | ${self.price_target.high:.2f} ({((self.price_target.high/self.current_price)-1)*100:+.1f}%) |
| Time Horizon | {self.price_target.time_horizon} |
"""

        report += """
## Risk Management
"""
        if self.risk_params:
            report += f"""| Parameter | Value |
|-----------|-------|
| Stop Loss | ${self.risk_params.stop_loss:.2f} ({((self.risk_params.stop_loss/self.current_price)-1)*100:+.1f}%) |
| Take Profit | ${self.risk_params.take_profit:.2f} ({((self.risk_params.take_profit/self.current_price)-1)*100:+.1f}%) |
| Position Size | {self.risk_params.position_size_pct:.1%} of portfolio |
| Max Loss | ${self.risk_params.max_loss_dollars:,.2f} |
| Risk/Reward | {self.risk_params.risk_reward_ratio:.1f}:1 |
"""

        report += f"""
## Market Context
| Factor | Status |
|--------|--------|
| Market Regime | {self.market_regime} |
| Sector Strength | {self.sector_strength} |
| Time Horizon | {self.time_horizon} |

## Key Catalysts 🚀
"""
        for catalyst in self.key_catalysts[:5]:
            report += f"- {catalyst}\n"

        report += """
## Key Risks ⚠️
"""
        for risk in self.key_risks[:5]:
            report += f"- {risk}\n"

        report += f"""
## Data Quality
| Metric | Score |
|--------|-------|
| Data Completeness | {self.data_completeness:.0%} |
| Analyst Agreement | {self.analyst_agreement:.0%} |
| Risk Team Agreement | {self.risk_agreement:.0%} |

## Summary
{self.reasoning_summary}

---
*Generated by TradingAgents on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        return report


class EnhancedOutputBuilder:
    """Builder for creating EnhancedDecision objects."""

    def __init__(self):
        """Initialize builder."""
        self._data = {}

    def set_core_decision(
        self,
        ticker: str,
        date: str,
        decision: str,
        confidence: float,
        current_price: float
    ) -> "EnhancedOutputBuilder":
        """Set core decision data."""
        self._data["ticker"] = ticker
        self._data["date"] = date
        self._data["decision"] = decision
        self._data["confidence"] = confidence
        self._data["current_price"] = current_price
        return self

    def set_price_targets(
        self,
        low: float,
        mid: float,
        high: float,
        time_horizon: str = "1-3 months"
    ) -> "EnhancedOutputBuilder":
        """Set price targets."""
        self._data["price_target"] = PriceTarget(
            low=low, mid=mid, high=high, time_horizon=time_horizon
        )
        return self

    def set_risk_params(
        self,
        stop_loss: float,
        take_profit: float,
        position_size_pct: float,
        max_loss_dollars: float,
        risk_reward_ratio: float
    ) -> "EnhancedOutputBuilder":
        """Set risk parameters."""
        self._data["risk_params"] = RiskParameters(
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_pct=position_size_pct,
            max_loss_dollars=max_loss_dollars,
            risk_reward_ratio=risk_reward_ratio
        )
        return self

    def set_market_context(
        self,
        regime: str,
        sector_strength: str
    ) -> "EnhancedOutputBuilder":
        """Set market context."""
        self._data["market_regime"] = regime
        self._data["sector_strength"] = sector_strength
        return self

    def add_catalysts(self, catalysts: List[str]) -> "EnhancedOutputBuilder":
        """Add key catalysts."""
        self._data["key_catalysts"] = catalysts
        return self

    def add_risks(self, risks: List[str]) -> "EnhancedOutputBuilder":
        """Add key risks."""
        self._data["key_risks"] = risks
        return self

    def set_data_quality(
        self,
        completeness: float,
        analyst_agreement: float,
        risk_agreement: float
    ) -> "EnhancedOutputBuilder":
        """Set data quality metrics."""
        self._data["data_completeness"] = completeness
        self._data["analyst_agreement"] = analyst_agreement
        self._data["risk_agreement"] = risk_agreement
        return self

    def set_reasoning(self, summary: str) -> "EnhancedOutputBuilder":
        """Set reasoning summary."""
        self._data["reasoning_summary"] = summary
        return self

    def build(self) -> EnhancedDecision:
        """Build the EnhancedDecision object."""
        return EnhancedDecision(**self._data)
