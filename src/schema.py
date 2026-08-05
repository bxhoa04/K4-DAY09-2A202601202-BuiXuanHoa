"""
src/schema.py
--------------------------------------------------------------------------------
Định nghĩa Data Models / Schemas bằng Pydantic cho hệ thống Dispute Resolution.
Phụ trách bởi: Thành viên B (Policy, Verifier & Orchestration Specialist)
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# 1. HELPER / EMBEDDED MODELS (Cấu trúc con)
# ==============================================================================

class CaseAssessment(BaseModel):
    primary_issue: str
    secondary_issues: List[str] = Field(default_factory=list)
    case_status: Literal["action_required", "no_action"]
    confidence: float = Field(ge=0.0, le=1.0)


class AffectedEntities(BaseModel):
    order_ids: List[str] = Field(default_factory=list, max_length=5)
    item_ids: List[str] = Field(default_factory=list, max_length=5)
    seller_ids: List[str] = Field(default_factory=list, max_length=3)
    payment_ids: List[str] = Field(default_factory=list, max_length=5)


class CustomerContext(BaseModel):
    customer_unique_id: Optional[str] = None
    related_order_ids: List[str] = Field(default_factory=list, max_length=5)


class ProductContext(BaseModel):
    product_ids: List[str] = Field(default_factory=list, max_length=5)
    category_names: List[str] = Field(default_factory=list, max_length=5)


class SellerHandoffItem(BaseModel):
    seller_id: str
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: bool

    @field_validator('handoff_variance_hours', mode='before')
    def round_hours(cls, v):
        if v is not None:
            return round(float(v), 2)
        return None


class DeliveryAnalysis(BaseModel):
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: List[SellerHandoffItem] = Field(default_factory=list)
    late_handoff_seller_ids: List[str] = Field(default_factory=list)

    @field_validator('delivery_variance_hours', mode='before')
    def round_hours(cls, v):
        if v is not None:
            return round(float(v), 2)
        return None


class PaymentReconciliation(BaseModel):
    currency: str = "BRL"
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    payment_types: List[str] = Field(default_factory=list)

    @field_validator(
        'item_total_brl', 
        'freight_total_brl', 
        'expected_total_brl', 
        'payment_total_brl', 
        'difference_brl', 
        mode='before'
    )
    def round_brl(cls, v):
        if v is not None:
            return round(float(v), 2)
        return None


class RankedCause(BaseModel):
    cause_code: str
    rank: int


class ResponsibleParty(BaseModel):
    party_type: str
    party_id: str


class RootCauseAnalysis(BaseModel):
    ranked_causes: List[RankedCause] = Field(default_factory=list, max_length=3)
    responsible_parties: List[ResponsibleParty] = Field(default_factory=list, max_length=3)


class FinancialResolution(BaseModel):
    currency: str = "BRL"
    recommended_refund_brl: float

    @field_validator('recommended_refund_brl', mode='before')
    def round_brl(cls, v):
        if v is not None:
            return round(float(v), 2)
        return 0.0


# ==============================================================================
# 2. OUTPUT ROOT SCHEMA (Cấu trúc JSON hoàn chỉnh xuất ra output/)
# ==============================================================================

class CaseOutputSchema(BaseModel):
    """Schema chính dùng cho Verifier Agent kiểm tra và xuất file JSON."""
    case_id: str
    case_assessment: CaseAssessment
    affected_entities: AffectedEntities
    customer_context: CustomerContext
    product_context: ProductContext
    delivery_analysis: DeliveryAnalysis
    payment_reconciliation: PaymentReconciliation
    root_cause_analysis: RootCauseAnalysis
    evidence_ids: List[str] = Field(default_factory=list, max_length=20)
    financial_resolution: FinancialResolution
    resolution_actions: List[str] = Field(default_factory=list, max_length=5)


# ==============================================================================
# 3. INTERNAL HANDOFF STATE SCHEMA (Luồng truyền dữ liệu giữa các Agents)
# ==============================================================================

class AgentHandoffState(BaseModel):
    """
    State chung được truyền qua các Agent:
    DataLoader -> Customer -> OrderProduct -> Delivery -> Payment -> Policy -> Verifier
    """
    case_id: str
    claimed_order_id: str
    policy_version: str = "EC_POLICY_V2"
    
    # Kết quả do Customer Agent điền
    customer_unique_id: Optional[str] = None
    related_order_ids: List[str] = Field(default_factory=list)
    repeat_customer: bool = False

    # Kết quả do Order & Product Agent điền
    order_status: Optional[str] = None
    item_ids: List[str] = Field(default_factory=list)
    product_ids: List[str] = Field(default_factory=list)
    category_names: List[str] = Field(default_factory=list)
    seller_ids: List[str] = Field(default_factory=list)
    multi_item_order: bool = False
    multi_seller_order: bool = False
    multiple_categories: bool = False

    # Kết quả do Delivery Agent điền
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: List[SellerHandoffItem] = Field(default_factory=list)
    late_handoff_seller_ids: List[str] = Field(default_factory=list)

    # Kết quả do Payment Agent điền
    payment_ids: List[str] = Field(default_factory=list)
    payment_types: List[str] = Field(default_factory=list)
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    split_payment: bool = False

    # Kết quả do Policy Agent điền
    primary_issue: Optional[str] = None
    secondary_issues: List[str] = Field(default_factory=list)
    root_cause_code: Optional[str] = None
    responsible_party_type: Optional[str] = None
    responsible_party_ids: List[str] = Field(default_factory=list)
    recommended_refund_brl: float = 0.0
    resolution_actions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0
