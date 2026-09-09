"""Exactly eight publication-ready matplotlib figures, rebuilt from CSVs only."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, StrMethodFormatter
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd
from . import config as c

BLUE, ORANGE, GREEN, RED, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#6A7582"
BANDS = {"00_unknown": "Unknown", "01_0_200": "0–200", "02_200_500": "200–500", "03_500_1000": "500–1,000",
         "04_1000_2000": "1,000–2,000", "05_2000_plus": "2,000+"}


def read(name):
    return pd.read_csv(c.TABLES / f"{name}.csv")


def finish(fig, number, slug, caption):
    path = c.FIGURES / f"fig{number:02d}_{slug}.png"
    fig.savefig(path, dpi=150, facecolor="white", bbox_inches="tight", metadata={"Software": "OnTime / matplotlib"})
    path.with_suffix(".caption.txt").write_text(caption.strip()+"\n", encoding="utf-8")
    plt.close(fig)


def figures():
    c.ensure_dirs()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.titlesize": 19,
                         "axes.labelsize": 14, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titlepad": 18, "axes.labelpad": 10, "legend.frameon": False,
                         "xtick.labelsize": 12, "ytick.labelsize": 12, "figure.constrained_layout.use": True})
    metrics = json.loads((c.OUTPUTS / "metrics.json").read_text())

    monthly = read("monthly_rates")
    monthly["month"] = pd.to_datetime(monthly.month)
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.plot(monthly.month, monthly.late_rate, "o-", color=BLUE, lw=2.8, ms=6)
    for date, label in ((c.TRAIN_END, "Validation begins"), (c.VALIDATION_END, "Test begins")):
        ax.axvline(pd.Timestamp(date), color=GREY, ls="--", lw=1.5)
        ax.text(pd.Timestamp(date), ax.get_ylim()[1]*0.94, label, rotation=90, va="top", ha="right", color=GREY)
    ax.set(title="Delivery risk changes substantially over time", xlabel="Purchase month", ylabel="Orders delivered after promise (%)")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", alpha=0.18)
    finish(fig, 1, "late_rate_over_time", "Monthly rates use the eligible delivered population; dashed lines mark the frozen chronological cutoffs. Sparse early months are retained.")

    states = read("smr_state").sort_values("smr")
    fig, ax = plt.subplots(figsize=(10.5, 11))
    positions = np.arange(len(states))
    colors = [RED if s == "RJ" else BLUE for s in states.segment]
    for i, row in enumerate(states.itertuples()):
        ax.errorbar(row.smr, i, xerr=[[row.smr-row.ci_lower], [row.ci_upper-row.smr]], fmt="o", color=colors[i], capsize=3, ms=6)
    ax.set_yticks(positions, states.segment)
    ax.axvline(1, color=GREY, ls="--", lw=1.5)
    ax.set(title="Which states exceed their expected late orders?", xlabel="Observed / mix-expected late orders (SMR; 95% CI)", ylabel="Customer state")
    ax.grid(axis="x", alpha=0.15)
    ax.text(0.98, 0.02, "Adjusted for category, distance, freight,\nitem count and purchase month", transform=ax.transAxes, ha="right", va="bottom", fontsize=11, color=GREY)
    finish(fig, 2, "state_smr", "Cross-fitted mix-only expectations; exact Poisson intervals condition on expected counts and are pointwise, without model-estimation or clustering uncertainty. Rio de Janeiro is highlighted.")

    pareto = read("seller_pareto")
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    ax.plot(np.r_[0, pareto.seller_share], np.r_[0, pareto.cumulative_positive_excess_share], color=BLUE, lw=3)
    ax.plot([0, 1], [0, 1], color=GREY, ls="--", lw=1.2, label="Equal concentration")
    ax.set(title="Excess lateness is concentrated among sellers", xlabel="Cumulative share of sellers, ranked by excess (%)", ylabel="Cumulative share of positive excess late orders (%)", xlim=(0, 1), ylim=(0, 1.02))
    ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(alpha=0.15); ax.legend(loc="lower right")
    finish(fig, 3, "seller_pareto", "Sellers are ordered by observed minus expected late orders; only positive excess enters the cumulative numerator. Negative excess is not offset, and this curve differs from the FDR-screened action tail.")

    stage = read("decomposition")
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(stage))
    handling = stage.handling_late_days/stage.late_orders
    carrier = stage.linehaul_late_days/stage.late_orders
    ax.bar(x, handling, color=ORANGE, label="Seller handling")
    ax.bar(x, carrier, bottom=handling, color=BLUE, label="Carrier-stage transit")
    for i, row in enumerate(stage.itertuples()):
        ax.text(i, handling.iloc[i]+carrier.iloc[i]+0.12, f"{row.linehaul_share:.0%} transit", ha="center", fontsize=11)
    ax.set_xticks(x, [BANDS[b] for b in stage.at_distance_band])
    ax.set(title="Where late-vs-promise days accumulate", xlabel="Straight-line seller–customer distance (km)", ylabel="Allocated days late per late order (days)")
    ax.set_ylim(0, (handling+carrier).max()*1.23)
    ax.legend(loc="upper left", ncols=2); ax.grid(axis="y", alpha=0.15)
    finish(fig, 4, "day_decomposition", "Actual days late are allocated by positive stage-duration excess over distance-matched on-time medians; this is a descriptive accounting convention, not an identified causal or preventable share.")

    ladder = read("model_ladder")
    legit, leaky = ladder.iloc[:-1], ladder.iloc[-1]
    labels = ["Never-late floor", "Base-rate constant", "Distance logistic", "Full logistic", "L2 logistic", "LightGBM"]
    fig, (ax, control) = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [3.8, 1.35]})
    bars = ax.barh(np.arange(6), legit.pr_auc, color=[GREY, GREY, BLUE, BLUE, GREEN, BLUE], height=0.65)
    ax.set_yticks(np.arange(6), labels); ax.invert_yaxis()
    floor = float(ladder.pr_auc_floor.iloc[0])
    ax.axvline(floor, color=GREY, ls="--", label=f"Test base rate = {floor:.3f}")
    max_ap = legit.pr_auc.max()
    ax.set_xlim(0, max_ap*1.28)
    for bar, val in zip(bars, legit.pr_auc):
        ax.text(val+max_ap*0.02, bar.get_y()+bar.get_height()/2, f"{val:.3f}", va="center", fontsize=12)
    ax.set(title="Checkout-only performance", xlabel="Test average precision (PR-AUC)", ylabel="Model")
    ax.legend(loc="lower right", fontsize=11); ax.grid(axis="x", alpha=0.15)
    control.bar([0], [leaky.pr_auc], color=RED, width=0.5)
    control.set(ylim=(0, 1.05), xticks=[0], xticklabels=["Leaky\nLightGBM"], ylabel="Test average precision", title="Negative control")
    control.text(0, leaky.pr_auc+0.025, f"{leaky.pr_auc:.3f}", ha="center", color=RED, weight="bold")
    control.text(0, 0.35, "USES FUTURE\nDELIVERY\nINFORMATION", ha="center", color="white", weight="bold", fontsize=12)
    finish(fig, 5, "model_ladder", "Average precision is the step-weighted PR area. All models share the test cohort; the separated negative control uses future stage durations and review scores. Panel scales differ, and the control cannot be deployed.")

    fig, ax = plt.subplots(figsize=(9, 7))
    max_value = 0.0
    for name, color, label, marker in (("uncalibrated", BLUE, "Uncalibrated", "o"), ("isotonic", ORANGE, "Isotonic", "s")):
        rel = read("reliability_"+name).dropna()
        ax.plot(rel.mean_prediction, rel.observed_rate, marker=marker, color=color, lw=2, label=label)
        max_value = max(max_value, rel.mean_prediction.max(), rel.observed_rate.max())
    limit = min(1.0, max(0.4, max_value*1.08))
    ax.plot([0, limit], [0, limit], color=GREY, ls="--", label="Perfect calibration")
    ax.set(title="Calibration must survive the next time period", xlabel="Mean predicted late probability", ylabel="Observed late fraction", xlim=(0, limit), ylim=(0, limit))
    ax.legend(loc="upper left"); ax.grid(alpha=0.15)
    finish(fig, 6, "reliability", "Test reliability in ten equal-width probability bins; empty bins are omitted and counts are in companion CSVs. Isotonic regression was fitted on a disjoint validation period; improvement is not guaranteed under drift.")

    reviews = read("review_distribution")
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    x = np.arange(5)
    for late, color, label, shift in ((0, BLUE, "On time", -0.2), (1, ORANGE, "Late", 0.2)):
        part = reviews.loc[(reviews.is_late == late) & (reviews.review_score > 0)].set_index("review_score").reindex(range(1, 6), fill_value=0)
        shares = part.orders/part.orders.sum()
        ax.bar(x+shift, shares, width=0.38, color=color, label=label)
    ax.set_xticks(x, ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"])
    ax.set(title="Late deliveries are associated with poorer reviews", xlabel="Latest review score per order", ylabel="Share of reviewed orders (%)")
    ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.legend(); ax.grid(axis="y", alpha=0.15)
    finish(fig, 7, "review_scores", "Each group is normalised over orders with a recorded review; missing-review counts are reported separately. Association does not identify retention loss or a monetary value for preventing lateness.")

    grid = read("cost_sensitivity")
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
    extent = max(abs(grid.net_per_order.min()), abs(grid.net_per_order.max()), 0.01)
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    precision = metrics["cost_model"]["precision"]
    for ax, eff in zip(axes, c.EFFECTIVENESS_GRID):
        part = grid.loc[grid.effectiveness == eff].pivot(index="cost_brl", columns="value_brl", values="net_per_order")
        enabled = grid.loc[grid.effectiveness == eff].pivot(index="cost_brl", columns="value_brl", values="validation_enabled")
        mesh = ax.imshow(part.values, cmap="PuOr", norm=norm, origin="lower", aspect="auto", extent=(-0.5, 2.5, -0.5, 2.5))
        for i in range(3):
            for j in range(3):
                v = part.iloc[i, j]
                text = f"{v:+.3f}" if enabled.iloc[i, j] else "OFF\n0.000"
                ax.text(j, i, text, ha="center", va="center", fontsize=12, color="white" if abs(v)>extent*0.55 else "#20252B")
        xx, yy = np.meshgrid(np.linspace(0, 2, 80), np.linspace(0, 2, 80))
        value = c.VALUE_GRID[0]+xx*(c.VALUE_GRID[-1]-c.VALUE_GRID[0])/2
        cost = c.COST_GRID[0]+yy*(c.COST_GRID[-1]-c.COST_GRID[0])/2
        surface = eff*value*precision-cost
        if surface.min() < 0 < surface.max():
            ax.contour(xx, yy, surface, levels=[0], colors=["#222222"], linestyles="--", linewidths=1.7)
        ax.set_xticks(range(3), [f"R${v:.0f}" for v in c.VALUE_GRID])
        ax.set_yticks(range(3), [f"R${v:.0f}" for v in c.COST_GRID])
        ax.set(title=f"Effectiveness: {eff:.0%}", xlabel="Value of preventing a late order")
    axes[0].set_ylabel("Cost per flagged order")
    fig.colorbar(mesh, ax=axes, label="Test expected net value (BRL per incoming order)", shrink=0.74)
    fig.suptitle("Economic value is sensitive to unmeasured assumptions", fontsize=20)
    finish(fig, 8, "cost_sensitivity", "Each cell selects its threshold on validation; OFF means validation chose no intervention. Dashed contours show break-even at the base candidate's fixed test precision, a reference distinct from cell-specific policies. Values assume effectiveness, not observed intervention effects.")
    print("Rendered eight figures and eight captions.")


if __name__ == "__main__":
    figures()
