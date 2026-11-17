"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    import math
    from lab9.graders import GRADERS
    problems = []
    for title, rep in (("PR", pr), ("baseline", base)):
        manifest = rep.get("manifest", {})
        rows = rep.get("rows", [])
        seeds = manifest.get("seeds", [])
        if not seeds or len(set(seeds)) != len(seeds):
            problems.append(f"{title}: invalid seed manifest")
        if len(rows) != manifest.get("items", 0) * len(seeds):
            problems.append(f"{title}: row count differs from manifest")
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if len(set(pairs)) != len(pairs):
            problems.append(f"{title}: duplicate item/seed")
        item_ids = {r.get("item_id") for r in rows}
        if len(item_ids) != manifest.get("items") or set(pairs) != {(i, seed) for i in item_ids for seed in seeds}:
            problems.append(f"{title}: incomplete item/seed grid")
        if rep.get("evaluator_failures"):
            problems.append(f"{title}: evaluator failures")
        for mid, value in rep.get("metrics", {}).items():
            if isinstance(value, (int, float)) and not math.isfinite(value):
                problems.append(f"{title}: nonfinite metric {mid}")
        for m in spec["metrics"]:
            mid = m["id"]
            value = rep.get("metrics", {}).get(mid)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{title}: invalid metric {mid}")
            if mid in GRADERS:
                for row in rows:
                    v = row.get(mid)
                    if not isinstance(v, (int, float)) or not math.isfinite(v):
                        problems.append(f"{title}: missing/nonfinite row score {mid}")
                        break
        for row in rows:
            for value in row.values():
                if isinstance(value, float) and not math.isfinite(value):
                    problems.append(f"{title}: nonfinite row value")
        if rows and not problems and all("cost" in row for row in rows):
            from lab9.eval import aggregate
            graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
            recalculated = aggregate(rows, graded, k_values=spec.get("pass_k", []))
            for mid, expected in recalculated.items():
                reported = rep.get("metrics", {}).get(mid)
                if expected != reported:
                    problems.append(f"{title}: aggregate {mid} differs from rows")
        # Slice membership must also be consistent across seeds within a report.
        tags = {}
        for row in rows:
            key, value = row.get("item_id"), frozenset(row.get("slices") or [])
            if key in tags and tags[key] != value:
                problems.append(f"{title}: inconsistent slice membership")
            tags[key] = value
    pr_pairs = {(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])}
    base_pairs = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if pr_pairs != base_pairs or pr["manifest"].get("seeds") != base["manifest"].get("seeds"):
        problems.append("item/seed grid differs from baseline")
    base_tags = {r.get("item_id"): frozenset(r.get("slices") or []) for r in base.get("rows", [])}
    if any(frozenset(r.get("slices") or []) != base_tags.get(r.get("item_id")) for r in pr.get("rows", [])):
        problems.append("slice tags differ from baseline")
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def ratchet(old_entries, new_entries, key, nested):
            new_map = {key(m): m for m in new_entries}
            for old in old_entries:
                name = key(old)
                new = new_map.get(name)
                if new is None:
                    problems.append(f"ratchet: removed {name}")
                    continue
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: nonblocking {name}")
                before = old.get("threshold", {}) if nested else old
                after = new.get("threshold", {}) if nested else new
                for field in ("min", "max", "max_increase"):
                    if field in before and (field not in after or
                        (after[field] < before[field] if field == "min" else after[field] > before[field])):
                        problems.append(f"ratchet: loosened {name}/{field}")
                if before.get("no_significant_drop") and not after.get("no_significant_drop"):
                    problems.append(f"ratchet: removed CI protection {name}")
        ratchet(base_spec.get("metrics", []), spec.get("metrics", []), lambda m: m["id"], True)
        ratchet(base_spec.get("slices", []), spec.get("slices", []), lambda m: (m["name"], m["metric"]), False)
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        mid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        keys = sorted(set(a) & set(b))
        value = sum(a.values()) / len(a) if a else None
        failed = value is None or ("min" in entry and value < entry["min"])
        note = ""
        if entry.get("no_significant_drop") and keys:
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                confidence=bs.get("confidence", 0.95))
            failed |= hi < 0
            note = f"delta {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        if failed and entry.get("blocking"):
            blocked.append(mid)
        lines.append(f"  {mid} {value} {note} {'BLOCK' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
