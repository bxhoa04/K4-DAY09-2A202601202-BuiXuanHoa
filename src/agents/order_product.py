"""
Order & Product Agent — Responsible for items, products, sellers & categories.
Updates AgentHandoffState directly.
"""

from typing import List
from src.data_loader import DataLoader
from src.schema import AgentHandoffState


class OrderProductAgent:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def process(self, state: AgentHandoffState) -> AgentHandoffState:
        """
        Extract items, products, sellers, categories and evaluate secondary issue flags.
        Enforces strict array bounds. Updates and returns AgentHandoffState.
        """
        claimed_order_id = state.claimed_order_id
        order = self.data_loader.get_order(claimed_order_id)
        if order:
            state.order_status = order.get("order_status")

        items = self.data_loader.get_items(claimed_order_id)
        
        if not items:
            state.item_ids = []
            state.product_ids = []
            state.category_names = []
            state.seller_ids = []
            state.multi_item_order = False
            state.multi_seller_order = False
            state.multiple_categories = False
            return state

        item_ids = [f"{claimed_order_id}:{item['order_item_id']}" for item in items]
        
        sellers: List[str] = []
        products: List[str] = []
        categories: List[str] = []

        for item in items:
            sid = item["seller_id"]
            pid = item["product_id"]
            cat = self.data_loader.get_product_category(pid)

            if sid not in sellers:
                sellers.append(sid)
            if pid not in products:
                products.append(pid)
            if cat and cat not in categories:
                categories.append(cat)

        # Flag evaluations
        state.multi_item_order = len(items) >= 2
        state.multi_seller_order = len(sellers) >= 2
        state.multiple_categories = len(categories) >= 2

        # Enforce array limits
        state.item_ids = item_ids[:5]
        state.product_ids = products[:5]
        state.category_names = categories[:5]
        state.seller_ids = sellers[:3]

        return state
