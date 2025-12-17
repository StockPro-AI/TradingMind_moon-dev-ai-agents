"""
Integrated analyzer that combines all analysis modules.
Produces comprehensive trading recommendations.
"""

import yfinance as yf
from typing import Dict, Any, Optional
from datetime import datetime

from .confidence_scorer import ConfidenceScorer
from .enhanced_output import EnhancedDecision, EnhancedOutputBuilder, PriceTarget, RiskParameters
from .risk_calculator import RiskCalculator
from .position_sizer import PositionSizer
from ..agents.analysts.market_context_analyst import MarketContextAnalyst
from ..dataflows.sec_edgar import SECEdgarClient


class IntegratedAnalyzer:
    """
    Combines all analysis modules to produce comprehensive recommendations.

    Uses only FREE data sources:
    - yfinance for price data
    - SEC EDGAR for filings
    - Internal calculations for risk metrics
    """

    def __init__(self, portfolio_value: float = 100000):
        """
        Initialize integrated analyzer.

        Args:
            portfolio_value: Portfolio value for position sizing
        """
        self.confidence_scorer = ConfidenceScorer()
        self.risk_calculator = RiskCalculator()
        self.position_sizer = PositionSizer(portfolio_value=portfolio_value)
        self.market_context = MarketContextAnalyst()
        self.sec_client = SECEdgarClient()

    def get_current_price(self, ticker: str) -> float:
        """Get current stock price."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get("currentPrice", info.get("regularMarketPrice", 0))
        except Exception:
            return 0

    def analyze(
        self,
        ticker: str,
        state: Dict[str, Any],
        decision: str,
        include_sec: bool = True
    ) -> EnhancedDecision:
        """
        Run comprehensive analysis and produce enhanced decision.

        Args:
            ticker: Stock symbol
            state: Final state from trading graph
            decision: BUY, SELL, or HOLD from trading graph
            include_sec: Whether to include SEC filings (slower)

        Returns:
            EnhancedDecision with complete analysis
        """
        builder = EnhancedOutputBuilder()

        # Get current price
        current_price = self.get_current_price(ticker)
        if current_price == 0:
            current_price = 100  # Fallback

        # Calculate confidence
        market_regime = self.market_context.detect_market_regime()
        regime = market_regime.get("regime", "UNKNOWN")

        confidence = self.confidence_scorer.calculate_confidence(
            state, decision, regime
        )

        # Set core decision
        builder.set_core_decision(
            ticker=ticker,
            date=datetime.now().strftime("%Y-%m-%d"),
            decision=decision,
            confidence=confidence.overall,
            current_price=current_price
        )

        # Calculate risk metrics
        risk_metrics = self.risk_calculator.calculate_risk_metrics(ticker)
        volatility = risk_metrics.get("volatility_annual", 25) / 100

        # Calculate position size
        positions = self.position_sizer.calculate_optimal_position(
            entry_price=current_price,
            stop_loss_pct=min(0.08, volatility * 2),  # 2x daily vol or 8% max
            volatility=volatility / 16,  # Convert annual to daily
            confidence=confidence.overall
        )

        recommended = positions.get("recommended")
        if recommended:
            builder.set_risk_params(
                stop_loss=recommended.stop_loss_price,
                take_profit=recommended.take_profit_price,
                position_size_pct=recommended.position_pct,
                max_loss_dollars=recommended.risk_amount,
                risk_reward_ratio=recommended.risk_reward_ratio
            )

            # Calculate price targets based on volatility
            target_move = current_price * volatility * 0.5  # 50% of annual vol
            builder.set_price_targets(
                low=current_price - target_move * 0.5,
                mid=current_price + target_move if decision == "BUY" else current_price - target_move,
                high=current_price + target_move * 1.5,
                time_horizon="1-3 months"
            )

        # Get sector context
        sector_context = self.market_context.get_sector_for_stock(ticker)
        sector_strength = "STRONG" if sector_context.get("sector_relative_strength", 0) > 2 else \
                         "WEAK" if sector_context.get("sector_relative_strength", 0) < -2 else "NEUTRAL"

        builder.set_market_context(regime=regime, sector_strength=sector_strength)

        # Extract catalysts and risks from state
        catalysts, risks = self._extract_catalysts_and_risks(state, ticker, include_sec)
        builder.add_catalysts(catalysts)
        builder.add_risks(risks)

        # Set data quality
        builder.set_data_quality(
            completeness=confidence.data_quality,
            analyst_agreement=confidence.analyst_agreement,
            risk_agreement=confidence.risk_agreement
        )

        # Generate reasoning summary
        reasoning = self._generate_reasoning_summary(
            decision, confidence, risk_metrics, market_regime, sector_context
        )
        builder.set_reasoning(reasoning)

        return builder.build()

    def _extract_catalysts_and_risks(
        self,
        state: Dict[str, Any],
        ticker: str,
        include_sec: bool
    ) -> tuple:
        """Extract key catalysts and risks from analysis."""
        catalysts = []
        risks = []

        # Extract from bull/bear debate
        debate_state = state.get("investment_debate_state", {})

        bull_history = debate_state.get("bull_history", "").lower()
        bear_history = debate_state.get("bear_history", "").lower()

        # Simple keyword extraction for catalysts
        catalyst_keywords = ["growth", "revenue", "earnings", "expansion", "launch", "acquisition", "partnership"]
        for kw in catalyst_keywords:
            if kw in bull_history:
                catalysts.append(f"Potential {kw} opportunity identified")
                break

        # Extract risks
        risk_keywords = ["risk", "concern", "challenge", "competition", "decline", "debt", "lawsuit"]
        for kw in risk_keywords:
            if kw in bear_history:
                risks.append(f"Analyst identified {kw} factor")
                break

        # Add SEC-based catalysts/risks if enabled
        if include_sec:
            try:
                sec_analysis = self.sec_client.analyze_filings(ticker)

                # Recent 8-K filings indicate activity
                if sec_analysis.get("recent_8k_count", 0) > 2:
                    catalysts.append("High SEC filing activity - potential corporate events")

                # Check for material events
                for event in sec_analysis.get("recent_8k_events", [])[:2]:
                    if "acquisition" in event.get("description", "").lower():
                        catalysts.append("Recent acquisition activity (8-K filing)")
                    if "agreement" in event.get("description", "").lower():
                        catalysts.append("New material agreement announced")

            except Exception:
                pass

        # Add default items if empty
        if not catalysts:
            catalysts = ["Technical momentum", "Sector rotation potential", "Valuation opportunity"]
        if not risks:
            risks = ["Market volatility", "Sector-specific headwinds", "Execution risk"]

        return catalysts[:5], risks[:5]

    def _generate_reasoning_summary(
        self,
        decision: str,
        confidence,
        risk_metrics: Dict,
        market_regime: Dict,
        sector_context: Dict
    ) -> str:
        """Generate a reasoning summary."""
        regime = market_regime.get("regime", "UNKNOWN")
        sector = sector_context.get("sector", "Unknown")
        vol = risk_metrics.get("volatility_annual", 0)
        beta = risk_metrics.get("beta", 1)

        summary = f"**{decision}** recommendation with **{confidence.overall:.0%}** confidence. "

        if decision == "BUY":
            summary += f"Analysis suggests upside potential in the current {regime} market environment. "
        elif decision == "SELL":
            summary += f"Risk factors outweigh potential gains in current {regime} conditions. "
        else:
            summary += f"Mixed signals suggest waiting for clearer direction. "

        summary += f"The stock operates in the {sector} sector with {vol:.0f}% annualized volatility "
        summary += f"and beta of {beta:.2f}. "

        if confidence.overall >= 0.7:
            summary += "High confidence supports full position sizing."
        elif confidence.overall >= 0.5:
            summary += "Moderate confidence suggests reduced position size."
        else:
            summary += "Low confidence warrants caution or paper trading."

        return summary

    def generate_full_report(
        self,
        ticker: str,
        state: Dict[str, Any],
        decision: str
    ) -> str:
        """
        Generate comprehensive analysis report.

        Args:
            ticker: Stock symbol
            state: Final state from trading graph
            decision: Trading decision

        Returns:
            Complete markdown report
        """
        # Get enhanced decision
        enhanced = self.analyze(ticker, state, decision)

        # Generate base report
        report = enhanced.generate_report()

        # Add risk analysis
        risk_report = self.risk_calculator.generate_risk_report(ticker)
        report += "\n---\n" + risk_report

        # Add market context
        context_report = self.market_context.generate_report(ticker)
        report += "\n---\n" + context_report

        return report
