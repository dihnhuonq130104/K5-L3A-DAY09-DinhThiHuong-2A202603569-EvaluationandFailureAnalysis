# Trace case — C-002 tin ticket hơn DB

Người thực hiện: **Đinh Thị Hường** (`dihnhuonq130104`).

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`; run `E-seeded_regression-20261118-7ac8` ([report](../src/reports/eval_seeded_regression.json)). |
| Triệu chứng | DB ghi đơn O-202 trễ 2 ngày, nên không được hoàn; ticket tự khai 5 ngày. Ledger của variant hoàn 20.000đ, nhãn yêu cầu 0đ. TrialPass, RefundAmountCorrect và DbFactKept fail. |
| Bước sai đầu tiên | Event **3**, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là đầu tiên | Event 1 handoff chỉ giao công cụ đọc; event 2 investigator trả đúng DB `delay_days=2`, visible=true. Đến event 3 agent mới thay dữ kiện đáng tin bằng lời khách. Quote ở event 4 và refund sau đó là hậu quả. |
| Failure mode | **FM-03 ticket_trust**. |
| Đối chứng | `fixed C-002@11` giữ delay_days=2, không có model_override, quote=0, status=denied và ledger=0. |
| Regression test | `tests/test_lab9_regression.py::test_lab9_c002_ticket_override_regression`: cùng claim/seed, khẳng định TrialPass, RefundAmountCorrect, DbFactKept đều fail trên seeded_regression và pass trên fixed. |
| Chưa chắc chắn | Không suy ra tần suất lỗi của model thật từ MockLLM; approval hợp lệ không chứng minh khách đủ điều kiện chính sách. |

Chạy lại trong `src/`:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= tests/test_lab9_regression.py
```

Bằng chứng đầy đủ: `src/reports/submission_evidence.json`, mục `traces.seeded_regression` và `traces.fixed`. Test bổ sung `test_lab9_reply_amount_matches_committed_effect` kiểm tra FM-08 trên C-008 và C-014: ledger có thể đúng trong khi lời báo hoàn sai.
