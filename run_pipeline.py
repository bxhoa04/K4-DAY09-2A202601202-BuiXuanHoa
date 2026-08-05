"""
run_pipeline.py
--------------------------------------------------------------------------------
Script chính điều phối toàn bộ Multi-Agent Dispute Resolution System.
Phụ trách bởi: Thành viên B (Orchestrator)

Luồng xử lý cho từng case:
Input JSON -> DataLoader -> CustomerAgent -> OrderProductAgent 
           -> DeliveryAgent -> PaymentAgent -> PolicyAgent 
           -> VerifierAgent -> Output JSON & trace.jsonl
"""

import os
import json
import time
from typing import List

from src.data_loader import DataLoader
from src.schema import AgentHandoffState
from src.agents.customer import CustomerAgent
from src.agents.order_product import OrderProductAgent
from src.agents.delivery import DeliveryAgent
from src.agents.payment import PaymentAgent
from src.agents.policy import PolicyAgent
from src.agents.verifier import VerifierAgent


def main():
    print("🚀 Đang khởi tạo hệ thống Multi-Agent Dispute Resolution...")
    
    # 1. Khởi tạo Data Loader và nạp dữ liệu Olist vào bộ nhớ O(1)
    data_loader = DataLoader(data_dir="data")
    data_loader.load_data()
    print("✅ Đã nạp thành công dữ liệu Olist CSV.")

    # 2. Khởi tạo các Agents
    customer_agent = CustomerAgent(data_loader)
    order_product_agent = OrderProductAgent(data_loader)
    delivery_agent = DeliveryAgent(data_loader)
    payment_agent = PaymentAgent(data_loader)
    policy_agent = PolicyAgent()
    verifier_agent = VerifierAgent(output_dir="output")

    input_dir = "input"
    trace_file = "trace.jsonl"
    
    # Chuẩn bị file trace.jsonl mới (ghi đè lượt chạy mới nhất)
    if os.path.exists(trace_file):
        os.remove(trace_file)

    # 3. Lấy danh sách 50 file input (EC_001.json đến EC_050.json)
    input_files = [f for f in os.listdir(input_dir) if f.startswith("EC_") and f.endswith(".json")]
    input_files.sort()  # Sắp xếp đúng thứ tự từ 001 đến 050

    print(f"🔄 Bắt đầu xử lý {len(input_files)} cases...")

    start_time = time.time()
    successful_cases = 0

    with open(trace_file, "a", encoding="utf-8") as trace_f:
        for filename in input_files:
            file_path = os.path.join(input_dir, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                input_data = json.load(f)

            case_id = input_data["case_id"]
            claimed_order_id = input_data["customer_request"]["claimed_order_id"]
            policy_version = input_data.get("policy_version", "EC_POLICY_V2")

            # Giai đoạn 1: Khởi tạo State ban đầu
            state = AgentHandoffState(
                case_id=case_id,
                claimed_order_id=claimed_order_id,
                policy_version=policy_version
            )

            # Giai đoạn 2 & 3: Chạy luồng Handoff qua từng Agent
            state = customer_agent.process(state)
            state = order_product_agent.process(state)
            state = delivery_agent.process(state)
            state = payment_agent.process(state)
            state = policy_agent.process(state)

            # Giai đoạn 4: QC & Export JSON Output
            final_output = verifier_agent.process_and_export(state)
            successful_cases += 1

            # Ghi Log Handoff Trace vào trace.jsonl theo yêu cầu đề bài
            trace_entry = {
                "case_id": case_id,
                "claimed_order_id": claimed_order_id,
                "primary_issue": state.primary_issue,
                "secondary_issues": state.secondary_issues,
                "recommended_refund_brl": state.recommended_refund_brl,
                "resolution_actions": state.resolution_actions,
                "status": "COMPLETED"
            }
            trace_f.write(json.dumps(trace_entry, ensure_ascii=False) + "\n")

    total_time = round(time.time() - start_time, 2)
    print(f"🎉 Hoàn tất {successful_cases}/{len(input_files)} cases trong {total_time}s!")
    print(f"📁 Kết quả JSON đã ghi tại thư mục: output/")
    print(f"📝 Trace chạy đã ghi tại: {trace_file}")


if __name__ == "__main__":
    main()