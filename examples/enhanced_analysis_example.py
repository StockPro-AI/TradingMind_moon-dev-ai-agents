#!/usr/bin/env python3
"""
Example: Enhanced Analysis with TradingAgents

This example shows how to use the new analysis modules:
- Backtesting framework
- Risk calculator
- Market context analysis
- SEC filings integration
- Confidence scoring
- Enhanced output format

All using FREE data sources only!
"""

import sys
sys.path.insert(0, '..')

from tradingagents.backtesting import BacktestEngine, PerformanceMetrics
from tradingagents.risk import RiskCalculator, PositionSizer
from tradingagents.agents.analysts.market_context_analyst import MarketContextAnalyst
from tradingagents.dataflows.sec_edgar import SECEdgarClient
from tradingagents.analysis import IntegratedAnalyzer, ConfidenceScorer


def example_backtesting():
    """Example: Backtesting historical recommendations."""
    print("\n" + "="*60)
    print("BACKTESTING EXAMPLE")
    print("="*60)

    engine = BacktestEngine(lookback_months=3, holding_days=5)

    # Simulate some historical recommendations
    recommendations = [
        {"date": "2024-10-01", "decision": "BUY"},
        {"date": "2024-10-15", "decision": "HOLD"},
        {"date": "2024-11-01", "decision": "BUY"},
        {"date": "2024-11-15", "decision": "SELL"},
        {"date": "2024-12-01", "decision": "BUY"},
    ]

    result = engine.run_backtest("AAPL", recommendations)
    print(engine.generate_report(result))


def example_risk_analysis():
    """Example: Risk analysis for a stock."""
    print("\n" + "="*60)
    print("RISK ANALYSIS EXAMPLE")
    print("="*60)

    calculator = RiskCalculator(lookback_days=60)
    print(calculator.generate_risk_report("NVDA"))


def example_position_sizing():
    """Example: Position sizing calculations."""
    print("\n" + "="*60)
    print("POSITION SIZING EXAMPLE")
    print("="*60)

    sizer = PositionSizer(portfolio_value=100000)

    # Get current price
    import yfinance as yf
    stock = yf.Ticker("TSLA")
    price = stock.info.get("currentPrice", 250)

    positions = sizer.calculate_optimal_position(
        entry_price=price,
        stop_loss_pct=0.05,  # 5% stop loss
        confidence=0.7
    )

    print(sizer.generate_position_report("TSLA", price, positions))


def example_market_context():
    """Example: Market context analysis."""
    print("\n" + "="*60)
    print("MARKET CONTEXT EXAMPLE")
    print("="*60)

    analyst = MarketContextAnalyst()
    print(analyst.generate_report("MSFT"))


def example_sec_filings():
    """Example: SEC filings analysis."""
    print("\n" + "="*60)
    print("SEC FILINGS EXAMPLE")
    print("="*60)

    client = SECEdgarClient()
    print(client.generate_report("AAPL"))


def example_full_analysis():
    """Example: Full integrated analysis."""
    print("\n" + "="*60)
    print("FULL INTEGRATED ANALYSIS EXAMPLE")
    print("="*60)

    # This would normally come from the TradingAgentsGraph
    # Here we simulate a minimal state
    mock_state = {
        "market_report": "Technical analysis shows bullish momentum with price above key moving averages.",
        "sentiment_report": "Social sentiment is positive with increased retail interest.",
        "news_report": "Recent earnings beat expectations. Analysts raising price targets.",
        "fundamentals_report": "Strong revenue growth. Improving margins. Healthy balance sheet.",
        "investment_debate_state": {
            "bull_history": "Strong growth potential. Market leader. Expanding margins.",
            "bear_history": "Valuation concerns. Competition risks. Macro headwinds.",
            "judge_decision": "BUY with caution. Growth justifies premium valuation."
        },
        "risk_debate_state": {
            "risky_history": "High reward potential. Accept short-term volatility.",
            "safe_history": "Use smaller position size. Set strict stop loss.",
            "neutral_history": "Balanced approach recommended. Monitor closely."
        },
        "final_trade_decision": "BUY"
    }

    analyzer = IntegratedAnalyzer(portfolio_value=100000)
    enhanced = analyzer.analyze(
        ticker="GOOGL",
        state=mock_state,
        decision="BUY",
        include_sec=True
    )

    print(enhanced.generate_report())

    # Also show JSON output
    print("\n--- JSON Output ---")
    print(enhanced.to_json())


def main():
    """Run all examples."""
    print("TradingAgents Enhanced Analysis Examples")
    print("All using FREE data sources!")
    print("="*60)

    # Run each example
    try:
        example_risk_analysis()
    except Exception as e:
        print(f"Risk analysis error: {e}")

    try:
        example_position_sizing()
    except Exception as e:
        print(f"Position sizing error: {e}")

    try:
        example_market_context()
    except Exception as e:
        print(f"Market context error: {e}")

    try:
        example_sec_filings()
    except Exception as e:
        print(f"SEC filings error: {e}")

    try:
        example_backtesting()
    except Exception as e:
        print(f"Backtesting error: {e}")

    try:
        example_full_analysis()
    except Exception as e:
        print(f"Full analysis error: {e}")


if __name__ == "__main__":
    main()
