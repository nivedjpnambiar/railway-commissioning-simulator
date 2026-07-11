from railway_commissioning.commissioning import run_commissioning_suite
from railway_commissioning.reporting import results_to_csv, results_to_html


def test_commissioning_suite_passes() -> None:
    results = run_commissioning_suite()
    assert len(results) >= 8
    assert all(result.passed for result in results)


def test_reports_contain_results() -> None:
    results = run_commissioning_suite()
    csv_report = results_to_csv(results)
    html_report = results_to_html(results)
    assert "TC-001" in csv_report
    assert "Overall result" in html_report
    assert "PASS" in html_report
