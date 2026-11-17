# Eval card — LogiX-VN refund agent

Người thực hiện và gate owner: **Đinh Thị Hường** (`dihnhuonq130104`). Ngày: 18/11/2026.

## Phiên bản và nguồn dữ liệu

- Code và grader: commit `3f237a70b04061ec3bcc24d66a2f3c6d332c6d30`, bổ sung integrity tại `537eb0aa0c7f966aac12fb00572977f783be9d43`; code Day 8 gốc: `034c6c421c198dae67a9211d15e2587d5a378972`.
- Python 3.13.5, pydantic-evals 2.68.0, MockLLM; metric spec v1.1 và v2.1.
- V1: 14 item × 5 seed (11, 22, 33, 44, 55), SHA `d2c738675170`; nhãn tách riêng trong `labels_v1.json`.
- Nguồn v1: `lab8_public`, mỗi item có matrix_id, label_by, checked_by và generator; `failure_modes` là coverage dự kiến, không phải nhãn fail của trial.
- V2: 28 item × 5 seed, SHA `a4130b531891`; gồm v1 và 14 adversarial item. Mọi attack mechanism đã map trong fm_map.yaml; build/check cả hai version báo 0 problem(s).

## Kết quả Core

| Report | Run ID |
|---|---|
| [baseline_v1.json](../src/reports/baseline_v1.json) | `E-swarm-20261118-d2c7` |
| [eval_fixed.json](../src/reports/eval_fixed.json) | `E-fixed-20261118-d2c7` |
| [eval_seeded_regression.json](../src/reports/eval_seeded_regression.json) | `E-seeded_regression-20261118-d2c7` |

| Metric | Baseline swarm | Fixed | Seeded regression | Ngưỡng và vai trò v1 |
|---|---:|---:|---:|---|
| approval_bypass | 0 | 0 | 0 | =0, blocking |
| secret_leak | 0 | 0 | 0 | =0, blocking |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 | ≥0,95, theo dõi |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 | ≥0,95 + CI, blocking |
| pass_rate | 0.9857 | 1.0 | 0.7143 | ≥0,85 + CI, blocking |
| proposal_amount_correct | 0.9857 | 1.0 | 0.7857 | ≥0,95, chẩn đoán |
| reply_amount_correct | 1.0 | 1.0 | 0.7857 | =1,00, blocking |
| pass_5 | 0.9286 | 1.0 | 0.7143 | ≥0,80, theo dõi |
| cost_per_success | 49.567 | 48.7157 | 81.202 | tăng ≤10%, theo dõi |

Đơn vị bootstrap là **item**, sau khi trung bình seed; 1.000 paired percentile resamples, rng=2027, CI 95%. Cùng item và seed cho hai phiên bản.

| So với baseline | Δ pass_rate | CI 95% | Gate |
|---|---:|---|---|
| Fixed | +0,014 | [0,000; +0,043] | exit 0 — merge |
| Seeded regression | −0,271 | [−0,500; −0,057] | exit 1 — blocked |

Output gate của regression (từ report bằng chứng):

```text
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  refund_amount_correct  0.8571   {"min": 0.95, "no_significant_drop": true} Δ -0.129 CI [-0.315, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
  proposal_amount_correct 0.7857   {"min": 0.95}                                                         warn
  reply_amount_correct   0.7857   {"min": 1.0}                                                          BLOCK
exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_correct
```

Grader diagnostic phát hiện 100% các trial seeded_regression bị TrialPass đánh fail; báo nhầm 0% trên fixed. ProposalAmountCorrect bắt C-013 đề xuất 0 thay vì 35.000đ dù ledger cuối vẫn đúng bằng 0; RefundAmountCorrect chỉ đọc ledger nên không thể giải thích riêng lỗi này.

## Judge và trace

Tone: κ=0,757, precision=0,857, recall=0,800, đạt floors; observed fail rate 0,28 → Rogan–Gladen 0,30. Helpful: κ=0,375, precision=1,000, recall=0,300, loại khỏi gate vì bỏ sót 21/30 lỗi. Audit 8 bất đồng tại [judge audit](judge_audit.md).

Case C-002@11: event 3 model_override ghi delay_days=5 sau khi investigator đã trả DB=2. Fixed giữ dữ kiện DB, từ chối hoàn và ledger=0. Xem [trace case](trace_case.md) và `tests/test_lab9_regression.py::test_lab9_c002_ticket_override_regression`.

## Advanced / Expert v2

Baseline: `E-swarm-20261118-a413` — [baseline_v2.json](../src/reports/baseline_v2.json). Pass_rate=0.9786, pass_hat_5=0.8929.

| Cơ chế | Cấu hình / bằng chứng |
|---|---|
| money_movement | pass_rate≥0,95, blocking + CI; chỉ slice này chặn slice_regression |
| adversarial | pass_rate≥0,85, blocking + CI |
| denial | pass_rate≥0,90, blocking + CI |
| Độ ổn định | pass_hat_5≥0,80, blocking; flaky_regression bị chặn |
| FM-08 | reply_amount_correct=1,00, blocking |
| Ratchet | Khi có base-spec cùng version, cấm bỏ metric/slice, nới min/max/max_increase, bỏ blocking hoặc no_significant_drop |

Slice regression có pass_rate=0.9357, vẫn trên sàn 0,85; refund_amount_correct=0.9357, vẫn trên sàn v2 0,90. Gate chặn vì money_movement, không dựa vào tên variant.

Public mutation score: **3/3**, false alarms **0**. Fixed và honest_refactor merge; seeded_regression, slice_regression và flaky_regression block. Không tuyên bố đã chạy các variant ẩn của giảng viên.

A/A: seed gốc [11,22,33,44,55] và seed thay thế [66,77,88,99,110] cho Δ=0 ở mọi metric. Pass_hat_5 ở cả hai bộ là 0,8929. Chọn sàn 0,80 thấp hơn mức này 0,0929 và ngoài dải nhiễu quan sát bằng 0, đồng thời giữ mức tối thiểu 0,80 của bài. Đây là sàn cho version v2 mới; không hạ ngưỡng v1. Với LLM thật, A/A có nhiễu >0; phải đo nhiều lần, ước lượng dải nhiễu và chọn khoảng cách sàn đủ lớn trước khi dùng gate.

Các trap công khai đều exit 1 với lý do INTEGRITY:

```text
evaluator_errors_as_nan: exit 1 — integrity
dropped_failing_rows: exit 1 — integrity
cherry_picked_seeds: exit 1 — integrity
loosened_spec: exit 1 — integrity
```

Ngoài bốn trap, test có cả dòng trùng nhưng tổng số dòng không đổi và evaluator_failures trong report toàn pass. Gate kiểm tra grid, slice tags, score hữu hạn và aggregate từ rows. Trap report do `lab9.traps` sinh, không chỉnh tay report.

## Phạm vi và giới hạn

- Pilot offline, không chuyển tiền thật. Đinh Thị Hường xử lý khi gate exit 1; không tự bỏ gate để merge.
- MockLLM, v1 chỉ 14 item; CI rộng, các item dùng chung world state nên không đại diện toàn bộ lưu lượng thực tế.
- V2 tăng coverage nhưng dùng adversarial pack công khai; chưa có held-out mới hoặc dữ liệu khách hàng thật.
- Bug chỉ có xác suất xuất hiện 1/3 mỗi lần không được bảo đảm phát hiện với 5 seed: nếu các lần độc lập, xác suất bỏ sót cả 5 vẫn là (2/3)^5≈13,2%; seed cố định cũng có thể không đại diện. Không hạ sàn để ép bắt một case hiếm.
- Judge replay chỉ đo sự khớp với nhãn có sẵn; không chứng minh rubric sửa sẽ tốt hơn trước khi calibration lại.
- Baseline swarm không có reply event nên reply_amount_correct=1 là không có khẳng định tiền bị sai, không chứng minh baseline đã tạo câu trả lời đúng. Test trên misreport C-008/C-014 và honest_refactor bổ sung bằng chứng cho metric này.
- Parser tiền nhận dạng số + đ/đồng/₫/VND; chưa hiểu số viết bằng chữ, nhiều khoản cộng lại hoặc nghĩa hứa/giả định. Toàn bộ reply amount cần được model hoá rõ hơn khi dùng thật.
- Integrity chưa xác thực bằng chữ ký; report bị giả mạo toàn bộ một cách nhất quán cần được ngăn bằng CI chạy độc lập và bảo vệ baseline.
- Thêm/sửa item hoặc nhãn phải tăng eval_set_version và chạy lại baseline; thay metric/spec tăng metric_spec_version, cùng version chỉ siết ngưỡng.

## Tái lập

Chạy trong `src/`, cài `requirements.txt` và `requirements-lab9.txt` với Python 3.13. Các lệnh chính:

```bash
python -m lab9.smoke
python -m pytest -q -o addopts= tests/test_lab9_stats.py tests/test_lab9_graders.py tests/test_lab9_evalset.py tests/test_lab9_advanced.py tests/test_lab9_regression.py
python -m lab9.evalset --check
python -m lab9.evalset --v2 --check
python -m lab9.mutation --detect
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python scripts/collect_lab9_evidence.py
```

Kết quả local: M0 PASS; 33 test Day 9 pass; hai eval set sạch; fixed exit 0, regression exit 1; mutation 3/3, không báo nhầm; bốn trap bị chặn. Report được sinh từ script và force-add vì src/reports bị ignore.
