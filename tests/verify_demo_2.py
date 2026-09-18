"""Check a downloaded Demo 2 result without executing the agent's Python file."""

import argparse
import ast
import json
from pathlib import Path

EXPECTED = {
    "revenue_2024_millions": 391035,
    "revenue_2025_millions": 416161,
    "increase_millions": 25126,
    "growth_percent": 6.43,
    "largest_increase_category": "Services",
    "largest_increase_millions": 12989,
}
SOURCE = "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"


def verify_result(directory):
    files = {}
    for name in ("metrics.json", "report.md", "analysis.py"):
        path = directory / name
        if not 0 < path.stat().st_size <= 64_000:
            raise ValueError(f"Unexpected output size: {name}")
        files[name] = path.read_text(encoding="utf-8")
    metrics = json.loads(files["metrics.json"])
    if metrics != EXPECTED:
        raise ValueError(f"Incorrect metrics: {metrics}")
    for key, expected in EXPECTED.items():
        if type(metrics[key]) is not type(expected):
            raise ValueError(f"Unexpected type for {key}")
    report = files["report.md"]
    for heading in ("## Revenue comparison", "## Largest increase", "## Source"):
        if heading not in report:
            raise ValueError(f"Missing report heading: {heading}")
    if SOURCE not in report or "23" not in report:
        raise ValueError("Missing filing URL or printed page number")
    if len(report.split()) > 250:
        raise ValueError("Report exceeds 250 words")
    if "Services" not in report or "6.43" not in report:
        raise ValueError("Report does not contain the expected category and growth")
    ast.parse(files["analysis.py"])
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_result(args.output_directory), indent=2))
    print("PASS: calculation, report structure, source, and Python syntax")
