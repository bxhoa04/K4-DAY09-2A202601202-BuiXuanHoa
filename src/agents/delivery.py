"""
Delivery Agent — Responsible for delivery timelines, variance calculations & seller handoff analysis.
Updates AgentHandoffState directly.
"""

from typing import Optional
from datetime import datetime
from src.data_loader import DataLoader
from src.schema import AgentHandoffState, SellerHandoffItem


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str or str(dt_str).strip() == "" or str(dt_str).lower() == "nan":
        return None
    try:
        return datetime.strptime(str(dt_str).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def calculate_variance_hours(dt1: Optional[datetime], dt2: Optional[datetime]) -> Optional[float]:
    """Calculate (dt1 - dt2) in hours, rounded to 2 decimal places."""
    if not dt1 or not dt2:
        return None
    diff_seconds = (dt1 - dt2).total_seconds()
    return round(diff_seconds / 3600.0, 2)


class DeliveryAgent:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def process(self, state: AgentHandoffState) -> AgentHandoffState:
        """
        Analyze delivery timelines, seller handoff deadlines, and compute variances.
        Updates and returns AgentHandoffState.
        """
        claimed_order_id = state.claimed_order_id
        order = self.data_loader.get_order(claimed_order_id)
        
        if not order:
            state.delivered_at = None
            state.estimated_delivery_at = None
            state.carrier_handoff_at = None
            state.delivery_variance_hours = None
            state.seller_handoff_analysis = []
            state.late_handoff_seller_ids = []
            return state

        delivered_str = order.get("order_delivered_customer_date")
        estimated_str = order.get("order_estimated_delivery_date")
        carrier_handoff_str = order.get("order_delivered_carrier_date")

        dt_delivered = parse_datetime(delivered_str)
        dt_estimated = parse_datetime(estimated_str)
        dt_carrier_handoff = parse_datetime(carrier_handoff_str)

        state.delivered_at = delivered_str if dt_delivered else None
        state.estimated_delivery_at = estimated_str if dt_estimated else None
        state.carrier_handoff_at = carrier_handoff_str if dt_carrier_handoff else None
        state.delivery_variance_hours = calculate_variance_hours(dt_delivered, dt_estimated)

        # Analyze Seller Handoffs
        items = self.data_loader.get_items(claimed_order_id)
        seller_limits = {}
        seller_limit_strs = {}

        for item in items:
            sid = item["seller_id"]
            limit_str = item.get("shipping_limit_date")
            limit_dt = parse_datetime(limit_str)

            if sid not in seller_limits or (limit_dt and (not seller_limits[sid] or limit_dt < seller_limits[sid])):
                seller_limits[sid] = limit_dt
                seller_limit_strs[sid] = limit_str

        seller_handoff_analysis = []
        late_handoff_seller_ids = []

        for sid, limit_dt in seller_limits.items():
            limit_str = seller_limit_strs[sid]
            handoff_variance = calculate_variance_hours(dt_carrier_handoff, limit_dt)
            is_late = handoff_variance is not None and handoff_variance > 0

            item_analysis = SellerHandoffItem(
                seller_id=sid,
                shipping_limit_at=limit_str,
                handoff_variance_hours=handoff_variance,
                late_handoff=is_late
            )
            seller_handoff_analysis.append(item_analysis)

            if is_late and sid not in late_handoff_seller_ids:
                late_handoff_seller_ids.append(sid)

        state.seller_handoff_analysis = seller_handoff_analysis
        state.late_handoff_seller_ids = late_handoff_seller_ids

        return state
