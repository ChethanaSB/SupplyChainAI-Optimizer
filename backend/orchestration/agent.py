"""
agent.py — Cognitive Supply Chain Agent (Agentic Orchestration).
Uses Google Gemini to analyze signals and orchestrate optimizations.
"""
import logging
import json
from typing import List, Dict
from backend.config import GEMINI_API_KEY
import google.generativeai as genai

logger = logging.getLogger("chainmind.agent")

class SupplyChainAgent:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    async def orchestrate(self, signals: List[Dict]) -> Dict:
        """
        Analyze incoming disruption signals and decide on an orchestration plan.
        """
        if not self.model:
            return {"action": "LOG_ONLY", "reason": "AI Agent offline (no key)"}

        prompt = f"""
        System: You are the ZF ChainMind Orchestration Agent. 
        Context: You monitor ZF's global supply chain for disruptions.
        
        Recent Signals:
        {json.dumps(signals, indent=2)}
        
        Task:
        1. Evaluate urgency (LOW, MEDIUM, HIGH, CRITICAL).
        2. Decide if we should: 
           - REOPTIMIZE_ROUTING
           - ADJUST_SAFETY_STOCK
           - ALERT_SUPPLIERS
           - DO_NOTHING
        3. Explain your reasoning in 1 sentence.
        
        Return JSON format: {{"urgency": "...", "action": "...", "reason": "..."}}
        """

        try:
            response = self.model.generate_content(prompt)
            plan = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
            logger.info("Agent Orchestration Plan: %s", plan)
            return plan
        except Exception as exc:
            logger.error("Agent failed to orchestrate: %s", exc)
            return {"urgency": "HIGH", "action": "REOPTIMIZE_ROUTING", "reason": "Signal detected, system fallback triggered."}

# Global instance
agent = SupplyChainAgent()
