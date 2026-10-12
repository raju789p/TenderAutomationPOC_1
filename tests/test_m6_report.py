"""M6 report output must stay tied to machine-produced verifier metrics."""

import json

from poc.report import generate_accuracy_report, results_table
from poc.render_docx import ROOT


def test_accuracy_report_results_numbers_match_metrics() -> None:
    metrics = json.loads((ROOT / "data/output/metrics.json").read_text(encoding="utf-8"))
    report = generate_accuracy_report(metrics)
    expected_table = results_table(metrics)
    assert expected_table in report
    assert f"{metrics['overall']['ledger']['placed']} / {metrics['overall']['ledger']['regenerated']} / {metrics['overall']['ledger']['unplaced']}" in expected_table
    assert str(metrics["overall"]["defect_count"]) in expected_table
