"""
early_warning.py — Early Warning System (EWS) for Disaster Prediction.
Predicts disruption risks for the next 3 months using signal intelligence.
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict

class EarlyWarningSystem:
    def __init__(self):
        # Disaster patterns: (Prob, Severity)
        self.disaster_types = [
            "Tropical Cyclone Surge",
            "Geopolitical Port Closure",
            "Labor Strike",
            "Energy Price Shock",
            "Semiconductor Scarcity"
        ]

    def predict_90_days(self, location: str) -> List[Dict]:
        """
        Predict disaster risks for the next 90 days.
        """
        predictions = []
        base_date = datetime.now()
        
        for i in range(1, 4):  # Month 1, 2, 3
            prediction_date = base_date + timedelta(days=i*30)
            
            # Weighted probability based on 'real world' signals (simulated)
            prob = random.uniform(0.02, 0.18) 
            disaster = random.choice(self.disaster_types)
            
            # Severity Scale 1-10
            severity = random.randint(4, 9)
            
            predictions.append({
                "month": i,
                "date_horizon": prediction_date.strftime("%Y-%m-%d"),
                "hazard_type": disaster,
                "probability": round(prob, 2),
                "severity_score": severity,
                "mitigation_strategy": self._get_mitigation(disaster),
                "zf_impact_estimate": f"High (Potential {severity*2}% lead time delay)"
            })
            
        return predictions

    def _get_mitigation(self, hazard: str) -> str:
        mitigations = {
            "Tropical Cyclone Surge": "Activate air-freight contingency lanes.",
            "Geopolitical Port Closure": "Reroute via inland rail corridor (Belt and Road).",
            "Labor Strike": "Pre-position safety stock in regional hubs by Month-1.",
            "Energy Price Shock": "Shift to 'Green Corridor' rail routes to minimize fuel surcharges.",
            "Semiconductor Scarcity": "Trigger long-term capacity reservations with Tier-2 suppliers."
        }
        return mitigations.get(hazard, "Increase safety stock buffers.")

# Global instance
ews = EarlyWarningSystem()
