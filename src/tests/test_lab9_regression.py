"""Trace-derived regression cases, authored by dihnhuonq130104."""
import copy
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


def context(trial, label):
    from pydantic_evals.evaluators import EvaluatorContext
    return EvaluatorContext(name="regression", inputs={}, metadata=None,
        expected_output=label, output=trial, duration=0.0, _span_tree=None,
        attributes={}, metrics={})


def test_lab9_c002_ticket_override_regression():
    from lab9.trace_case import investigate
    from lab9.graders import RefundAmountCorrect, DbFactKept
    for shape, expected in (("seeded_regression", False), ("fixed", True)):
        case = investigate(shape, "C-002", 11)
        ctx = context(case["trial"], case["label"])
        assert RefundAmountCorrect().evaluate(ctx).value is expected
        assert DbFactKept().evaluate(ctx).value is expected
        assert case["trial"]["lab8_pass"] is expected


@pytest.mark.parametrize("claim", ["C-008", "C-014"])
def test_lab9_reply_amount_matches_committed_effect(claim):
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape
    from lab9.trace_case import investigate
    from lab9.graders import ReplyAmountCorrect
    SHAPES["test_misreport"] = make_shape("test_misreport", {"no_override", "misreport"})
    for shape, expected in (("test_misreport", False), ("fixed", True)):
        case = investigate(shape, claim, 11)
        assert ReplyAmountCorrect().evaluate(context(case["trial"], case["label"])).value is expected


def test_lab9_honest_paraphrase_keeps_amount():
    from lab9.trace_case import investigate
    from lab9.graders import ReplyAmountCorrect
    case = investigate("honest_refactor", "C-008", 11)
    assert ReplyAmountCorrect().evaluate(context(case["trial"], case["label"])).value is True


def test_lab9_integrity_duplicate_and_green_evaluator_failure():
    from lab9.gate import integrity_check
    spec = {"metrics": [{"id": "pass_rate"}]}
    rows = [{"item_id": "E-001", "seed": s, "pass_rate": True} for s in (11, 22)]
    base = {"manifest": {"items": 1, "seeds": [11, 22]}, "rows": rows,
            "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}
    assert integrity_check(base, base, spec) == []
    bad = copy.deepcopy(base)
    bad["rows"][1] = copy.deepcopy(bad["rows"][0])
    assert integrity_check(bad, base, spec)
    bad = copy.deepcopy(base)
    bad["evaluator_failures"] = ["grader crashed despite green scores"]
    assert integrity_check(bad, base, spec)


def test_lab9_pre_deducted_to_zero_has_diagnostic():
    from lab9.trace_case import investigate
    from lab9.graders import ProposalAmountCorrect
    for shape, expected in (("seeded_regression", False), ("fixed", True)):
        case = investigate(shape, "C-013", 11)
        assert ProposalAmountCorrect().evaluate(context(case["trial"], case["label"])).value is expected
