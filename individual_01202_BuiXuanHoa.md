# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Bùi Xuân Hòa |
| MSSV            | 2A202601202 |
| Khóa/Lớp        | K4 |
| Vai trò chính   | Data Engine & Context Specialist (Thành viên A) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Data Loader Layer | `src/data_loader.py` | 9 file CSV dữ liệu Olist tại `data/` | Hash map indexing tra cứu O(1) (`DataLoader`) | Hoàn thành |
| Customer Agent | `src/agents/customer.py` | `claimed_order_id`, `AgentHandoffState` | `customer_unique_id`, `related_order_ids` (max 5), `repeat_customer` | Hoàn thành |
| Order & Product Agent | `src/agents/order_product.py` | `claimed_order_id`, `AgentHandoffState` | `item_ids`, `product_ids`, `category_names`, `seller_ids`, `multi_item_order`, `multi_seller_order`, `multiple_categories` | Hoàn thành |
| Delivery Agent | `src/agents/delivery.py` | `claimed_order_id`, `AgentHandoffState` | `delivery_variance_hours`, `seller_handoff_analysis`, `late_handoff_seller_ids` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Tích hợp Data Contract | Thành viên B (`src/schema.py`) | Đã đồng bộ 3 Agent để ghi/đọc trực tiếp trên `AgentHandoffState` của Thành viên B |
| Viết Unit Test Pipeline A | Toàn nhóm (`tests/test_phase1_member_a.py`) | Bộ test tự động kiểm thử toàn bộ dữ liệu ngữ cảnh cho 50 case input |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng Data Engine tra cứu O(1) | `src/data_loader.py` | Nạp 9 CSV Olist trong < 2.2 giây | `.\.venv\Scripts\python tests/test_phase1_member_a.py` |
| Bóc tách ngữ cảnh Khách hàng, Sản phẩm & Vận chuyển | `src/agents/customer.py`<br>`src/agents/order_product.py`<br>`src/agents/delivery.py` | Trích xuất chính xác 100% entities & tính độ lệch trễ hạn làm tròn 2 chữ số | Kiểm tra State Dump dạng JSON trong test output |

**Mô tả output cụ thể:**
Đã trích xuất thành công toàn bộ ngữ cảnh dữ liệu cho 50 đơn hàng khiếu nại, tự động ép hạn mức độ dài mảng (max 5 items, max 5 products, max 5 categories, max 3 sellers) và làm tròn 2 chữ số thập phân cho số giờ trễ hạn vận chuyển (`delivery_variance_hours`, `handoff_variance_hours`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Bài toán yêu cầu đối soát 50 ticket khiếu nại qua 9 bảng CSV Olist. Dữ liệu khiếu nại chỉ có `claimed_order_id`, cần phải join nhanh các bảng liên quan, trích xuất đúng danh tính khách hàng, các sản phẩm, nhà bán hàng và tính toán thời gian trễ hạn giao hàng/bàn giao để làm đầu vào cho Policy Agent.

### Cách triển khai
1. **Nạp & Indexing**: Dùng module `csv` tiêu chuẩn của Python đọc 9 file CSV thành các Python `dict` indexed theo `order_id`, `customer_id`, `customer_unique_id`, `product_id`.
2. **Customer Agent**: Dùng `customer_id` tra cứu `customer_unique_id` và lấy các đơn hàng khác (`related_order_ids`), cắt mảng $\le 5$ phần tử và gắn cờ `repeat_customer`.
3. **OrderProduct Agent**: Bóc tách danh sách `item_ids`, `product_ids`, `category_names`, `seller_ids`, tính các cờ `multi_item_order`, `multi_seller_order`, `multiple_categories`.
4. **Delivery Agent**: Parse mốc thời gian ISO (`YYYY-MM-DD HH:MM:SS`), tính `delivery_variance_hours` = `delivered_at - estimated_at` và `handoff_variance_hours` cho từng seller, làm tròn 2 chữ số thập phân.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `claimed_order_id` từ ticket JSON và instance `DataLoader` |
| Output | `AgentHandoffState` chứa thông tin khách hàng, sản phẩm, sellers và độ lệch giờ trễ hạn |
| Module phụ thuộc | `src/data_loader.py`, `src/schema.py` |
| Module sử dụng output | `PaymentAgent`, `PolicyAgent`, `VerifierAgent` (Thành viên B) |
| Điều kiện lỗi cần xử lý | Đơn hàng hủy/thiếu item (trả mảng rỗng `[]` và `null` cho các phép tính) |

### Cách xác minh

```bash
.\.venv\Scripts\python tests/test_phase1_member_a.py
```

- **Kết quả mong đợi:** 100% tests PASSED, in ra đầy đủ JSON State Dump của `AgentHandoffState`.
- **Kết quả thực tế:** Test chạy thành công trong 2.2 giây, hiển thị chính xác toàn bộ trường dữ liệu của Thành viên A.
- **Artifact/log:** [tests/test_phase1_member_a.py](file:///d:/Aithucchien/K4-DAY09-2A202601202-BuiXuanHoa/tests/test_phase1_member_a.py)

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn giải pháp lưu trữ và truy xuất dữ liệu từ 9 file CSV cho hệ thống Multi-Agent.
- **Các phương án đã cân nhắc:**
  1. Phương án A: Dùng `pandas` DataFrame cho mỗi câu query join.
  2. Phương án B: Nạp dữ liệu vào SQLite in-memory database.
  3. Phương án C (Được chọn): Dùng Python built-in `csv` module đọc và index trực tiếp vào Python Hash Maps (`dict`).
- **Phương án đã chọn:** Phương án C (Python Built-in Dict Indexing).
- **Lý do:** Giúp hệ thống không phụ thuộc vào thư viện bên ngoài (`pandas`), thời gian nạp và tra cứu đạt tốc độ $O(1)$ tức thì, khởi động chỉ mất ~2 giây cho hơn 100,000 dòng dữ liệu.
- **Bằng chứng quyết định phù hợp:** Thời gian thực thi toàn bộ pipeline 50 case chỉ mất **2.2 giây**.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'pydantic'` khi chạy lệnh test `python -m unittest tests/test_phase1_member_a.py`.
- **Lệnh hoặc bước tái hiện:** Chạy lệnh `python` hệ thống mặc định ngoài terminal.
- **Nguyên nhân gốc:** Terminal PowerShell đang gọi Python môi trường toàn cục (chưa cài Pydantic) thay vì gọi Python trong môi trường ảo `.venv`.
- **Cách xử lý:** Cài đặt Pydantic vào `.venv` và gọi chính xác đường dẫn virtualenv: `.\.venv\Scripts\python tests/test_phase1_member_a.py`.
- **Cách xác minh sau khi sửa:** Lệnh chạy mượt mà, trả về kết quả 100% OK.
- **Điều học được:** Luôn chỉ định rõ đường dẫn thực thi môi trường ảo trong các script tự động hóa.

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

**Họ và tên:** Bùi Xuân Hòa  
**Ngày xác nhận:** 2026-08-05  
