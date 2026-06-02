"""Compare two local RateCon gold evaluation summaries."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    SYSTEM_SHADOW,
    write_json,
)


DEFAULT_BASELINE = (
    Path(".local_outputs")
    / "private_ratecon_gold_eval_baseline"
    / "ratecon_gold_evaluation_summary.json"
)
DEFAULT_EXPERIMENT = (
    Path(".local_outputs")
    / "private_ratecon_gold_eval_gold_diagnostic_v1"
    / "ratecon_gold_evaluation_summary.json"
)
DEFAULT_OUTPUT_DIR = Path(".local_outputs") / "private_ratecon_gold_eval_comparison"


def _load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_local_output_dir(output_dir, allow_custom_output_dir=False):
    path = Path(output_dir)
    if not allow_custom_output_dir and (not path.parts or path.parts[0] != ".local_outputs"):
        raise ValueError("comparison output must be under .local_outputs unless --allow-custom-output-dir is used")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _metric(summary, field_name):
    return (
        (summary.get("field_metrics", {}) or {})
        .get(SYSTEM_SHADOW, {})
        .get(field_name, {})
        or {}
    )


def _field_delta(baseline, experiment, field_name):
    base = _metric(baseline, field_name)
    exp = _metric(experiment, field_name)
    keys = [
        "exact_match_count",
        "normalized_match_count",
        "missing_count",
        "wrong_value_count",
        "precision",
        "recall",
        "high_confidence_but_wrong_count",
    ]
    payload = {
        "baseline": {key: base.get(key, 0) for key in keys},
        "experiment": {key: exp.get(key, 0) for key in keys},
        "delta": {},
    }
    for key in keys:
        payload["delta"][key] = round(float(exp.get(key, 0)) - float(base.get(key, 0)), 4)
    payload["baseline"]["correct_count"] = base.get("exact_match_count", 0) + base.get("normalized_match_count", 0)
    payload["experiment"]["correct_count"] = exp.get("exact_match_count", 0) + exp.get("normalized_match_count", 0)
    payload["delta"]["correct_count"] = (
        payload["experiment"]["correct_count"] - payload["baseline"]["correct_count"]
    )
    return payload


def _analysis_delta(baseline, experiment, key):
    base = baseline.get(key, {}) or {}
    exp = experiment.get(key, {}) or {}
    count_keys = [
        "wrong_selected_count",
        "missing_count",
        "gold_in_candidates_not_selected",
        "gold_not_in_candidates",
        "gold_total_in_candidates_not_selected",
        "gold_total_not_in_candidates",
    ]
    payload = {"baseline": base, "experiment": exp, "delta": {}}
    for count_key in count_keys:
        if count_key in base or count_key in exp:
            payload["delta"][count_key] = int(exp.get(count_key, 0)) - int(base.get(count_key, 0))
    return payload


def _recall_summary_delta(baseline, experiment):
    base = baseline.get("load_candidate_recall_summary", {}) or {}
    exp = experiment.get("load_candidate_recall_summary", {}) or {}
    keys = [
        "evaluated_docs",
        "gold_load_in_any_candidate",
        "gold_load_in_independent_candidate",
        "gold_load_in_layout_candidate",
        "gold_load_in_header_candidate",
        "gold_load_in_table_candidate",
        "gold_load_in_legacy_fallback_candidate",
        "gold_load_not_in_candidates",
        "gold_load_visible_in_text_but_not_candidate",
        "gold_load_visible_in_layout_but_not_candidate",
        "gold_load_requires_ocr_or_vision",
    ]
    return {
        "baseline": {key: base.get(key, 0) for key in keys},
        "experiment": {key: exp.get(key, 0) for key in keys},
        "delta": {key: int(exp.get(key, 0)) - int(base.get(key, 0)) for key in keys},
        "baseline_missing_reasons": base.get("candidate_missing_reason_counts", {}) or {},
        "experiment_missing_reasons": exp.get("candidate_missing_reason_counts", {}) or {},
    }


def _rate_profile_safety_summary(baseline, experiment):
    rate_delta = _field_delta(baseline, experiment, FIELD_TOTAL_CARRIER_RATE).get("delta", {})
    error_delta = _analysis_delta(baseline, experiment, "rate_error_analysis").get("delta", {})
    return {
        "correct_delta": rate_delta.get("correct_count", 0),
        "wrong_delta": rate_delta.get("wrong_value_count", 0),
        "missing_delta": rate_delta.get("missing_count", 0),
        "high_confidence_wrong_delta": rate_delta.get("high_confidence_but_wrong_count", 0),
        "gold_total_in_candidates_not_selected_delta": error_delta.get(
            "gold_total_in_candidates_not_selected",
            0,
        ),
        "wrong_money_context_delta": error_delta.get("wrong_selected_count", 0),
    }


def _stop_serialization(summary, field_name):
    metric = _metric(summary, field_name)
    return {
        "field_not_serialized_count": metric.get("field_not_serialized_count", 0),
        "partial_match_count": metric.get("partial_match_count", 0),
        "wrong_value_count": metric.get("wrong_value_count", 0),
        "missing_count": metric.get("missing_count", 0),
    }


def compare_summaries(baseline, experiment):
    return {
        "schema_version": "ratecon_gold_evaluation_comparison_v1",
        "labels_evaluated": {
            "baseline": baseline.get("labels_evaluated", 0),
            "experiment": experiment.get("labels_evaluated", 0),
        },
        "shadow_field_deltas": {
            FIELD_LOAD_NUMBER: _field_delta(baseline, experiment, FIELD_LOAD_NUMBER),
            FIELD_TOTAL_CARRIER_RATE: _field_delta(baseline, experiment, FIELD_TOTAL_CARRIER_RATE),
        },
        "stop_component_comparability": {
            "pickup_stops": {
                "baseline": _stop_serialization(baseline, "pickup_stops"),
                "experiment": _stop_serialization(experiment, "pickup_stops"),
            },
            "delivery_stops": {
                "baseline": _stop_serialization(baseline, "delivery_stops"),
                "experiment": _stop_serialization(experiment, "delivery_stops"),
            },
        },
        "load_number_error_analysis_delta": _analysis_delta(
            baseline,
            experiment,
            "load_number_error_analysis",
        ),
        "rate_error_analysis_delta": _analysis_delta(
            baseline,
            experiment,
            "rate_error_analysis",
        ),
        "load_candidate_recall_delta": _recall_summary_delta(baseline, experiment),
        "rate_profile_safety_summary": _rate_profile_safety_summary(baseline, experiment),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _markdown_report(comparison):
    lines = [
        "# RateCon Gold Evaluation Comparison",
        "",
        f"labels_evaluated: {json.dumps(comparison.get('labels_evaluated', {}), sort_keys=True)}",
        "",
        "## Shadow Field Deltas",
        "",
    ]
    for field_name, payload in (comparison.get("shadow_field_deltas", {}) or {}).items():
        lines.append(f"{field_name}: {json.dumps(payload, sort_keys=True)}")
    lines.extend(["", "## Stop Comparability", ""])
    lines.append(json.dumps(comparison.get("stop_component_comparability", {}) or {}, sort_keys=True))
    lines.extend(["", "## Error Analysis Deltas", ""])
    lines.append(
        "load_number: "
        + json.dumps(comparison.get("load_number_error_analysis_delta", {}) or {}, sort_keys=True)
    )
    lines.append(
        "total_carrier_rate: "
        + json.dumps(comparison.get("rate_error_analysis_delta", {}) or {}, sort_keys=True)
    )
    lines.extend(["", "## Load Candidate Recall Delta", ""])
    lines.append(json.dumps(comparison.get("load_candidate_recall_delta", {}) or {}, sort_keys=True))
    lines.extend(["", "## Rate Profile Safety", ""])
    lines.append(json.dumps(comparison.get("rate_profile_safety_summary", {}) or {}, sort_keys=True))
    return "\n".join(lines) + "\n"


def build_parser():
    parser = argparse.ArgumentParser(description="Compare local RateCon gold evaluation summaries.")
    parser.add_argument("--baseline-summary", default=str(DEFAULT_BASELINE))
    parser.add_argument("--experiment-summary", default=str(DEFAULT_EXPERIMENT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    baseline = _load_json(args.baseline_summary)
    experiment = _load_json(args.experiment_summary)
    output_dir = _normalize_local_output_dir(
        args.output_dir,
        allow_custom_output_dir=args.allow_custom_output_dir,
    )
    comparison = compare_summaries(baseline, experiment)
    summary_path = output_dir / "ratecon_gold_evaluation_comparison_summary.json"
    report_path = output_dir / "ratecon_gold_evaluation_comparison_report.md"
    write_json(summary_path, comparison)
    report_path.write_text(_markdown_report(comparison), encoding="utf-8")
    print(
        "ratecon_gold_evaluation_comparison_written: "
        + json.dumps(
            {
                "summary": summary_path.name,
                "report": report_path.name,
                "private_values_printed": False,
                "raw_text_printed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
