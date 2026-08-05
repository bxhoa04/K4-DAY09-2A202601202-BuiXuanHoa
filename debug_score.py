import glob
import json

files = glob.glob("output/EC_*.json")
print(f"🔍 Đang kiểm tra {len(files)} files output...")

errors = 0
for fpath in files:
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
        case_id = data["case_id"]
        
        refund = data["financial_resolution"]["recommended_refund_brl"]
        status = data["case_assessment"]["case_status"]
        primary = data["case_assessment"]["primary_issue"]
        actions = data["resolution_actions"]
        evidences = data["evidence_ids"]
        
        # Check 1: Refund vs Status
        if refund > 0 and status != "action_required":
            print(f"❌ [{case_id}] Refund = {refund} nhưng Status = {status}")
            errors += 1
        elif refund == 0 and status != "no_action":
            print(f"❌ [{case_id}] Refund = 0 nhưng Status = {status}")
            errors += 1
            
        # Check 2: Forbidden Action
        if primary == "valid_split_payment" and "verify_payment_allocation" in actions:
            print(f"❌ [{case_id}] Valid split payment bị dính 'verify_payment_allocation'!")
            errors += 1
            
        # Check 3: Evidence prefix format
        for ev in evidences:
            if not any(ev.startswith(p) for p in ["order:", "item:", "payment:", "seller:", "policy:", "customer:"]):
                print(f"❌ [{case_id}] Evidence sai định dạng prefix: {ev}")
                errors += 1
                break

if errors == 0:
    print("🎉 Không phát hiện lỗi Schema cơ bản. Điểm số thấp có thể do phân loại Primary Issue chưa chuẩn theo EC_POLICY_V2.")
else:
    print(f"⚠️ Phát hiện {errors} lỗi cấu trúc cần sửa!")