import numpy as np
import pandas as pd
import pytest
from ontime import config as c
from ontime.features import haversine
from ontime.standardise import smr_interval, bh_adjust
from ontime.calibrate import ece, fit_isotonic, reliability
from ontime.costmodel import break_even_effectiveness, economic_value, threshold_sweep, choose_threshold


@pytest.mark.parametrize("coords,km", [
    ((-23.5505,-46.6333,-22.9068,-43.1729),360.75),
    ((0,0,0,1),111.195),((51.5074,-0.1278,48.8566,2.3522),343.56),
    ((0,0,0,0),0),((0,0,0,180),20015.114),
])
def test_haversine_known_pairs(coords, km):
    assert haversine(*coords) == pytest.approx(km, abs=0.7)


def test_smr_exact_toy():
    ratio, lower, upper = smr_interval(10,5)
    assert ratio == 2
    assert lower == pytest.approx(0.9590777, abs=1e-6)
    assert upper == pytest.approx(3.6780712, abs=1e-6)


def test_zero_observed_ci():
    ratio, lower, upper = smr_interval(0,10)
    assert ratio == lower == 0
    assert upper == pytest.approx(-np.log(0.025)/10)


def test_bh_correction_toy():
    assert bh_adjust([0.01,0.04,0.03,0.20]) == pytest.approx([0.04,0.053333333,0.053333333,0.20])


def test_isotonic_monotone():
    iso = fit_isotonic([0,1,0,1,1,0,1,1], np.linspace(0,1,8))
    assert (np.diff(iso.predict(np.linspace(-1,2,100))) >= 0).all()


def test_perfect_calibration_ece():
    y = np.tile(np.r_[np.zeros(8),np.ones(2)],10)
    assert ece(y,np.full(100,0.2)) < 1e-12


def test_reliability_bin_edges():
    table = reliability([0,1],[0,1])
    assert len(table) == 10 and table.orders.sum() == 2
    assert table.orders.iloc[0] == table.orders.iloc[-1] == 1


@pytest.mark.parametrize("cost,value,precision,expected", [(8,80,0.2,0.5),(10,100,0.1,1.0),(0,40,0.4,0.0)])
def test_analytic_break_even(cost,value,precision,expected):
    assert break_even_effectiveness(cost,value,precision) == pytest.approx(expected)


def test_no_precision_cannot_break_even():
    assert np.isinf(break_even_effectiveness(8,80,0))


def test_cost_zero_at_break_even():
    y,p=[1,0,0,0,0],[0.8]*5
    result=economic_value(y,p,0.5,8,80,0.5)
    assert result["net_per_order"] == 0


def test_unflagged_orders_have_no_cost():
    result=economic_value([1,0],[0.1,0.2],0.5,8,80,0.5)
    assert result["flagged"] == result["net_per_order"] == 0


def test_policy_selection_does_not_use_test_labels():
    sweep=threshold_sweep([1,0,1,0],[0.9,0.8,0.7,0.1],1,20,0.5)
    threshold=choose_threshold(sweep,min_flagged=2).threshold
    left=economic_value([1,1],[0.9,0.8],threshold,1,20,0.5)
    right=economic_value([0,0],[0.9,0.8],threshold,1,20,0.5)
    assert left["threshold"] == right["threshold"] and left["net_per_order"] != right["net_per_order"]


def test_grid_has_27_distinct_cells(metrics):
    grid=pd.read_csv(c.TABLES / "cost_sensitivity.csv")
    assert len(grid) == len(grid.drop_duplicates(["cost_brl","value_brl","effectiveness"])) == 27
    assert int(grid.net_positive.sum()) == metrics["cost_model"]["net_positive_cells"]


def test_day_allocation_is_conservative(con):
    table=con.table("stage_attribution").df()
    assert np.allclose(table.handling_late_days+table.linehaul_late_days,table.days_late)
    assert (table[["handling_late_days","linehaul_late_days"]] >= 0).all().all()


def test_review_denominator_is_reviewed_orders():
    table=pd.read_csv(c.TABLES / "review_summary.csv")
    assert np.allclose(table.low_review_rate,table.low_review_orders/table.reviewed_orders)
