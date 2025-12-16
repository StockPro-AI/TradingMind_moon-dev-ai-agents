"""
Confidence scoring for trading decisions.
Analyzes multiple factors to generate a confidence level.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ConfidenceBreakdown:
    """Breakdown of confidence score components."""
    analyst_agreement: float  # 0-1
    risk_agreement: float     # 0-1
    market_alignment: float   # 0-1
    data_quality: float       # 0-1
    reasoning_strength: float # 0-1
    overall: float            # 0-1
    interpretation: str


class ConfidenceScorer:
    """
    Calculate confidence scores for trading decisions.

    Factors considered:
    1. Analyst agreement (do all analysts agree?)
    2. Risk team agreement (consensus on risk?)
    3. Market alignment (is decision aligned with market regime?)
    4. Data quality (were all data sources available?)
    5. Reasoning strength (quality of arguments)
    """

    def __init__(self):
        """Initialize confidence scorer."""
        pass

    def calculate_confidence(
        self,
        state: Dict[str, Any],
        decision: str,
        market_regime: Optional[str] = None
    ) -> ConfidenceBreakdown:
        """
        Calculate confidence score for a trading decision.

        Args:
            state: Final state from trading graph
            decision: BUY, SELL, or HOLD
            market_regime: Current market regime (BULL, BEAR, etc.)

        Returns:
            ConfidenceBreakdown with scores
        """
        # 1. Analyst agreement
        analyst_agreement = self._calculate_analyst_agreement(state, decision)

        # 2. Risk team agreement
        risk_agreement = self._calculate_risk_agreement(state, decision)

        # 3. Market alignment
        market_alignment = self._calculate_market_alignment(decision, market_regime)

        # 4. Data quality
        data_quality = self._calculate_data_quality(state)

        # 5. Reasoning strength
        reasoning_strength = self._calculate_reasoning_strength(state)

        # Weighted overall score
        weights = {
            "analyst_agreement": 0.25,
            "risk_agreement": 0.20,
            "market_alignment": 0.15,
            "data_quality": 0.15,
            "reasoning_strength": 0.25
        }

        overall = (
            analyst_agreement * weights["analyst_agreement"] +
            risk_agreement * weights["risk_agreement"] +
            market_alignment * weights["market_alignment"] +
            data_quality * weights["data_quality"] +
            reasoning_strength * weights["reasoning_strength"]
        )

        interpretation = self._interpret_confidence(overall)

        return ConfidenceBreakdown(
            analyst_agreement=round(analyst_agreement, 2),
            risk_agreement=round(risk_agreement, 2),
            market_alignment=round(market_alignment, 2),
            data_quality=round(data_quality, 2),
            reasoning_strength=round(reasoning_strength, 2),
            overall=round(overall, 2),
            interpretation=interpretation
        )

    def _calculate_analyst_agreement(self, state: Dict[str, Any], decision: str) -> float:
        """Calculate agreement among analysts."""
        reports = [
            state.get("market_report", ""),
            state.get("sentiment_report", ""),
            state.get("news_report", ""),
            state.get("fundamentals_report", "")
        ]

        # Count how many reports support the decision
        support_keywords = {
            "BUY": ["bullish", "positive", "upside", "growth", "strong", "opportunity", "buy"],
            "SELL": ["bearish", "negative", "downside", "decline", "weak", "risk", "sell"],
            "HOLD": ["neutral", "mixed", "uncertain", "wait", "sideways", "hold"]
        }

        keywords = support_keywords.get(decision.upper(), [])
        supporting = 0
        total = 0

        for report in reports:
            if report:
                total += 1
                report_lower = report.lower()
                if any(kw in report_lower for kw in keywords):
                    supporting += 1

        if total == 0:
            return 0.5

        return supporting / total

    def _calculate_risk_agreement(self, state: Dict[str, Any], decision: str) -> float:
        """Calculate agreement among risk analysts."""
        risk_state = state.get("risk_debate_state", {})

        histories = [
            risk_state.get("risky_history", ""),
            risk_state.get("safe_history", ""),
            risk_state.get("neutral_history", "")
        ]

        # Count support for decision
        support_keywords = {
            "BUY": ["approve", "proceed", "acceptable", "manageable", "reward"],
            "SELL": ["exit", "reduce", "protect", "hedge"],
            "HOLD": ["wait", "monitor", "cautious", "review"]
        }

        keywords = support_keywords.get(decision.upper(), [])
        supporting = 0
        total = 0

        for history in histories:
            if history:
                total += 1
                history_lower = history.lower()
                if any(kw in history_lower for kw in keywords):
                    supporting += 1

        if total == 0:
            return 0.5

        return supporting / total

    def _calculate_market_alignment(self, decision: str, market_regime: Optional[str]) -> float:
        """Check if decision aligns with market regime."""
        if not market_regime:
            return 0.5

        alignment_matrix = {
            ("BUY", "BULL"): 1.0,
            ("BUY", "SIDEWAYS"): 0.6,
            ("BUY", "BEAR"): 0.3,
            ("BUY", "HIGH_VOLATILITY"): 0.4,
            ("SELL", "BEAR"): 1.0,
            ("SELL", "SIDEWAYS"): 0.6,
            ("SELL", "BULL"): 0.3,
            ("SELL", "HIGH_VOLATILITY"): 0.7,
            ("HOLD", "SIDEWAYS"): 0.8,
            ("HOLD", "HIGH_VOLATILITY"): 0.8,
            ("HOLD", "BULL"): 0.5,
            ("HOLD", "BEAR"): 0.5,
        }

        return alignment_matrix.get((decision.upper(), market_regime), 0.5)

    def _calculate_data_quality(self, state: Dict[str, Any]) -> float:
        """Calculate data quality/completeness."""
        required_fields = [
            "market_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
            "investment_debate_state",
            "risk_debate_state"
        ]

        available = sum(1 for f in required_fields if state.get(f))
        return available / len(required_fields)

    def _calculate_reasoning_strength(self, state: Dict[str, Any]) -> float:
        """Analyze strength of reasoning in reports."""
        # Check for quantitative mentions
        final_decision = state.get("final_trade_decision", "")
        investment_plan = state.get("investment_plan", "")

        combined = f"{final_decision} {investment_plan}".lower()

        # Positive indicators
        positive_indicators = [
            r"\d+%",  # Percentage mentions
            r"\$\d+",  # Dollar amounts
            r"pe ratio|p/e",  # Valuation metrics
            r"support|resistance",  # Technical levels
            r"catalyst|trigger",  # Event-driven reasoning
            r"revenue|earnings|growth",  # Fundamental mentions
        ]

        score = 0.5  # Base score

        for pattern in positive_indicators:
            if re.search(pattern, combined):
                score += 0.08

        # Cap at 1.0
        return min(score, 1.0)

    def _interpret_confidence(self, score: float) -> str:
        """Generate interpretation of confidence score."""
        if score >= 0.8:
            return "HIGH CONFIDENCE - Strong consensus across all factors"
        elif score >= 0.6:
            return "MODERATE-HIGH CONFIDENCE - Good alignment with some minor concerns"
        elif score >= 0.4:
            return "MODERATE CONFIDENCE - Mixed signals, consider position sizing"
        elif score >= 0.2:
            return "LOW CONFIDENCE - Significant disagreement, reduce exposure"
        else:
            return "VERY LOW CONFIDENCE - Consider avoiding this trade"

    def generate_confidence_report(self, breakdown: ConfidenceBreakdown) -> str:
        """Generate human-readable confidence report."""
        return f"""
## Confidence Analysis

### Overall Score: {breakdown.overall:.0%}
**Interpretation:** {breakdown.interpretation}

### Score Breakdown
| Factor | Score | Weight |
|--------|-------|--------|
| Analyst Agreement | {breakdown.analyst_agreement:.0%} | 25% |
| Risk Team Agreement | {breakdown.risk_agreement:.0%} | 20% |
| Market Alignment | {breakdown.market_alignment:.0%} | 15% |
| Data Quality | {breakdown.data_quality:.0%} | 15% |
| Reasoning Strength | {breakdown.reasoning_strength:.0%} | 25% |

### Recommendation
"""
        if breakdown.overall >= 0.7:
            return "- Proceed with full position size"
        elif breakdown.overall >= 0.5:
            return "- Consider reduced position size (50-75%)"
        else:
            return "- Consider paper trading or skipping this opportunity"
