"""
Market Context Analyst for TradingAgents.
Provides market regime detection, sector analysis, and peer comparison.
Uses free yfinance data only.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class MarketContextAnalyst:
    """
    Analyzes broader market context for trading decisions.
    Uses free yfinance data for all analysis.
    """

    # Sector ETFs for sector analysis (all available via yfinance for free)
    SECTOR_ETFS = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financials": "XLF",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Materials": "XLB",
        "Industrials": "XLI",
        "Communication Services": "XLC"
    }

    # Market indicators
    MARKET_INDICATORS = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq 100",
        "IWM": "Russell 2000",
        "DIA": "Dow Jones",
        "VIX": "Volatility Index"
    }

    def __init__(self, lookback_days: int = 60):
        """
        Initialize market context analyst.

        Args:
            lookback_days: Days of data for analysis
        """
        self.lookback_days = lookback_days

    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get basic stock information from yfinance.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with stock info including sector
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", None),
                "forward_pe": info.get("forwardPE", None),
                "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "52w_high": info.get("fiftyTwoWeekHigh", 0),
                "52w_low": info.get("fiftyTwoWeekLow", 0),
            }
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {"ticker": ticker, "sector": "Unknown"}

    def detect_market_regime(self) -> Dict[str, Any]:
        """
        Detect current market regime using SPY and VIX.

        Returns:
            Dict with regime classification and metrics
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)

            # Get SPY data
            spy = yf.Ticker("SPY")
            spy_data = spy.history(start=start_date.strftime("%Y-%m-%d"),
                                   end=end_date.strftime("%Y-%m-%d"))

            if spy_data.empty:
                return {"regime": "UNKNOWN", "confidence": 0}

            # Calculate metrics
            spy_close = spy_data["Close"]

            # Moving averages
            sma_20 = spy_close.rolling(20).mean().iloc[-1]
            sma_50 = spy_close.rolling(50).mean().iloc[-1] if len(spy_close) >= 50 else sma_20
            current_price = spy_close.iloc[-1]

            # Trend strength
            returns_20d = (current_price / spy_close.iloc[-20] - 1) * 100 if len(spy_close) >= 20 else 0

            # Get VIX
            try:
                vix = yf.Ticker("^VIX")
                vix_data = vix.history(period="5d")
                vix_level = vix_data["Close"].iloc[-1] if not vix_data.empty else 20
            except:
                vix_level = 20  # Default

            # Determine regime
            if current_price > sma_20 > sma_50 and returns_20d > 2:
                regime = "BULL"
                confidence = min(0.9, 0.5 + returns_20d / 20)
            elif current_price < sma_20 < sma_50 and returns_20d < -2:
                regime = "BEAR"
                confidence = min(0.9, 0.5 + abs(returns_20d) / 20)
            elif vix_level > 25:
                regime = "HIGH_VOLATILITY"
                confidence = min(0.9, vix_level / 40)
            else:
                regime = "SIDEWAYS"
                confidence = 0.5

            return {
                "regime": regime,
                "confidence": round(confidence, 2),
                "spy_price": round(current_price, 2),
                "spy_vs_sma20": round((current_price / sma_20 - 1) * 100, 2),
                "spy_vs_sma50": round((current_price / sma_50 - 1) * 100, 2),
                "spy_20d_return": round(returns_20d, 2),
                "vix_level": round(vix_level, 2),
                "interpretation": self._interpret_regime(regime, vix_level)
            }

        except Exception as e:
            print(f"Error detecting market regime: {e}")
            return {"regime": "UNKNOWN", "confidence": 0}

    def _interpret_regime(self, regime: str, vix: float) -> str:
        """Generate regime interpretation."""
        interpretations = {
            "BULL": "Market is in uptrend. Favor long positions and momentum strategies.",
            "BEAR": "Market is in downtrend. Consider defensive positions or shorts.",
            "SIDEWAYS": "Market is range-bound. Consider mean-reversion strategies.",
            "HIGH_VOLATILITY": f"VIX at {vix:.0f}. High uncertainty - reduce position sizes."
        }
        return interpretations.get(regime, "Unable to determine market conditions.")

    def get_sector_performance(self) -> Dict[str, Dict[str, float]]:
        """
        Get sector performance rankings using sector ETFs.

        Returns:
            Dict with sector performance metrics
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)

            results = {}
            for sector, etf in self.SECTOR_ETFS.items():
                try:
                    ticker = yf.Ticker(etf)
                    data = ticker.history(start=start_date.strftime("%Y-%m-%d"),
                                        end=end_date.strftime("%Y-%m-%d"))

                    if data.empty:
                        continue

                    close = data["Close"]
                    current = close.iloc[-1]

                    # Calculate returns
                    return_5d = (current / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0
                    return_20d = (current / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0
                    return_60d = (current / close.iloc[0] - 1) * 100

                    # Relative strength vs SPY
                    spy = yf.Ticker("SPY")
                    spy_data = spy.history(start=start_date.strftime("%Y-%m-%d"),
                                          end=end_date.strftime("%Y-%m-%d"))
                    spy_return = (spy_data["Close"].iloc[-1] / spy_data["Close"].iloc[0] - 1) * 100

                    results[sector] = {
                        "etf": etf,
                        "return_5d": round(return_5d, 2),
                        "return_20d": round(return_20d, 2),
                        "return_60d": round(return_60d, 2),
                        "relative_strength": round(return_60d - spy_return, 2)
                    }

                except Exception as e:
                    print(f"Error fetching {sector} ({etf}): {e}")
                    continue

            return results

        except Exception as e:
            print(f"Error getting sector performance: {e}")
            return {}

    def get_sector_for_stock(self, ticker: str) -> Dict[str, Any]:
        """
        Get sector context for a specific stock.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with sector analysis for the stock
        """
        info = self.get_stock_info(ticker)
        sector = info.get("sector", "Unknown")

        if sector == "Unknown":
            return {"sector": sector, "sector_performance": None}

        sector_perf = self.get_sector_performance()
        sector_data = sector_perf.get(sector, {})

        return {
            "stock": ticker,
            "sector": sector,
            "industry": info.get("industry", "Unknown"),
            "sector_etf": sector_data.get("etf", "N/A"),
            "sector_5d_return": sector_data.get("return_5d", 0),
            "sector_20d_return": sector_data.get("return_20d", 0),
            "sector_relative_strength": sector_data.get("relative_strength", 0)
        }

    def find_peers(self, ticker: str, max_peers: int = 5) -> List[str]:
        """
        Find peer companies in the same sector/industry.

        Note: This uses a predefined mapping since yfinance doesn't provide peers directly.

        Args:
            ticker: Stock symbol
            max_peers: Maximum peers to return

        Returns:
            List of peer tickers
        """
        # Predefined peer groups for major sectors
        tech_peers = {
            "AAPL": ["MSFT", "GOOGL", "META", "AMZN"],
            "MSFT": ["AAPL", "GOOGL", "ORCL", "CRM"],
            "GOOGL": ["META", "MSFT", "AMZN", "NFLX"],
            "NVDA": ["AMD", "INTC", "QCOM", "AVGO"],
            "AMD": ["NVDA", "INTC", "QCOM", "MU"],
            "TSLA": ["F", "GM", "RIVN", "NIO"],
        }

        finance_peers = {
            "JPM": ["BAC", "WFC", "C", "GS"],
            "BAC": ["JPM", "WFC", "C", "USB"],
            "GS": ["MS", "JPM", "BAC", "C"],
        }

        healthcare_peers = {
            "JNJ": ["PFE", "MRK", "ABBV", "LLY"],
            "PFE": ["JNJ", "MRK", "ABBV", "BMY"],
            "UNH": ["CVS", "CI", "HUM", "ANTM"],
        }

        all_peers = {**tech_peers, **finance_peers, **healthcare_peers}

        peers = all_peers.get(ticker.upper(), [])
        return peers[:max_peers]

    def compare_to_peers(self, ticker: str) -> Dict[str, Any]:
        """
        Compare stock to its peers.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with peer comparison
        """
        peers = self.find_peers(ticker)
        if not peers:
            return {"peers": [], "comparison": "No peers found"}

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            results = []

            # Get target stock data
            target = yf.Ticker(ticker)
            target_data = target.history(start=start_date.strftime("%Y-%m-%d"),
                                        end=end_date.strftime("%Y-%m-%d"))
            target_return = (target_data["Close"].iloc[-1] / target_data["Close"].iloc[0] - 1) * 100

            for peer in peers:
                try:
                    peer_ticker = yf.Ticker(peer)
                    peer_data = peer_ticker.history(start=start_date.strftime("%Y-%m-%d"),
                                                   end=end_date.strftime("%Y-%m-%d"))

                    if peer_data.empty:
                        continue

                    peer_return = (peer_data["Close"].iloc[-1] / peer_data["Close"].iloc[0] - 1) * 100

                    results.append({
                        "ticker": peer,
                        "return_30d": round(peer_return, 2),
                        "vs_target": round(peer_return - target_return, 2)
                    })

                except Exception:
                    continue

            # Rank
            results.sort(key=lambda x: x["return_30d"], reverse=True)

            # Find target's rank
            all_returns = [target_return] + [r["return_30d"] for r in results]
            all_returns.sort(reverse=True)
            target_rank = all_returns.index(target_return) + 1

            return {
                "target": ticker,
                "target_return_30d": round(target_return, 2),
                "rank_among_peers": f"{target_rank}/{len(all_returns)}",
                "peers": results,
                "outperforming": sum(1 for r in results if r["vs_target"] < 0),
                "underperforming": sum(1 for r in results if r["vs_target"] > 0)
            }

        except Exception as e:
            print(f"Error comparing peers: {e}")
            return {"peers": [], "comparison": f"Error: {e}"}

    def get_market_breadth(self) -> Dict[str, Any]:
        """
        Calculate market breadth indicators.

        Returns:
            Dict with breadth metrics
        """
        try:
            # Use sector ETFs as proxy for breadth
            sector_perf = self.get_sector_performance()

            if not sector_perf:
                return {"breadth": "UNKNOWN"}

            positive_sectors = sum(1 for s in sector_perf.values() if s.get("return_20d", 0) > 0)
            total_sectors = len(sector_perf)

            # Calculate average sector return
            avg_return = np.mean([s.get("return_20d", 0) for s in sector_perf.values()])

            # Breadth rating
            breadth_ratio = positive_sectors / total_sectors if total_sectors > 0 else 0.5

            if breadth_ratio > 0.7:
                breadth = "STRONG"
            elif breadth_ratio > 0.5:
                breadth = "NEUTRAL"
            elif breadth_ratio > 0.3:
                breadth = "WEAK"
            else:
                breadth = "VERY_WEAK"

            return {
                "breadth": breadth,
                "sectors_positive": positive_sectors,
                "sectors_total": total_sectors,
                "breadth_ratio": round(breadth_ratio, 2),
                "avg_sector_return": round(avg_return, 2),
                "strongest_sector": max(sector_perf.items(), key=lambda x: x[1].get("return_20d", 0))[0],
                "weakest_sector": min(sector_perf.items(), key=lambda x: x[1].get("return_20d", 0))[0]
            }

        except Exception as e:
            print(f"Error calculating breadth: {e}")
            return {"breadth": "UNKNOWN"}

    def analyze(self, ticker: str) -> Dict[str, Any]:
        """
        Run complete market context analysis.

        Args:
            ticker: Stock symbol

        Returns:
            Comprehensive market context analysis
        """
        return {
            "stock_info": self.get_stock_info(ticker),
            "market_regime": self.detect_market_regime(),
            "sector_context": self.get_sector_for_stock(ticker),
            "peer_comparison": self.compare_to_peers(ticker),
            "market_breadth": self.get_market_breadth()
        }

    def generate_report(self, ticker: str) -> str:
        """
        Generate market context report.

        Args:
            ticker: Stock symbol

        Returns:
            Formatted report
        """
        analysis = self.analyze(ticker)

        regime = analysis["market_regime"]
        sector = analysis["sector_context"]
        peers = analysis["peer_comparison"]
        breadth = analysis["market_breadth"]

        report = f"""
## Market Context Analysis: {ticker}

### Market Regime
**Current Regime:** {regime.get('regime', 'UNKNOWN')} (Confidence: {regime.get('confidence', 0):.0%})

| Indicator | Value |
|-----------|-------|
| SPY Price | ${regime.get('spy_price', 0):.2f} |
| SPY vs 20 SMA | {regime.get('spy_vs_sma20', 0):+.1f}% |
| SPY vs 50 SMA | {regime.get('spy_vs_sma50', 0):+.1f}% |
| SPY 20d Return | {regime.get('spy_20d_return', 0):+.1f}% |
| VIX Level | {regime.get('vix_level', 0):.1f} |

**Interpretation:** {regime.get('interpretation', 'N/A')}

### Sector Analysis
**Sector:** {sector.get('sector', 'Unknown')} | **Industry:** {sector.get('industry', 'Unknown')}

| Metric | Value |
|--------|-------|
| Sector ETF | {sector.get('sector_etf', 'N/A')} |
| Sector 5d Return | {sector.get('sector_5d_return', 0):+.1f}% |
| Sector 20d Return | {sector.get('sector_20d_return', 0):+.1f}% |
| Relative Strength | {sector.get('sector_relative_strength', 0):+.1f}% vs SPY |

### Peer Comparison
**{ticker} 30d Return:** {peers.get('target_return_30d', 0):+.1f}%
**Rank:** {peers.get('rank_among_peers', 'N/A')}

| Peer | 30d Return | vs {ticker} |
|------|------------|-------------|
"""
        for peer in peers.get('peers', [])[:5]:
            report += f"| {peer['ticker']} | {peer['return_30d']:+.1f}% | {peer['vs_target']:+.1f}% |\n"

        report += f"""
### Market Breadth
**Breadth:** {breadth.get('breadth', 'UNKNOWN')}

| Metric | Value |
|--------|-------|
| Sectors Positive | {breadth.get('sectors_positive', 0)}/{breadth.get('sectors_total', 0)} |
| Avg Sector Return | {breadth.get('avg_sector_return', 0):+.1f}% |
| Strongest Sector | {breadth.get('strongest_sector', 'N/A')} |
| Weakest Sector | {breadth.get('weakest_sector', 'N/A')} |
"""

        return report
