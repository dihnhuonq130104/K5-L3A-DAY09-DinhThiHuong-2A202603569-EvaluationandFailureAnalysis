"""Reproduce trace, calibration, detection and gate evidence. Author: dihnhuonq130104.

Run from src: python scripts/collect_lab9_evidence.py
Reports are generated from executed trials, never edited manually.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab8.shapes import SHAPES
from lab9 import gate
from lab9.eval import load_spec, run_eval
from lab9.judge import calibrate
from lab9.mutation import detect
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape


def main():
    cases = [
        ("leaky_trace", "C-001", {"leaky_trace"}),
        ("ignore_denied", "C-007", {"no_override", "ignore_denied"}),
        ("ticket_trust", "C-002", {"ticket_trust"}),
        ("sum_parts", "C-014", {"no_override", "sum_parts"}),
        ("pre_deducted", "C-014", {"no_override", "pre_deducted"}),
        ("stale_clause", "C-006", {"no_override", "stale_clause"}),
        ("sibling_refund", "C-001", {"no_override", "sibling_refund"}),
        ("misreport", "C-008", {"no_override", "misreport"}),
        ("cross_principal", "C-005", {"no_override"}),
    ]
    traces = {}
    for name, claim, bugs in cases:
        shape = "evidence_" + name
        SHAPES[shape] = make_shape(shape, bugs)
        case = investigate(shape, claim, 11)
        trial = case["trial"]
        traces[name] = {"claim": claim, "seed": 11, "bugs": sorted(bugs),
            "events": trial["events"], "snapshot": trial["snapshot"],
            "unexpected_rows": trial["unexpected_rows"], "result": trial["result"],
            "lab8_pass": trial["lab8_pass"], "lab8_reason": trial["lab8_reason"],
            "label": case["label"]}
    for shape in ("seeded_regression", "fixed"):
        case = investigate(shape, "C-002", 11)
        traces[shape] = {"claim": "C-002", "seed": 11, **case}
    spec = load_spec()
    baseline = json.loads(Path("reports/baseline_v1.json").read_text(encoding="utf-8"))
    decisions = {}
    for shape in ("fixed", "seeded_regression"):
        rep = json.loads(Path(f"reports/eval_{shape}.json").read_text(encoding="utf-8"))
        blocked, lines = gate.check(rep, baseline, spec)
        decisions[shape] = {"exit": int(bool(blocked)), "blocked": blocked, "lines": lines}
    detection, false_alarm = detect(spec)
    evidence = {"author": "dihnhuonq130104", "day8_commit": "034c6c421c198dae67a9211d15e2587d5a378972",
        "judges": {name: calibrate(Path(f"data/eval/judge_{name}_public.csv")) for name in ("tone", "helpful")},
        "detection": detection, "false_alarm": false_alarm, "gates": decisions, "traces": traces}
    if Path("reports/baseline_v2.json").exists():
        v2 = load_spec(Path("config/metric_spec_v2.yaml"))
        base_v2 = json.loads(Path("reports/baseline_v2.json").read_text(encoding="utf-8"))
        aa = run_eval("swarm", v2, [66, 77, 88, 99, 110])
        Path("reports/eval_swarm_aa_v2.json").write_text(json.dumps(aa, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence["aa_v2"] = {"base_seeds": base_v2["manifest"]["seeds"], "alternate_seeds": aa["manifest"]["seeds"],
            "deltas": {k: aa["metrics"][k] - value for k, value in base_v2["metrics"].items()
                       if isinstance(value, (int, float)) and isinstance(aa["metrics"].get(k), (int, float))}}
    Path("reports/submission_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote reports/submission_evidence.json")


if __name__ == "__main__":
    main()
