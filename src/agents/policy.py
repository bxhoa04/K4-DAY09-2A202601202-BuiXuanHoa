"""
src/agents/policy.py
--------------------------------------------------------------------------------
Policy Agent — Dynamic AI Reasoning Engine.
Sử dụng LLM để đọc văn bản chính sách EC_POLICY_V2, phân tích ngữ cảnh 
đơn hàng và tự động đưa ra quyết định (Primary/Secondary Issues, Refund, Actions).
Phụ trách bởi: Thành viên B
"""

import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from src.schema import AgentHandoffState
from src.llm_client import LocalLLMClient


# Schema cấu trúc Pydantic linh hoạt - Chấp nhận Optional cho cả chuỗi lẫn số tránh lỗi validation
class PolicyDecisionSchema(BaseModel):
    primary_issue: str = Field(
        description="Vấn đề chính: canceled_order_paid, unavailable_order_paid, late_delivery_seller, late_delivery_logistics, valid_split_payment, delivered_on_time, unsupported_late_claim"
    )
    root_cause_code: Optional[str] = Field(
        default="OUT_OF_POLICY_CLAIM",
        description="Mã nguyên nhân gốc tương ứng theo EC_POLICY_V2"
    )
    responsible_party_type: Optional[str] = Field(
        default="platform",
        description="Loại bên chịu trách nhiệm: platform, seller, logistics_provider, hoặc null"
    )
    responsible_party_ids: List[str] = Field(
        default_factory=list, 
        description="Danh sách ID bên chịu trách nhiệm"
    )
    recommended_refund_brl: Optional[float] = Field(
        default=0.0,
        description="Số tiền hoàn đề xuất (BRL)"
    )
    resolution_actions: List[str] = Field(
        default_factory=list,
        description="Danh sách các hành động xử lý tiếp theo (tối đa 5)"
    )

    # Validator tự động biến null (NoneType) thành 0.0 đối với số tiền hoàn
    @field_validator('recommended_refund_brl', mode='before')
    def handle_none_refund(cls, v):
        if v is None:
            return 0.0
        return float(v)


class PolicyAgent:
    def __init__(self):
        self.llm = LocalLLMClient()

    def _build_policy_prompt(self, state: AgentHandoffState) -> str:
        """Tạo Prompt chứa văn bản Quy tắc EC_POLICY_V2 và Context dữ liệu đơn hàng."""
        
        policy_context = f"""
        === CHÍNH SÁCH XỬ LÝ KHIẾU NẠI (EC_POLICY_V2) ===
        Thứ tự ưu tiên xét duyệt từ trên xuống dưới (Mức ưu tiên cao nhất đứng trước):

        1. CANCELED ORDER: Nếu trạng thái đơn là 'canceled' và tổng tiền > 0 -> primary_issue: 'canceled_order_paid', root_cause_code: 'ORDER_CANCELED_AFTER_PAYMENT', hoàn 100% tiền đơn (lấy đúng {state.payment_total_brl or 0.0} BRL), bên chịu trách nhiệm: 'platform' ('OLIST_PLATFORM').
        2. UNAVAILABLE ORDER: Nếu trạng thái đơn là 'unavailable' và tổng tiền > 0 -> primary_issue: 'unavailable_order_paid', root_cause_code: 'ORDER_UNAVAILABLE_AFTER_PAYMENT', hoàn 100% tiền đơn (lấy đúng {state.payment_total_brl or 0.0} BRL), bên chịu trách nhiệm: 'platform' ('OLIST_PLATFORM').
        3. LATE DELIVERY (SELLER FAULT): Nếu giao trễ (delivered_at > estimated_delivery_at) VÀ có Seller bàn giao trễ -> primary_issue: 'late_delivery_seller', root_cause_code: 'SELLER_HANDOFF_AFTER_LIMIT', hoàn tiền phí vận chuyển (lấy đúng {state.freight_total_brl or 0.0} BRL), bên chịu trách nhiệm: 'seller' (danh sách late_handoff_seller_ids).
        4. LATE DELIVERY (CARRIER FAULT): Nếu giao trễ VÀ KHÔNG có Seller bàn giao trễ -> primary_issue: 'late_delivery_logistics', root_cause_code: 'CARRIER_DELIVERED_AFTER_ESTIMATE', hoàn tiền phí vận chuyển (lấy đúng {state.freight_total_brl or 0.0} BRL), bên chịu trách nhiệm: 'logistics_provider' ('LOGISTICS_PROVIDER').
        5. VALID SPLIT PAYMENT: Nếu có thanh toán chia tách (split_payment=True), đã đối soát thành công (reconciled=True) và không trễ hạn -> primary_issue: 'valid_split_payment', root_cause_code: 'MULTIPLE_PAYMENTS_RECONCILED', hoàn 0.0 BRL.
        6. DELIVERED ON TIME: Nếu không trễ hạn và đối soát thành công -> primary_issue: 'delivered_on_time', root_cause_code: 'DELIVERY_WITHIN_ESTIMATE', hoàn 0.0 BRL.
        7. FALLBACK: Nếu ngoài các trường hợp trên -> primary_issue: 'unsupported_late_claim', root_cause_code: 'OUT_OF_POLICY_CLAIM', hoàn 0.0 BRL.

        QUY TẮC VỀ HÀNH ĐỘNG (RESOLUTION ACTIONS):
        - Hành động chính tương ứng: 'issue_full_refund', 'refund_freight', 'explain_valid_split_payment', 'close_case_no_action', 'reject_late_refund'.
        - Nếu late_delivery_seller: Thêm 'review_seller_handoff'.
        - Nếu late_delivery_logistics: Thêm 'review_carrier_delay'.
        - Nếu refund > 0: Thêm 'verify_refund_completion'.
        - Nếu multi_seller_order: Thêm 'coordinate_multi_seller_case'.
        - Nếu split_payment VÀ primary_issue KHÔNG PHẢI 'valid_split_payment': Thêm 'verify_payment_allocation'.
        - Tối đa không quá 5 hành động.

        QUY TẮC ĐỊNH DẠNG JSON:
        - Tuyệt đối KHÔNG trả về `null` cho các trường.
        - Nếu không có hoàn tiền, đặt recommended_refund_brl là 0.0.
        """

        case_data = {
            "order_status": state.order_status,
            "payment_total_brl": state.payment_total_brl or 0.0,
            "freight_total_brl": state.freight_total_brl or 0.0,
            "delivered_at": state.delivered_at,
            "estimated_delivery_at": state.estimated_delivery_at,
            "late_handoff_seller_ids": state.late_handoff_seller_ids,
            "split_payment": getattr(state, "split_payment", False),
            "reconciled": getattr(state, "reconciled", True),
            "multi_item_order": getattr(state, "multi_item_order", False),
            "multi_seller_order": getattr(state, "multi_seller_order", False),
            "repeat_customer": getattr(state, "repeat_customer", False),
            "multiple_categories": getattr(state, "multiple_categories", False)
        }

        prompt = f"""
        {policy_context}

        === DỮ LIỆU ĐƠN HÀNG CẦN ĐÁNH GIÁ ===
        {json.dumps(case_data, indent=2, ensure_ascii=False)}

        Nhiệm vụ: Phân tích kỹ dữ liệu đơn hàng dựa trên văn bản chính sách EC_POLICY_V2 và trả về kết quả JSON tuân thủ Schema:
        ```json
        {{
          "primary_issue": "string",
          "root_cause_code": "string",
          "responsible_party_type": "string",
          "responsible_party_ids": ["string"],
          "recommended_refund_brl": float,
          "resolution_actions": ["string"]
        }}
        ```
        """
        return prompt

    def process(self, state: AgentHandoffState) -> AgentHandoffState:
        """
        Đánh giá EC_POLICY_V2 thông qua LLM Suy Luận.
        """
        prompt = self._build_policy_prompt(state)
        system_prompt = "Bạn là AI Policy Engine chuyên gia về thương mại điện tử. Bạn tuân thủ chính xác 100% văn bản chính sách và luôn trả về định dạng JSON."

        try:
            llm_response = self.llm.generate_response(prompt, system_prompt)
            
            clean_json = llm_response.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            decision_data = json.loads(clean_json)
            decision = PolicyDecisionSchema(**decision_data)

            # Cập nhật kết quả cơ bản từ LLM
            state.primary_issue = decision.primary_issue
            state.root_cause_code = decision.root_cause_code or "OUT_OF_POLICY_CLAIM"
            state.responsible_party_type = decision.responsible_party_type or "platform"
            state.responsible_party_ids = decision.responsible_party_ids
            state.resolution_actions = decision.resolution_actions[:5]

            # --- BỘ LỌC BẢO HIỂM LOGIC (DETERMINISTIC FALLBACK) ---
            refund = decision.recommended_refund_brl or 0.0
            
            # Nếu đơn bị hủy/không có sẵn mà LLM trả ra 0 -> Ép lấy full payment_total_brl
            if state.primary_issue in ["canceled_order_paid", "unavailable_order_paid"] and refund == 0.0:
                refund = state.payment_total_brl or 0.0
                
            # Nếu giao trễ mà LLM trả ra 0 -> Ép lấy phí vận chuyển freight_total_brl
            elif state.primary_issue in ["late_delivery_seller", "late_delivery_logistics"] and refund == 0.0:
                refund = state.freight_total_brl or 0.0

            state.recommended_refund_brl = round(refund, 2)

        except Exception as e:
            # Fallback an toàn nếu LLM gặp sự cố parse JSON
            print(f"⚠️ LLM Policy Reasoning error on case {state.case_id}: {e}")
            state.primary_issue = "unsupported_late_claim"
            state.root_cause_code = "OUT_OF_POLICY_CLAIM"
            state.responsible_party_type = "platform"
            state.recommended_refund_brl = 0.0
            state.resolution_actions = ["reject_late_refund"]

        # Phân tích Secondary Issues
        secondary_issues: List[str] = []
        for issue_key in ["multi_item_order", "multi_seller_order", "split_payment", "repeat_customer", "multiple_categories"]:
            if getattr(state, issue_key, False):
                secondary_issues.append(issue_key)
        state.secondary_issues = secondary_issues

        # Tạo Evidence IDs tự động
        evidence_ids: List[str] = [f"order:{state.claimed_order_id}"]
        if hasattr(state, "item_ids") and state.item_ids:
            evidence_ids.extend([f"item:{i}" for i in state.item_ids])
        if hasattr(state, "payment_ids") and state.payment_ids:
            evidence_ids.extend([f"payment:{p}" for p in state.payment_ids])
        if state.responsible_party_type == "seller":
            evidence_ids.extend([f"seller:{s}" for s in state.responsible_party_ids])
        if state.root_cause_code:
            evidence_ids.append(f"policy:{state.root_cause_code}")

        state.evidence_ids = list(dict.fromkeys(evidence_ids))[:20]
        state.confidence = 0.95

        return state