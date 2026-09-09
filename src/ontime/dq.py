"""Quality findings are reported; eligibility policy is separately implemented."""
from .config import DATA


def report(connection):
    checks = connection.table("dq_results").order("check_name").df()
    assert len(checks) == 28 and checks.check_name.is_unique
    lines = ["# Data-quality report", "", "Counts refer to staging records, before filters.",
             "FAIL is a recorded data finding, not an ignored pipeline error.", "",
             "| Assertion | Violations | Result |", "|---|---:|---|"]
    for row in checks.itertuples(index=False):
        lines.append(f"| {row.check_name} | {row.violations:,} | {'PASS' if row.violations == 0 else 'FAIL'} |")
    lines += ["", "## Resolution policy", "",
              "Geolocation is many observations per zip, not a unique-zip dimension: median valid coordinates collapse it.",
              "Reviews are not keyed uniquely by review_id: choose latest answer per order with deterministic ties.",
              "Delivered/complete/monotone and valid item linkage filters are counted in outputs/tables/exclusions.csv.",
              "Missing/invalid weights and dimensions become null plus imputation indicators; missing categories and coordinates retain explicit unknown groups.",
              "Missing payments become unknown; payments never multiply order rows. Price/freight violations exclude affected orders.",
              "Duplicate item lines are removed before item aggregation; inconsistent duplicate keys would fail the uniqueness test."]
    (DATA / "dq_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checks
