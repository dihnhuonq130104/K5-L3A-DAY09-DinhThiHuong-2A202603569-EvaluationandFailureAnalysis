# Judge audit — replay public

Người thực hiện: **Đinh Thị Hường** (`dihnhuonq130104`). FAIL là lớp dương: judge có nhiệm vụ tìm lỗi. Nguồn: hai CSV public và `python -m lab9.judge --csv data/eval/judge_<tone|helpful>_public.csv --audit 5`. Kết quả máy đọc được lưu trong `reports/submission_evidence.json`.

| Tiêu chí | n | TP / FP / FN / TN | κ | Precision | Recall | Đạt κ≥0,6; P≥0,8; R≥0,7? | Quyết định |
|---|---:|---|---:|---:|---:|---|---|
| tone_ok | 100 | 24 / 4 / 6 / 66 | 0,757 | 0,857 | 0,800 | Có | Chấp nhận cho đánh giá giọng điệu trong phạm vi replay |
| helpful | 100 | 9 / 0 / 21 / 70 | 0,375 | 1,000 | 0,300 | Không | Loại khỏi gate |

## Audit bất đồng

Bảng dưới là phân tích lại các câu đã có trong CSV và ghi chú của người gán nhãn; không phải một vòng gán nhãn độc lập mới.

| Case | Judge | Người | Đánh giá dựa trên bằng chứng | Điều chỉnh rubric cần thử rồi calibration lại |
|---|---|---|---|---|
| H-008 | PASS | FAIL | Đồng ý nhãn người: “Em ... nha ... check” quá suồng sã theo chuẩn CS trong CSV. | Thêm ví dụ giáp ranh thân thiện/suồng sã; không coi mọi giọng thân thiện là đạt. |
| H-017 | PASS | FAIL | Theo nhãn và note, “bạn ... rồi nha” không phù hợp đối tượng khách. Tuổi khách không tự suy ra từ reply đơn lẻ. | Cấp ngữ cảnh xưng hô khi có; ghi rõ giới hạn nếu thiếu ngữ cảnh. |
| H-029 | PASS | FAIL | Đồng ý nhãn người: “không cần nhắn thêm” mang giọng ra lệnh dù có “Dạ, vui lòng”. | Chấm toàn bộ nội dung, thêm ví dụ có từ lịch sự nhưng vẫn áp đặt. |
| H-042 | FAIL | PASS | Đồng ý nhãn người: thông báo số tiền và thời gian 3–5 ngày rõ, lịch sự; không bắt buộc lời xin lỗi ở mọi reply. | Bỏ tiêu chí máy móc “thiếu xin lỗi = FAIL”. |
| H-051 | FAIL | PASS | Đồng ý nhãn người: từ “refund” được chuẩn CS LogiX trong CSV cho phép. | Bổ sung danh sách thuật ngữ được phép và ví dụ; không phạt mọi từ tiếng Anh. |
| H-063 | PASS | FAIL | Đồng ý nhãn người: hứa “sẽ hoàn thêm” vượt kết quả được xác nhận. | Cấm hứa hành động chưa được hệ thống xác nhận; kiểm tra factuality tách khỏi tone. |
| HL-015 | PASS | FAIL | Người đúng về factuality: reply 55.000đ trong khi note ledger=40.000đ. | Tiền phải đối chiếu ledger bằng code; lời văn lịch sự không bù được sai tiền. |
| HL-016 | PASS | FAIL | Người đúng: lời xin lỗi dài nhưng báo 55.000đ thay vì ledger=35.000đ. | Đặt điều kiện sự thật trước văn phong; không cộng điểm vì độ dài hoặc số lời xin lỗi. |

## Hiệu chỉnh và quyết định

Tone có observed failure rate=0,28, sensitivity=0,8, specificity=66/70. Rogan–Gladen cho tỉ lệ lỗi hiệu chỉnh=0,30. Helpful có observed=0,09 và hiệu chỉnh=0,30; con số hiệu chỉnh không cứu được judge có recall quá thấp. Judge này bỏ sót 21/30 lỗi, dù precision=1, nên dùng làm gate sẽ cho lọt nhiều câu sai tiền.

Tiền và approval dùng code. `ReplyAmountCorrect` đối chiếu số tiền được khẳng định trong reply với ledger; `RefundAmountCorrect` đối chiếu ledger với nhãn. Tone chỉ có thể dùng trong phạm vi tiêu chí đã hiệu chuẩn, chưa được đưa vào blocking metric hiện tại.

Chưa sửa CSV hoặc kết luận đã calibration lại rubric mới. Sau khi sửa rubric cần một tập held-out mới, người gán nhãn độc lập, rồi đo lại κ/P/R. Kappa không xác định phải FAIL; mẫu nhỏ và replay công khai có thể đánh giá quá cao khả năng judge trên dữ liệu mới.
