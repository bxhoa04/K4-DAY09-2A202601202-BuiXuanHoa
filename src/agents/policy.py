"""
src/agents/policy.py
--------------------------------------------------------------------------------
Policy Agent — Evaluates EC_POLICY_V2 rules in strict priority order.
Determines primary issue, secondary issues, responsible parties, root cause code,
refund amount, evidence IDs, and resolution actions.
Updates AgentHandoffState directly.
Phụ trách bởi: Thành viên B
"""

from typing import List
from src.schema import AgentHandoffState
from src.llm_client import LocalLLMClient

class PolicyAgent:
    def __init__(self):
        self.llm = LocalLLMClient()

    def generate_explanation_with_llm(self, primary_issue: str, refund_brl: float) -> str:
        """Sử dụng Ollama Local để sinh giải thích ngắn gọn bằng LLM."""
        system_prompt = "Bạn là trợ lý Chăm sóc khách hàng thương mại điện tử chuyên nghiệp."
        prompt = f"""
        Dựa vào kết quả điều tra khiếu nại:
        - Vấn đề chính: {primary_issue}
        - Khoản tiền hoàn: {refund_brl} BRL
        Hãy tóm tắt ngắn gọn trong 1 câu giải thích cho khách hàng lý do xử lý.
        """
        return self.llm.generate_response(prompt, system_prompt)

    def process(self, state: AgentHandoffState) -> AgentHandoffState:
        """
        Evaluates EC_POLICY_V2 on state context and sets policy output fields.
        """
        order_status = state.order_status
        payment_total = state.payment_total_brl or 0.0
        freight_total = state.freight_total_brl or 0.0
        
        delivered_at = state.delivered_at
        estimated_delivery_at = state.estimated_delivery_at
        
        is_late_delivery = False
        if delivered_at and estimated_delivery_at:
            is_late_delivery = delivered_at > estimated_delivery_at

        has_late_seller = len(state.late_handoff_seller_ids) > 0

        # ======================================================================
        # 1. Primary Issue Determination (Strict Top-to-Bottom Priority Order)
        # ======================================================================
        primary_issue = None
        root_cause_code = None
        responsible_party_type = None
        responsible_party_ids: List[str] = []
        recommended_refund_brl = 0.0
        primary_action = None

        if order_status == "canceled" and payment_total > 0:
            primary_issue = "canceled_order_paid"
            root_cause_code = "ORDER_CANCELED_AFTER_PAYMENT"
            responsible_party_type = "platform"
            responsible_party_ids = ["OLIST_PLATFORM"]
            recommended_refund_brl = payment_total
            primary_action = "issue_full_refund"

        elif order_status == "unavailable" and payment_total > 0:
            primary_issue = "unavailable_order_paid"
            root_cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            responsible_party_type = "platform"
            responsible_party_ids = ["OLIST_PLATFORM"]
            recommended_refund_brl = payment_total
            primary_action = "issue_full_refund"

        elif is_late_delivery and has_late_seller:
            primary_issue = "late_delivery_seller"
            root_cause_code = "SELLER_HANDOFF_AFTER_LIMIT"
            responsible_party_type = "seller"
            responsible_party_ids = state.late_handoff_seller_ids[:3]
            recommended_refund_brl = freight_total
            primary_action = "refund_freight"

        elif is_late_delivery and not has_late_seller:
            primary_issue = "late_delivery_logistics"
            root_cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            responsible_party_type = "logistics_provider"
            responsible_party_ids = ["LOGISTICS_PROVIDER"]
            recommended_refund_brl = freight_total
            primary_action = "refund_freight"

        elif state.split_payment and state.reconciled is True:
            primary_issue = "valid_split_payment"
            root_cause_code = "MULTIPLE_PAYMENTS_RECONCILED"
            responsible_party_type = None
            responsible_party_ids = []
            recommended_refund_brl = 0.0
            primary_action = "explain_valid_split_payment"

        elif not is_late_delivery and state.reconciled is True:
            primary_issue = "unsupported_late_claim"
            root_cause_code = "DELIVERY_WITHIN_ESTIMATE"
            responsible_party_type = None
            responsible_party_ids = []
            recommended_refund_brl = 0.0
            primary_action = "reject_late_refund"

        else:
            # Fallback default if edge case does not match
            primary_issue = "unsupported_late_claim"
            root_cause_code = "DELIVERY_WITHIN_ESTIMATE"
            responsible_party_type = None
            responsible_party_ids = []
            recommended_refund_brl = 0.0
            primary_action = "reject_late_refund"

        state.primary_issue = primary_issue
        state.root_cause_code = root_cause_code
        state.responsible_party_type = responsible_party_type
        state.responsible_party_ids = responsible_party_ids
        state.recommended_refund_brl = round(recommended_refund_brl, 2)

        # ======================================================================
        # 2. Secondary Issues Determination (Strict Business Priority Order)
        # ======================================================================
        secondary_issues: List[str] = []
        if state.multi_item_order:
            secondary_issues.append("multi_item_order")
        if state.multi_seller_order:
            secondary_issues.append("multi_seller_order")
        if state.split_payment:
            secondary_issues.append("split_payment")
        if state.repeat_customer:
            secondary_issues.append("repeat_customer")
        if state.multiple_categories:
            secondary_issues.append("multiple_categories")

        state.secondary_issues = secondary_issues

        # ======================================================================
        # 3. Action Sequence Determination
        # ======================================================================
        actions: List[str] = [primary_action]

        # Action 1: Handoff/Carrier review
        if primary_issue == "late_delivery_seller":
            actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            actions.append("review_carrier_delay")

        # Action 2: Refund completion verification
        if recommended_refund_brl > 0:
            actions.append("verify_refund_completion")

        # Action 3: Multi-seller coordination
        if "multi_seller_order" in secondary_issues:
            actions.append("coordinate_multi_seller_case")

        # Action 4: Payment allocation verification
        # Note: Do NOT add if primary issue is valid_split_payment
        if "split_payment" in secondary_issues and primary_issue != "valid_split_payment":
            actions.append("verify_payment_allocation")

        state.resolution_actions = actions[:5]  # Enforce max 5 limit

        # ======================================================================
        # 4. Evidence IDs Construction
        # ======================================================================
        evidence_ids: List[str] = [f"order:{state.claimed_order_id}"]

        for item_id in state.item_ids:
            evidence_ids.append(f"item:{item_id}")

        for pay_id in state.payment_ids:
            evidence_ids.append(f"payment:{pay_id}")

        if responsible_party_type == "seller":
            for sid in responsible_party_ids:
                evidence_ids.append(f"seller:{sid}")

        if root_cause_code:
            evidence_ids.append(f"policy:{root_cause_code}")

        state.evidence_ids = evidence_ids[:20]  # Enforce max 20 limit
        state.confidence = 1.0

        return state