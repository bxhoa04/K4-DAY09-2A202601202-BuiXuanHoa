"""
src/agents/payment.py
--------------------------------------------------------------------------------
Payment Agent — Responsible for payment rows aggregation, expected total calculation,
financial reconciliation, and split payment detection.
Updates AgentHandoffState directly.
Phụ trách bởi: Thành viên B
"""

from typing import List
from src.data_loader import DataLoader
from src.schema import AgentHandoffState


class PaymentAgent:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def process(self, state: AgentHandoffState) -> AgentHandoffState:
        """
        Processes payments and items for claimed_order_id.
        Calculates:
          - item_total_brl, freight_total_brl, expected_total_brl
          - payment_total_brl, difference_brl, reconciled
          - payment_ids, payment_types, split_payment flag
        Handles null cases for orders without items.
        """
        claimed_order_id = state.claimed_order_id
        items = self.data_loader.get_items(claimed_order_id)
        payments = self.data_loader.get_payments(claimed_order_id)

        # 1. Populate Payment IDs & Payment Types
        payment_ids = [
            f"{claimed_order_id}:{pay['payment_sequential']}"
            for pay in payments
        ]
        
        payment_types: List[str] = []
        payment_total = 0.0
        for pay in payments:
            ptype = pay["payment_type"]
            if ptype not in payment_types:
                payment_types.append(ptype)
            payment_total += pay["payment_value"]

        state.payment_ids = payment_ids[:5]  # Enforce max 5 limit
        state.payment_types = payment_types
        state.split_payment = len(payments) >= 2

        # 2. Reconcile with Items & Freight
        if not items:
            # According to EC_POLICY_V2: For orders without item rows,
            # expected_total_brl, difference_brl, and reconciled must be null.
            state.item_total_brl = None
            state.freight_total_brl = None
            state.expected_total_brl = None
            state.payment_total_brl = round(payment_total, 2) if payments else None
            state.difference_brl = None
            state.reconciled = None
            return state

        item_total = sum(item["price"] for item in items)
        freight_total = sum(item["freight_value"] for item in items)
        expected_total = item_total + freight_total
        difference = payment_total - expected_total
        is_reconciled = abs(difference) <= 0.10

        state.item_total_brl = round(item_total, 2)
        state.freight_total_brl = round(freight_total, 2)
        state.expected_total_brl = round(expected_total, 2)
        state.payment_total_brl = round(payment_total, 2)
        state.difference_brl = round(difference, 2)
        state.reconciled = is_reconciled

        return state