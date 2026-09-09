"""Thin SQL runner. No embedded warehouse SQL or analysis-time network."""
import os
import duckdb
import pandas as pd
from . import config as c
from .dq import report


def build():
    c.ensure_dirs()
    original = os.getcwd()
    os.chdir(c.ROOT)
    try:
        with duckdb.connect(str(c.DB), config={"threads": 1}) as con:
            con.register("runtime_config", pd.DataFrame([{
                "prior_weight": c.PRIOR_WEIGHT, "cold_late_rate": c.COLD_LATE_RATE,
                "cold_handling_days": c.COLD_HANDLING_DAYS,
            }]))
            for name in ("00_staging.sql", "10_dq_checks.sql", "20_order_fact.sql",
                         "30_seller_history.sql", "40_route_history.sql"):
                print(f"SQL: {name}", flush=True)
                con.execute((c.SQL / name).read_text(encoding="utf-8"))
                if name == "10_dq_checks.sql":
                    report(con)
            for table in ("exclusions", "population_audit", "monthly_rates", "review_distribution"):
                con.table(table).df().to_csv(c.TABLES / f"{table}.csv", index=False)
    finally:
        os.chdir(original)


if __name__ == "__main__":
    build()
