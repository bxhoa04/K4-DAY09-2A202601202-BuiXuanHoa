"""
Customer Agent — Responsible for customer identity & order history.
Updates AgentHandoffState directly.
"""

from typing import Dict, Any
from src.data_loader import DataLoader
from src.schema import AgentHandoffState


class CustomerAgent:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def process(self, state: AgentHandoffState) -> AgentHandoffState:
        """
        Extract customer identity and related order history.
        Enforces maximum limit of 5 related order IDs.
        Updates and returns AgentHandoffState.
        """
        claimed_order_id = state.claimed_order_id
        customer_unique_id = self.data_loader.get_customer_unique_id(claimed_order_id)
        
        if not customer_unique_id:
            state.customer_unique_id = None
            state.related_order_ids = []
            state.repeat_customer = False
            return state

        related_orders = self.data_loader.get_related_orders(customer_unique_id, claimed_order_id)
        
        state.customer_unique_id = customer_unique_id
        state.related_order_ids = related_orders[:5]  # Enforce max 5 limit
        state.repeat_customer = len(related_orders) > 0

        return state
