"""
SEC EDGAR integration for TradingAgents.
Uses the FREE SEC EDGAR API to fetch company filings.

The SEC EDGAR API is completely free and requires only a User-Agent header.
Documentation: https://www.sec.gov/developer
"""

import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re


class SECEdgarClient:
    """
    Client for SEC EDGAR API (completely free).

    Provides access to:
    - 10-K (Annual Reports)
    - 10-Q (Quarterly Reports)
    - 8-K (Material Events)
    - Company facts and financials
    """

    BASE_URL = "https://data.sec.gov"
    SUBMISSIONS_URL = f"{BASE_URL}/submissions"
    COMPANY_FACTS_URL = f"{BASE_URL}/api/xbrl/companyfacts"

    # SEC requires a User-Agent with contact info
    HEADERS = {
        "User-Agent": "TradingAgents/1.0 (contact@example.com)",
        "Accept": "application/json"
    }

    # Rate limit: 10 requests per second
    RATE_LIMIT_DELAY = 0.1

    def __init__(self):
        """Initialize SEC EDGAR client."""
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            CIK number as string (padded to 10 digits)
        """
        try:
            self._rate_limit()

            # Use SEC's ticker to CIK mapping
            url = f"{self.BASE_URL}/files/company_tickers.json"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Search for ticker
            ticker_upper = ticker.upper()
            for entry in data.values():
                if entry.get("ticker") == ticker_upper:
                    cik = str(entry.get("cik_str", ""))
                    return cik.zfill(10)  # Pad to 10 digits

            return None

        except Exception as e:
            print(f"Error getting CIK for {ticker}: {e}")
            return None

    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get company information from SEC.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with company info
        """
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return {"error": f"CIK not found for {ticker}"}

            self._rate_limit()

            url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            data = response.json()

            return {
                "ticker": ticker,
                "cik": cik,
                "name": data.get("name", ""),
                "sic": data.get("sic", ""),
                "sic_description": data.get("sicDescription", ""),
                "fiscal_year_end": data.get("fiscalYearEnd", ""),
                "state": data.get("stateOfIncorporation", ""),
                "exchange": data.get("exchanges", []),
            }

        except Exception as e:
            print(f"Error getting company info for {ticker}: {e}")
            return {"error": str(e)}

    def get_recent_filings(
        self,
        ticker: str,
        filing_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent SEC filings for a company.

        Args:
            ticker: Stock symbol
            filing_types: Types to filter (e.g., ["10-K", "10-Q", "8-K"])
            limit: Maximum filings to return

        Returns:
            List of filing metadata
        """
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return []

            self._rate_limit()

            url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            data = response.json()
            filings = data.get("filings", {}).get("recent", {})

            if not filings:
                return []

            # Extract filing details
            results = []
            form_types = filings.get("form", [])
            filing_dates = filings.get("filingDate", [])
            accession_numbers = filings.get("accessionNumber", [])
            primary_documents = filings.get("primaryDocument", [])
            descriptions = filings.get("primaryDocDescription", [])

            for i in range(min(len(form_types), 100)):  # Check last 100
                form_type = form_types[i]

                # Filter by type if specified
                if filing_types and form_type not in filing_types:
                    continue

                results.append({
                    "form_type": form_type,
                    "filing_date": filing_dates[i] if i < len(filing_dates) else "",
                    "accession_number": accession_numbers[i] if i < len(accession_numbers) else "",
                    "document": primary_documents[i] if i < len(primary_documents) else "",
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "url": self._build_filing_url(cik, accession_numbers[i], primary_documents[i])
                    if i < len(accession_numbers) and i < len(primary_documents) else ""
                })

                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            print(f"Error getting filings for {ticker}: {e}")
            return []

    def _build_filing_url(self, cik: str, accession: str, document: str) -> str:
        """Build URL to SEC filing document."""
        accession_clean = accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_clean}/{document}"

    def get_10k_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Get most recent 10-K (annual report) summary.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with 10-K summary
        """
        filings = self.get_recent_filings(ticker, filing_types=["10-K"], limit=1)

        if not filings:
            return {"error": "No 10-K found"}

        latest = filings[0]

        return {
            "form_type": "10-K",
            "filing_date": latest["filing_date"],
            "url": latest["url"],
            "description": "Annual Report",
            "key_sections": [
                "Business Overview",
                "Risk Factors",
                "Financial Statements",
                "MD&A (Management Discussion)"
            ]
        }

    def get_10q_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Get most recent 10-Q (quarterly report) summary.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with 10-Q summary
        """
        filings = self.get_recent_filings(ticker, filing_types=["10-Q"], limit=1)

        if not filings:
            return {"error": "No 10-Q found"}

        latest = filings[0]

        return {
            "form_type": "10-Q",
            "filing_date": latest["filing_date"],
            "url": latest["url"],
            "description": "Quarterly Report"
        }

    def get_8k_events(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent 8-K filings (material events).

        8-K items include:
        - 1.01: Entry into Material Agreement
        - 2.01: Completion of Acquisition
        - 2.02: Results of Operations (Earnings)
        - 5.02: Departure/Election of Directors
        - 7.01: Regulation FD Disclosure
        - 8.01: Other Events

        Args:
            ticker: Stock symbol
            days: Look back this many days

        Returns:
            List of 8-K events
        """
        filings = self.get_recent_filings(ticker, filing_types=["8-K"], limit=20)

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_8ks = []

        for filing in filings:
            try:
                filing_date = datetime.strptime(filing["filing_date"], "%Y-%m-%d")
                if filing_date >= cutoff_date:
                    recent_8ks.append({
                        "date": filing["filing_date"],
                        "description": filing.get("description", "Material Event"),
                        "url": filing["url"]
                    })
            except ValueError:
                continue

        return recent_8ks

    def get_company_facts(self, ticker: str) -> Dict[str, Any]:
        """
        Get XBRL company facts (financial data).

        This provides structured financial data from SEC filings.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with key financial metrics
        """
        try:
            cik = self._get_cik(ticker)
            if not cik:
                return {"error": f"CIK not found for {ticker}"}

            self._rate_limit()

            url = f"{self.COMPANY_FACTS_URL}/CIK{cik}.json"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extract key metrics from US-GAAP taxonomy
            facts = data.get("facts", {}).get("us-gaap", {})

            def get_latest_value(concept: str) -> Optional[float]:
                """Get most recent value for a concept."""
                concept_data = facts.get(concept, {})
                units = concept_data.get("units", {})

                # Try USD first, then shares
                for unit_type in ["USD", "shares"]:
                    if unit_type in units:
                        values = units[unit_type]
                        if values:
                            # Get most recent annual value
                            annual = [v for v in values if v.get("form") == "10-K"]
                            if annual:
                                return annual[-1].get("val")
                return None

            return {
                "ticker": ticker,
                "revenue": get_latest_value("Revenues") or get_latest_value("RevenueFromContractWithCustomerExcludingAssessedTax"),
                "net_income": get_latest_value("NetIncomeLoss"),
                "total_assets": get_latest_value("Assets"),
                "total_liabilities": get_latest_value("Liabilities"),
                "stockholders_equity": get_latest_value("StockholdersEquity"),
                "operating_income": get_latest_value("OperatingIncomeLoss"),
                "eps": get_latest_value("EarningsPerShareBasic"),
                "shares_outstanding": get_latest_value("CommonStockSharesOutstanding"),
            }

        except Exception as e:
            print(f"Error getting company facts for {ticker}: {e}")
            return {"error": str(e)}

    def analyze_filings(self, ticker: str) -> Dict[str, Any]:
        """
        Comprehensive SEC filing analysis.

        Args:
            ticker: Stock symbol

        Returns:
            Complete filing analysis
        """
        company_info = self.get_company_info(ticker)
        recent_10k = self.get_10k_summary(ticker)
        recent_10q = self.get_10q_summary(ticker)
        recent_8ks = self.get_8k_events(ticker)
        company_facts = self.get_company_facts(ticker)

        # Count material events
        material_events = len(recent_8ks)

        return {
            "company": company_info,
            "latest_10k": recent_10k,
            "latest_10q": recent_10q,
            "recent_8k_count": material_events,
            "recent_8k_events": recent_8ks,
            "financials": company_facts,
            "filing_activity": "HIGH" if material_events > 3 else "MODERATE" if material_events > 0 else "LOW"
        }

    def generate_report(self, ticker: str) -> str:
        """
        Generate SEC filings report.

        Args:
            ticker: Stock symbol

        Returns:
            Formatted report
        """
        analysis = self.analyze_filings(ticker)

        company = analysis["company"]
        facts = analysis["financials"]

        report = f"""
## SEC Filings Analysis: {ticker}

### Company Information
| Field | Value |
|-------|-------|
| Name | {company.get('name', 'N/A')} |
| CIK | {company.get('cik', 'N/A')} |
| Industry | {company.get('sic_description', 'N/A')} |
| State | {company.get('state', 'N/A')} |
| Fiscal Year End | {company.get('fiscal_year_end', 'N/A')} |

### Latest SEC Filings
| Filing | Date | Link |
|--------|------|------|
| 10-K (Annual) | {analysis['latest_10k'].get('filing_date', 'N/A')} | [View]({analysis['latest_10k'].get('url', '#')}) |
| 10-Q (Quarterly) | {analysis['latest_10q'].get('filing_date', 'N/A')} | [View]({analysis['latest_10q'].get('url', '#')}) |

### Recent Material Events (8-K)
**Activity Level:** {analysis['filing_activity']} ({analysis['recent_8k_count']} filings in last 30 days)

"""
        for event in analysis["recent_8k_events"][:5]:
            report += f"- **{event['date']}**: {event['description']} ([link]({event['url']}))\n"

        report += f"""
### Key Financial Metrics (from SEC XBRL)
| Metric | Value |
|--------|-------|
| Revenue | ${facts.get('revenue', 0):,.0f} |
| Net Income | ${facts.get('net_income', 0):,.0f} |
| Total Assets | ${facts.get('total_assets', 0):,.0f} |
| Total Liabilities | ${facts.get('total_liabilities', 0):,.0f} |
| Stockholders Equity | ${facts.get('stockholders_equity', 0):,.0f} |
| EPS | ${facts.get('eps', 0):.2f} |

### Analysis Notes
- Review the 10-K Risk Factors section for potential concerns
- Check 8-K filings for management changes or material agreements
- Compare financial metrics to previous quarters in 10-Q
"""

        return report
