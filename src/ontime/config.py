"""Frozen analytical decisions; monetary values are scenarios, not estimates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
DB = DATA / "ontime.duckdb"
SQL = ROOT / "sql"
OUTPUTS = ROOT / "outputs"
TABLES = OUTPUTS / "tables"
FIGURES = OUTPUTS / "figures"
SEED = 42
TRAIN_END = "2018-02-01"
VALIDATION_END = "2018-05-01"
# Validation is further split: tuning/calibration/policy are disjoint in time.
CALIBRATION_START = "2018-03-01"
POLICY_START = "2018-03-16"
POLICY_END = "2018-04-01"  # April is a label-maturation buffer before test.
PRIOR_WEIGHT = 20.0
# Cold start uses stated constants, never a full-sample (future) mean.
COLD_LATE_RATE = 0.08
COLD_HANDLING_DAYS = 3.0
SELLER_MIN_ORDERS = 100
# Prefer logistic when validation AP is within 0.01 of LightGBM.
SIMPLICITY_AP_TOLERANCE = 0.01
INTERVENTION_COST = 8.0  # BRL per flagged order, assumed expedited handoff fee.
PREVENTED_LATE_VALUE = 80.0  # BRL, assumed combined margin/retention proxy.
EFFECTIVENESS = 0.50  # Assumed fraction of would-be late orders saved.
COST_GRID = (4.0, 8.0, 12.0)
VALUE_GRID = (40.0, 80.0, 120.0)
EFFECTIVENESS_GRID = (0.25, 0.50, 0.75)
MIN_POLICY_FLAGGED = 100  # Prevent thresholds justified by a handful of cases.
THRESHOLDS = tuple(round(i / 200, 3) for i in range(201))


def ensure_dirs():
    for path in (DATA, RAW, TABLES, FIGURES, OUTPUTS / ".cache", ROOT / "docs"):
        path.mkdir(parents=True, exist_ok=True)
