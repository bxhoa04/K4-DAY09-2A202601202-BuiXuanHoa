"""
Unit Test for Member A — Integrated with AgentHandoffState from src/scheme.py.
Pipeline: DataLoader -> CustomerAgent -> OrderProductAgent -> DeliveryAgent
"""

import sys
import os
import unittest
import json

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader import DataLoader
from src.schema import AgentHandoffState
from src.agents.customer import CustomerAgent
from src.agents.order_product import OrderProductAgent
from src.agents.delivery import DeliveryAgent


class TestMemberAPhase1WithHandoffState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n==================================================")
        print(" [SETUP] Loading 9 Olist CSV Datasets...")
        print("==================================================")
        cls.data_loader = DataLoader(data_dir="data")
        cls.data_loader.load_data()
        cls.customer_agent = CustomerAgent(cls.data_loader)
        cls.order_prod_agent = OrderProductAgent(cls.data_loader)
        cls.delivery_agent = DeliveryAgent(cls.data_loader)
        print(" -> Data loaded successfully!\n")

    def test_pipeline_member_a(self):
        sample_oid = "e481f51cbdc54678b7cc49136f2d6af7"
        print("--------------------------------------------------")
        print(f" [PIPELINE MEMBER A] Running test for order: {sample_oid}")
        print("--------------------------------------------------")
        
        # 1. Initialize State
        state = AgentHandoffState(
            case_id="EC_001",
            claimed_order_id=sample_oid
        )

        # 2. Customer Agent
        state = self.customer_agent.process(state)
        self.assertIsNotNone(state.customer_unique_id)
        self.assertLessEqual(len(state.related_order_ids), 5)

        # 3. Order & Product Agent
        state = self.order_prod_agent.process(state)
        self.assertGreater(len(state.item_ids), 0)
        self.assertLessEqual(len(state.item_ids), 5)
        self.assertLessEqual(len(state.seller_ids), 3)

        # 4. Delivery Agent
        state = self.delivery_agent.process(state)
        self.assertIsNotNone(state.delivered_at)

        # Print State Dump
        print(" [STATE DUMP AFTER MEMBER A PIPELINE]:")
        print(json.dumps(state.model_dump(), indent=2, ensure_ascii=False))
        print(" -> PASSED PIPELINE MEMBER A!\n")


if __name__ == "__main__":
    unittest.main()
