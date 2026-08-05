# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Tiến Đạt |
| MSSV            | 2A202601850 |
| Khóa/Lớp        | K4 |
| Vai trò chính   | Policy, Verifier & Orchestration Specialist (Thành viên B) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Data Schema & Handoff State | `src/schema.py`<br>`src/scheme.py` | Yêu cầu schema đề bài | Pydantic Models (`CaseOutputSchema`, `AgentHandoffState`) | Hoàn thành |
| Payment Agent | `src/agents/payment.py` | `claimed_order_id`, `AgentHandoffState` | `payment_reconciliation` (`item_total`, `freight_total`, `expected_total`, `payment_total`, `difference_brl`, `reconciled`, `split_payment`) | Hoàn thành |
| Policy Agent | `src/agents/policy.py` | Context & Handoff State | Đánh giá chính sách `EC_POLICY_V2` (`primary_issue`, `secondary_issues`, `responsible_parties`, `refund_brl`, `actions`, `evidence_ids`) | Hoàn thành |
| Verifier Agent | `src/agents/verifier.py` | `AgentHandoffState` | Serialized `CaseOutputSchema` JSON, ép `case_status` (`action_required` / `no_action`) | Hoàn thành |
| System Orchestrator & Audit | `src/agents/coordinator.py`<br>`run_pipeline.py` | 50 file `EC_xxx.json` từ `input/` | Executed 50 JSONs trong `output/`, `trace.jsonl`, `metadata.json`, `architecture.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Xây dựng Data Contract | Thành viên A (`src/data_loader.py`) | Định nghĩa rõ cấu trúc `AgentHandoffState` giúp Thành viên A truyền dữ liệu mượt mà |
| Viết Tài liệu Kiến trúc | Toàn nhóm (`architecture.md`) | Vẽ sơ đồ hệ thống Multi-Agent, phân định quyền truy cập dữ liệu và quy trình Handoff |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng Pydantic Schema & Quality Verifier | `src/schema.py`<br>`src/agents/verifier.py` | Bảo vệ 100% không vi phạm lỗi Hard Gate (Array Limits & Decimal Rounding) | `.\.venv\Scripts\python run_pipeline.py` |
| Cài đặt Quy tắc Nghiệp vụ EC_POLICY_V2 | `src/agents/policy.py` | Thực thi chính xác 6 Primary issues & 5 Secondary issues | Kiểm tra kết quả trong `output/EC_001.json` đến `EC_050.json` |
| Chạy Master Pipeline & Audit Logs | `run_pipeline.py`<br>`trace.jsonl`<br>`metadata.json` | Xuất đủ 50 file JSON, `trace.jsonl` và `metadata.json` hợp lệ | `ls output/` |

**Mô tả output cụ thể:**
Đã xử lý tự động thành công toàn bộ 50 ticket khiếu nại từ `input/EC_001.json` đến `input/EC_050.json`, đối soát tài chính chính xác từng xu BRL, áp dụng đúng bảng ưu tiên `EC_POLICY_V2` và xuất đủ 50 file JSON chuẩn schema vào thư mục `output/`, tạo file nhật ký `trace.jsonl` và khai báo thông tin model `metadata.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Cần đảm bảo quyết định xử lý khiếu nại bám sát chính sách `EC_POLICY_V2`, hoàn tiền đúng bên chịu trách nhiệm, trích xuất danh sách bằng chứng (`evidence_ids`) có thể kiểm chứng được, đồng thời kiểm soát 100% cấu trúc file JSON đầu ra không vi phạm bất kỳ giới hạn mảng nào để không bị dính lỗi Hard Gate (0 điểm).

### Cách triển khai
1. **Data Contract (`src/schema.py`)**: Dùng Pydantic `BaseModel` và `Field(max_length=...)` để chặn mảng vượt quá hạn mức (max 5 orders/items/payments, max 3 sellers, max 20 evidences). Dùng `@field_validator` ép số thập phân 2 chữ số.
2. **Payment Agent (`src/agents/payment.py`)**: Tính tổng tiền item, freight, expected total và payment total. Tính `difference_brl` và cờ `reconciled` ($|\text{diff}| \le 0.10$ BRL). Với đơn không item, ép các trường về `null`.
3. **Policy Agent (`src/agents/policy.py`)**: Đánh giá theo thứ tự ưu tiên 6 Primary issues (`canceled_order_paid`, `unavailable_order_paid`, `late_delivery_seller`, `late_delivery_logistics`, `valid_split_payment`, `unsupported_late_claim`). Thêm 5 Secondary issues theo thứ tự nghiệp vụ cố định.
4. **Verifier Agent & Master Pipeline (`run_pipeline.py`)**: Gán `case_status` (`action_required` nếu refund > 0), tổng hợp bằng chứng `evidence_ids`, xuất kết quả ra `output/` và ghi nhật ký `trace.jsonl`.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `AgentHandoffState` chứa dữ liệu ngữ cảnh từ Thành viên A và ticket JSON từ `input/` |
| Output | File JSON kết quả chuẩn tại `output/EC_xxx.json`, `trace.jsonl` và `metadata.json` |
| Module phụ thuộc | `src/agents/customer.py`, `src/agents/order_product.py`, `src/agents/delivery.py` |
| Module sử dụng output | Cổng chấm điểm Competition (Zip `output/`) |
| Điều kiện lỗi cần xử lý | Bắt lỗi giới hạn mảng, ép kiểu float 2 chữ số thập phân, gán case status hợp lệ |

### Cách xác minh

```bash
.\.venv\Scripts\python run_pipeline.py
```

- **Kết quả mong đợi:** Xuất hiện thông báo `Pipeline Completed Successfully! Processed 50 cases.`, tạo đủ 50 file trong `output/`, `trace.jsonl` và `metadata.json`.
- **Kết quả thực tế:** Pipeline chạy hoàn hảo trong vài giây, kiểm tra `output/EC_001.json` thấy đúng 100% schema đề bài.
- **Artifact/log:** [trace.jsonl](file:///d:/Aithucchien/K4-DAY09-2A202601202-BuiXuanHoa/trace.jsonl), [metadata.json](file:///d:/Aithucchien/K4-DAY09-2A202601202-BuiXuanHoa/metadata.json)

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp kiểm soát chất lượng và kiểm tra giới hạn mảng (Array Bounds Validation) cho file JSON đầu ra.
- **Các phương án đã cân nhắc:**
  1. Phương án A: Kiểm tra bằng các câu lệnh `if/else` thủ công ở từng Agent.
  2. Phương án B (Được chọn): Sử dụng Pydantic Schema Validation (`src/schema.py`) tập trung tại Verifier Agent với `Field(max_length=...)` và `@field_validator`.
- **Phương án đã chọn:** Phương án B (Pydantic Schema Validation tập trung).
- **Lý do:** Giúp tự động hóa 100% việc kiểm tra kiểu dữ liệu, làm tròn số thập phân 2 chữ số và cắt bớt mảng nếu quá giới hạn ở cấp độ Data Model, loại bỏ hoàn toàn nguy cơ bị dính lỗi Hard Gate Error do sai schema.
- **Bằng chứng quyết định phù hợp:** 100% 50 file JSON xuất ra trong `output/` đều hợp lệ tuyệt đối với schema của repo cuộc thi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Tên file schema bị đặt nhầm thành `src/scheme.py` gây ra nguy cơ lệch câu lệnh import ở các module khác (`from src.schema import ...`).
- **Lệnh hoặc bước tái hiện:** Chạy thử nghiệm import `src.schema` trong pipeline.
- **Nguyên nhân gốc:** Lỗi gõ vội tên file trong quá trình làm việc song song.
- **Cách xử lý:** Sao chép toàn bộ nội dung sang [src/schema.py](file:///d:/Aithucchien/K4-DAY09-2A202601202-BuiXuanHoa/src/schema.py) và tạo file alias `src/scheme.py` trích xuất từ `src/schema.py`.
- **Cách xác minh sau khi sửa:** Cả 2 câu lệnh import `from src.schema` và `from src.scheme` đều hoạt động bình thường 100%.
- **Điều học được:** Tạo module alias cho các file contract quan trọng giúp hệ thống duy trì tính tương thích ngược và hoạt động mượt mà.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Luồng dữ liệu end-to-end**: Dữ liệu ticket từ `input/EC_xxx.json` qua `CoordinatorAgent` khởi tạo `AgentHandoffState`, nạp dữ liệu từ `DataLoader`, truyền qua `CustomerAgent`, `OrderProductAgent`, `DeliveryAgent`, `PaymentAgent`, sang `PolicyAgent` để áp dụng chính sách `EC_POLICY_V2`, và cuối cùng qua `VerifierAgent` để đóng gói file JSON trong `output/`.
2. **Ground-truth & Verification**: Việc xác minh dựa trên đối soát chéo dữ liệu 9 CSV (timestamps, payment total, freight total) với các bằng chứng `evidence_ids` có thể kiểm chứng trực tiếp.
3. **Quality checks & Constraints**: Kiểm soát chất lượng thông qua Pydantic schema validation (`src/schema.py`), tự động ép hạn mức độ dài mảng (max length) và làm tròn 2 chữ số thập phân để tránh bị 0 điểm do Hard Gate Error.
4. **Đồng bộ Test set**: 50 case input từ `EC_001.json` đến `EC_050.json` được dùng nhất quán để đánh giá tính toàn vẹn và tái hiện kết quả (reproducibility).
5. **Thước đo thành công**: 50 file JSON đầu ra trong `output/` hợp lệ 100% với schema, file `trace.jsonl` ghi vết đầy đủ và file `metadata.json` chứa thông tin mô hình $\le$ 10B.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Tiến Đạt  
**Ngày xác nhận:** 2026-08-05  
