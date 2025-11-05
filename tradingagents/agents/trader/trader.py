import functools
import time
import json


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        # Handle missing investment_plan when Research Manager is skipped (e.g., for DeepSeek)
        investment_plan = state.get("investment_plan", None)
        # Handle missing reports safely (some analysts may be skipped)
        market_research_report = state.get("market_report", "Market analysis not available.")
        sentiment_report = state.get("sentiment_report", "Sentiment analysis not available.")
        news_report = state.get("news_report", "News analysis not available.")
        fundamentals_report = state.get("fundamentals_report", "Fundamentals analysis not available.")

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        # Build context based on whether investment_plan exists
        if investment_plan:
            context = {
                "role": "user",
                "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
            }
        else:
            # When no investment plan (Research Manager skipped), use direct analyst reports
            context = {
                "role": "user",
                "content": f"Based on analysis by our team of analysts for {company_name}, here are the key insights:\n\n{curr_situation}\n\nBased on these insights, make an informed trading decision.",
            }

        messages = [
            {
                "role": "system",
                "content": f"""You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Do not forget to utilize lessons from past decisions to learn from your mistakes. Here is some reflections from similar situatiosn you traded in and the lessons learned: {past_memory_str}""",
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
