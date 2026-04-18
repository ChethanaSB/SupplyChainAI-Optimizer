"""
ledger.py — Blockchain-inspired CO2 Green Ledger.
Records immutable logs of CO2 emissions for ZF Supply Chain.
"""
import hashlib
import json
import time
from typing import List, Dict

class Block:
    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        value = str(self.index) + str(self.timestamp) + json.dumps(self.data) + self.previous_hash
        return hashlib.sha256(value.encode()).hexdigest()

class CO2Blockchain:
    def __init__(self):
        self.chain: List[Block] = [self.create_genesis_block()]

    def create_genesis_block(self) -> Block:
        return Block(0, time.time(), {"message": "ZF Green Ledger Genesis"}, "0")

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_emission_record(self, route_id: str, co2_kg: float, carrier: str):
        """Append a new emission record (smart contract-like execution)."""
        data = {
            "route_id": route_id,
            "co2_kg": co2_kg,
            "carrier": carrier,
            "verification": "ZF-ENVIRONMENTAL-CERT-V1"
        }
        new_block = Block(
            len(self.chain),
            time.time(),
            data,
            self.get_latest_block().hash
        )
        self.chain.append(new_block)
        return new_block

    def get_chain_data(self) -> List[Dict]:
        return [
            {
                "index": b.index,
                "timestamp": b.timestamp,
                "data": b.data,
                "hash": b.hash,
                "previous_hash": b.previous_hash
            }
            for b in self.chain
        ]

# Global singleton for the demo
carbon_ledger = CO2Blockchain()
