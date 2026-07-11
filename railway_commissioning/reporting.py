from __future__ import annotations

import csv
import html
import io
from datetime import datetime, timezone

from .models import TestResult


def results_to_csv(results: list[TestResult]) -> str:
    buffer = io.StringIO()
    fieldnames = ["Test ID", "Requirement", "Expected", "Measured", "Result", "Notes"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(result.to_dict() for result in results)
    return buffer.getvalue()


def results_to_html(results: list[TestResult], project_version: str = "1.0.0") -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    passed = sum(result.passed for result in results)
    overall = "PASS" if passed == len(results) else "FAIL"

    rows = []
    for result in results:
        values = result.to_dict()
        rows.append(
            "<tr>"
            + "".join(f"<td>{html.escape(str(values[key]))}</td>" for key in values)
            + "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Virtual Commissioning Test Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }}
h1, h2 {{ margin-bottom: 0.4rem; }}
.summary {{ padding: 1rem; border: 1px solid #d1d5db; margin: 1rem 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; vertical-align: top; }}
th {{ background: #f3f4f6; }}
</style>
</head>
<body>
<h1>Virtual Railway Door Commissioning Report</h1>
<p>Generated: {generated}</p>
<div class="summary">
<strong>Project version:</strong> {html.escape(project_version)}<br>
<strong>Passed tests:</strong> {passed}/{len(results)}<br>
<strong>Overall result:</strong> {overall}
</div>
<table>
<thead><tr>{''.join(f'<th>{key}</th>' for key in results[0].to_dict())}</tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body>
</html>"""
