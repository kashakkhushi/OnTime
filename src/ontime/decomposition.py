"""Allocate late-vs-promise days proportionally to stage benchmark excess.

This is an accounting convention, not proof of preventability or causal effect.
The allocation sums exactly to actual days_late for each order.
"""
from . import config as c


def decompose(con):
    con.execute((c.SQL / "60_decomposition.sql").read_text())
    tables = {}
    for name in ("decomposition", "review_summary", "stage_baselines"):
        tables[name] = con.table(name).df()
        tables[name].to_csv(c.TABLES / f"{name}.csv", index=False)
    far = tables["decomposition"].loc[tables["decomposition"].at_distance_band.isin(
        ["02_200_500", "03_500_1000", "04_1000_2000", "05_2000_plus"])]
    return {"linehaul_share_beyond_200km": float(far.linehaul_late_days.sum()/far.late_days.sum()),
            "total_late_days": float(tables["decomposition"].late_days.sum()),
            "fallback_orders": int(tables["decomposition"].fallback_orders.sum())}
