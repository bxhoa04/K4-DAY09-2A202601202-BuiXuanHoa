"""
src/agents/verifier.py
--------------------------------------------------------------------------------
Verifier Agent — Quality Control & Output Exporter.
Validates state against Pydantic schema (bounds, types, nulls),
formats the final JSON payload, and writes output to file.
Phụ trách bởi: Thành viên B
"""

import os
import json
from typing import Dict, Any
from src.schema import (
    AgentHandoffState,
    CaseOutputSchema,
    CaseAssessment,
    AffectedEntities,
    CustomerContext,
    ProductContext,
    DeliveryAnalysis,
    PaymentReconciliation,
    RootCauseAnalysis,
    FinancialResolution,
    RankedCause,
    ResponsibleParty
)


class VerifierAgent:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def process_and_export(self, state: AgentHandoffState) -> Dict[str, Any]:
        """
        Validates state, builds CaseOutputSchema dictionary, and saves JSON.
        """
        # 1. Determine case_status based on recommended refund
        refund = state.recommended_refund_brl or 0.0
        case_status = "action_required" if refund > 0 else "no_action"

        # 2. Map Assessment
        assessment = CaseAssessment(
            primary_issue=state.primary_issue or "unsupported_late_claim",
            secondary_issues=state.secondary_issues,
            case_status=case_status,
            confidence=state.confidence
        )

        # 3. Map Affected Entities
        entities = AffectedEntities(
            order_ids=[state.claimed_order_id],
            item_ids=state.item_ids,
            seller_ids=state.seller_ids,
            payment_ids=state.payment_ids
        )

        # 4. Map Customer Context
        customer_ctx = CustomerContext(
            customer_unique_id=state.customer_unique_id,
            related_order_ids=state.related_order_ids
        )

        # 5. Map Product Context
        product_ctx = ProductContext(
            product_ids=state.product_ids,
            category_names=state.category_names
        )

        # 6. Map Delivery Analysis
        delivery_ana = DeliveryAnalysis(
            delivered_at=state.delivered_at,
            estimated_delivery_at=state.estimated_delivery_at,
            carrier_handoff_at=state.carrier_handoff_at,
            delivery_variance_hours=state.delivery_variance_hours,
            seller_handoff_analysis=state.seller_handoff_analysis,
            late_handoff_seller_ids=state.late_handoff_seller_ids
        )

        # 7. Map Payment Reconciliation
        payment_rec = PaymentReconciliation(
            currency="BRL",
            item_total_brl=state.item_total_brl,
            freight_total_brl=state.freight_total_brl,
            expected_total_brl=state.expected_total_brl,
            payment_total_brl=state.payment_total_brl,
            difference_brl=state.difference_brl,
            reconciled=state.reconciled,
            payment_types=state.payment_types
        )

        # 8. Map Root Cause Analysis
        ranked_causes = []
        if state.root_cause_code:
            ranked_causes.append(RankedCause(cause_code=state.root_cause_code, rank=1))

        resp_parties = []
        if state.responsible_party_type:
            if state.responsible_party_ids:
                for pid in state.responsible_party_ids:
                    resp_parties.append(ResponsibleParty(party_type=state.responsible_party_type, party_id=pid))
            else:
                resp_parties.append(ResponsibleParty(party_type=state.responsible_party_type, party_id="NONE"))

        root_cause_ana = RootCauseAnalysis(
            ranked_causes=ranked_causes,
            responsible_parties=resp_parties
        )

        # 9. Map Financial Resolution
        fin_res = FinancialResolution(
            currency="BRL",
            recommended_refund_brl=refund
        )

        # 10. Build & Validate via Pydantic Schema
        output_data = CaseOutputSchema(
            case_id=state.case_id,
            case_assessment=assessment,
            affected_entities=entities,
            customer_context=customer_ctx,
            product_context=product_ctx,
            delivery_analysis=delivery_ana,
            payment_reconciliation=payment_rec,
            root_cause_analysis=root_cause_ana,
            evidence_ids=state.evidence_ids,
            financial_resolution=fin_res,
            resolution_actions=state.resolution_actions
        )

        # 11. Convert to Dict & Export JSON
        final_dict = output_data.model_dump()

        output_path = os.path.join(self.output_dir, f"{state.case_id}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_dict, f, ensure_ascii=False, indent=2)

        return final_dict