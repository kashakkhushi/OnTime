"""Generate the director memo and recruiter README from computed results only.

The memo's numeric display ledger preserves every displayed value and its source.
"""
import json
import re
import pandas as pd
from . import config as c


def markdown_table(frame, columns, formats=None):
    formats = formats or {}
    lines = ["| " + " | ".join(columns.values()) + " |", "|" + "|".join(["---"]*len(columns)) + "|"]
    for _, row in frame.iterrows():
        cells = [format(row[key], formats[key]) if key in formats else str(row[key]) for key in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate():
    m = json.loads((c.OUTPUTS / "metrics.json").read_text())
    table = lambda name: pd.read_csv(c.TABLES / f"{name}.csv")
    ex, reviews, stages = table("exclusions"), table("review_summary"), table("decomposition")
    states, ladder = table("smr_state"), table("model_ladder")
    p, rio, tail, costs = m["population"], m["rio"], m["seller_tail"], m["cost_model"]
    raw, calibrated = m["calibration"]
    champion = m["champion"].replace("_", " ")
    late_reviews, ontime_reviews = [reviews.loc[reviews.is_late == x].iloc[0] for x in (1,0)]
    ledger = []

    def n(key, value, fmt=",.0f", source="outputs/metrics.json"):
        display = format(value, fmt)
        for token in re.findall(r"(?<![A-Za-z_])\d[\d,.]*(?:%|)?", display):
            ledger.append({"key": key, "value": value, "display": token, "source": source})
        return display

    positive = costs["validation_enabled"] and costs["net_per_order"] > 0
    recommendation = ("Run a controlled intervention pilot before considering a broad model rollout."
                      if positive else "Do not deploy the checkout model as a paid-intervention trigger under the base assumptions.")
    economic_clause = ("The retrospective base scenario is positive, but its assumed effectiveness and customer value remain unmeasured."
                       if positive else "The validation-selected candidate loses money on the held-out test period, so no intervention is the better base-case policy.")
    calibration_direction = "improved" if calibrated["ece_10_bins"] < raw["ece_10_bins"] else "worsened"
    best = states.iloc[0]
    memo = f"""# OnTime — Decision memo

{recommendation} Prioritise investigation of the adjusted seller tail and Rio de Janeiro routes, with stage-specific operational audits. {economic_clause}

## What is actually broken

The clearest operational signal is uneven delivery performance after accounting for the work being shipped. Rio de Janeiro has a standardised mortality ratio, used here as a standardised lateness ratio, of {n('rio_smr',rio['smr'],'.2f')}, with a {n('confidence',m['assumptions']['smr_confidence'],'.0%')} interval from {n('rio_lower',rio['ci_lower'],'.2f')} to {n('rio_upper',rio['ci_upper'],'.2f')}. This corresponds to {n('rio_excess',rio['excess_late_orders'])} more late orders than the mix model expects. The comparison accounts for category, distance band, freight class, item count and purchase month. It is a better starting point than ranking raw late rates, which partly ranks the difficulty of each state's shipment mix.

Rio is not automatically the highest-ratio state. {best.segment} leads this particular specification with a ratio of {n('highest_state_smr',best.smr,'.2f','outputs/tables/smr_state.csv')} and an interval from {n('highest_state_lower',best.ci_lower,'.2f','outputs/tables/smr_state.csv')} to {n('highest_state_upper',best.ci_upper,'.2f','outputs/tables/smr_state.csv')}. Priorities should combine excess order volume, uncertainty, operational ownership and the cost of changing service. A large ratio on a small base is not interchangeable with a large number of affected customers. The route table provides the next level of investigation; it does not identify a specific carrier.

The seller screen flags {n('tail_sellers',tail['sellers'])} sellers covering {n('tail_orders',tail['orders'])} orders, or {n('tail_share',tail['order_share'],'.1%')} of the eligible population. Their observed late rate is {n('tail_raw',tail['raw_late_rate'],'.1%')}, but the actionable comparison is their aggregate adjusted ratio of {n('tail_smr',tail['smr'],'.2f')} and {n('tail_excess',tail['excess_late_orders'])} excess late orders. Screening requires at least {n('seller_min',m['assumptions']['seller_min_orders'])} orders and an excess signal that survives the specified false-discovery procedure. This identifies an audit queue, not a list of sellers proved to have caused customer harm. Selection itself makes the tail's apparent strength optimistic for a new period.

Every order is attributed to its largest seller by merchandise value. We retain {n('multiseller',p['multiseller_orders'])} multi-seller orders rather than silently dropping them, but an order-level delivery timestamp cannot establish which seller's parcel caused its final arrival. Operational follow-up must resolve that attribution before assigning accountability. Likewise, comparisons remain sensitive to the mix variables available in this extract; service class, capacity and carrier routing are absent.

## Where the days are lost

Beyond {n('distance_boundary',200,'.0f','sql/20_order_fact.sql; outputs/tables/decomposition.csv')} kilometres, the carrier-stage allocation accounts for {n('far_linehaul',m['decomposition']['linehaul_share_beyond_200km'],'.1%')} of observed late-vs-promise days under the stated decomposition. The calculation compares each late order's handling and transit durations with on-time median durations in the same distance band, then allocates its actual late days in proportion to positive stage excess. This preserves the total number of observed late days rather than treating every day in transit as an avoidable delay.

The implication is to inspect dispatch-to-delivery processes on longer routes: consolidation, sorting, last-mile handoffs, promised service and exception recovery. On short routes, use the corresponding stage split to decide whether dispatch readiness deserves equal attention. Handling is measured from purchase to carrier handoff, so it includes approval time; it is not a pure warehouse productivity measure. The transit stage also bundles activities beyond long-distance transport. Neither stage's accounting share is an estimate of how much an intervention would save.

There is a commercial warning in the reviews. Among reviewed late orders, {n('late_low_reviews',late_reviews.low_review_rate,'.1%','outputs/tables/review_summary.csv')} receive the lowest two scores, compared with {n('ontime_low_reviews',ontime_reviews.low_review_rate,'.1%','outputs/tables/review_summary.csv')} among reviewed on-time orders. The analysis separately records {n('missing_reviews',p['missing_review_orders'])} missing reviews. Dissatisfied customers may respond differently, and product problems may affect both ratings and delivery experiences. These data support concern about customer experience; they do not supply a retention effect or a currency conversion for dissatisfaction.

## What the model can and cannot do

The selected model is {champion}. Its untouched test ROC area is {n('roc',raw['roc_auc'],'.3f')} and average precision is {n('ap',raw['pr_auc'],'.3f')}, against a test-prevalence floor of {n('floor',raw['pr_auc_floor'],'.3f')}. Average precision summarises how well late orders rise toward the top of a ranked queue. Improvement over the floor is useful evidence of ranking information, but it does not tell an operations director that most flagged orders need rescue, or that rescue will work.

The modelling cohorts have late rates of {n('train_rate',m['splits'][0]['late_rate'],'.1%')} in training, {n('validation_rate',m['splits'][1]['late_rate'],'.1%')} in validation and {n('test_rate',m['splits'][2]['late_rate'],'.1%')} in test. This drift matters for costs: a flag means less when background risk falls. Isotonic calibration {calibration_direction} test expected calibration error from {n('ece_before',raw['ece_10_bins'],'.3f')} to {n('ece_after',calibrated['ece_10_bins'],'.3f')}. Calibration is learned from a past period and cannot guarantee the right probabilities after another regime change. The reliability table retains sparse and empty bins so apparent improvements cannot be hidden by selective plotting.

The negative control deliberately includes future delivery-stage durations and reviews. It reaches an average precision of {n('leaky_ap',m['model_ladder'][-1]['pr_auc'],'.3f')}; that result is evidence of how misleading unavailable information can be. The legitimate feature matrices exclude those columns. Seller and route histories only see deliveries strictly before each checkout, and their cold-start priors avoid the full-sample mean. Separate validation periods choose model settings, fit calibration and choose the intervention threshold, while a completion buffer limits label leakage. There is still uncertainty about whether static extract attributes exactly match their checkout versions.

## The economic decision

The base scenario assumes an intervention fee of R${n('cost',costs['cost_brl'],'.0f')}, value of R${n('value',costs['value_brl'],'.0f')} per prevented late delivery, and effectiveness of {n('effectiveness',costs['effectiveness'],'.0%')}. These are named planning assumptions, not marketplace cost estimates. Effectiveness is the fraction of genuinely late flagged orders that can be saved. The programme pays the fee on false positives as well as genuinely late orders.

The validation-selected active candidate flags {n('flags',costs['flagged'])} test orders at a probability threshold of {n('threshold',costs['threshold'],'.3f')}. Only {n('precision',costs['precision'],'.1%')} of its flagged orders are actually late. Its expected net value under the scenario is R${n('net',costs['net_per_order'],'.3f')} per incoming order. Break-even therefore requires effectiveness of {n('break_even',costs['break_even_effectiveness'],'.1%')}; the interval induced by uncertainty in precision runs from {n('break_even_lower',costs['break_even_lower'],'.1%')} to {n('break_even_upper',costs['break_even_upper'],'.1%')}. This interval excludes the much larger question of whether any intervention has the assumed causal effect.

Across {n('cells',costs['sensitivity_cells'])} cost, value and effectiveness scenarios, {n('positive_cells',costs['net_positive_cells'])} produce positive test value after validation-based policy selection. Cells rejected by validation implement no intervention. These are scenario counts, not a probability that deployment succeeds. The test set is used to evaluate frozen choices, never to select the most flattering threshold. The uncalibrated model, calibrated model and no-action policy should all remain visible when planning a prospective trial.

## What to do next

Give the route and seller audit queues to operations alongside volumes, expected late counts and uncertainty, and trace representative failures through dispatch and delivery events. Verify seller assignment and promise changes before attributing a problem. Establish whether the available lever changes pickup readiness, transit service or merely the promised date. A more generous promise can improve this target while leaving the customer waiting just as long.

Before paying for model-triggered intervention, collect carrier and service identifiers, parcel-level milestones, original and revised promises, inventory readiness, actual intervention fees, margin and subsequent customer activity. Run a controlled pilot with an untreated comparison group and predeclared economics. Measure prevented lateness and net contribution directly, including false-positive cost and customer impact. Monitor calibration and policy value over time; retraining cannot substitute for establishing that an operational action works.

## Limitations

This is a single marketplace during {n('min_year',p['min_purchase_year'],'.0f')}–{n('max_year',p['max_purchase_year'],'.0f')}, not evidence about today's network. Late means late against Olist's own promise, not late against customer need. The midnight timestamp convention can count an arrival on the promised calendar date as late. There is no carrier identity or observed intervention, margin, retention or cost data. Coordinates are zip-centroid straight-line proxies, and review response is selective.

The source contains {n('loaded',ex.retained.iloc[0])} orders; the modelling cohort retains {n('retained',p['orders'])} after the published exclusion ladder. Delivered-only selection excludes cancellations and unresolved delivery failures, while monotonicity filters remove some genuine operational anomalies along with bad records. Mix-adjusted comparisons remain observational, and the confidence intervals omit model-estimation uncertainty and dependence between orders. Pooled descriptive adjustment and future forecasting serve different questions. Those limits support a targeted investigation and a measured pilot, rather than an unsupported claim that this historical model is deployment-ready.
"""
    (c.ROOT / "docs" / "DECISION_MEMO.md").write_text(memo, encoding="utf-8", newline="\n")
    pd.DataFrame(ledger).drop_duplicates().to_csv(c.TABLES / "memo_number_ledger.csv", index=False)
    model_table = markdown_table(ladder, {"model":"Model", "roc_auc":"ROC-AUC", "pr_auc":"PR-AUC (AP)", "brier":"Brier", "log_loss":"Log loss", "pr_auc_floor":"AP floor"}, {key:".4f" for key in ("roc_auc","pr_auc","brier","log_loss","pr_auc_floor")})
    exclusion_table = markdown_table(ex,{"filter":"Sequential filter","retained":"Retained","excluded_at_step":"Excluded at step"},{"retained":",.0f","excluded_at_step":",.0f"})
    readme = f"""# OnTime

**E-commerce delivery-risk and operational-driver analytics — DuckDB, SQL and Python.** {recommendation}

- **Rio de Janeiro:** adjusted SMR **{rio['smr']:.2f}** (95% CI **{rio['ci_lower']:.2f}–{rio['ci_upper']:.2f}**), with **{rio['excess_late_orders']:,.0f}** excess late orders.
- **Seller action queue:** **{tail['sellers']} sellers**, **{tail['order_share']:.1%}** of orders, aggregate SMR **{tail['smr']:.2f}**, **{tail['excess_late_orders']:,.0f}** excess orders; volume threshold and FDR screening are explicit.
- **Longer routes:** **{m['decomposition']['linehaul_share_beyond_200km']:.1%}** of allocated late days beyond 200 km sit in the carrier stage, under a descriptive benchmark convention.
- **Economics:** base active candidate needs **{costs['break_even_effectiveness']:.1%} effectiveness** to break even; **{costs['net_positive_cells']}/{costs['sensitivity_cells']}** sensitivity scenarios have positive held-out value.

![Mix-adjusted state lateness with exact Poisson intervals](outputs/figures/fig02_state_smr.png)

Read the **[decision memo](docs/DECISION_MEMO.md)** for the recommendation and **[methods](docs/METHODS.md)** for definitions, availability assumptions and uncertainty.

![Stage allocation of observed late days](outputs/figures/fig04_day_decomposition.png)

## Honest model results

{model_table}

![Legitimate model ladder and the deliberately leaky control](outputs/figures/fig05_model_ladder.png)

Champion: **{champion}**. {m['champion_reason']}
The checkout-only average precision is the real forecasting result; the leaky control uses information that arrives after checkout and cannot support deployment. PR-AUC here means average precision, not trapezoidal PR area. Log loss clips probabilities at 0.000001 and 0.999999.

Isotonic test ECE {calibration_direction} from **{raw['ece_10_bins']:.4f}** to **{calibrated['ece_10_bins']:.4f}**. Calibrated Brier: **{calibrated['brier']:.4f}**; calibrated log loss: **{calibrated['log_loss']:.4f}**. Results are reported as measured, without forcing the prompt's expected improvement.

The active candidate has **{costs['precision']:.1%}** test precision and **R${costs['net_per_order']:.3f}** expected net per incoming order at assumed cost **R${costs['cost_brl']:.0f}**, value **R${costs['value_brl']:.0f}**, and effectiveness **{costs['effectiveness']:.0%}**. No action is explicitly available; monetary values and efficacy are scenarios, not observed business outcomes.

## Pipeline

```text
Pinned public CSVs → DuckDB typed staging → 28 DQ assertions → order_fact
    → strictly prior ASOF seller/route histories → chronological split
    → model ladder → held-out isotonic calibration → validation-selected policy
    → pooled mix-only standardisation + day decomposition → economic scenarios
    → auditable tables + eight figures + decision memo
```

All warehouse schema, typing, joins and aggregation SQL lives in `.sql` files. Python runners handle execution, modelling, statistical intervals and reporting. Downloads are separate; build, analysis, figures and tests use no network. There is no notebook execution order to reconstruct.

## Reproduce it

Requirements: **Python 3.11+**, Git and GNU Make. Verified locally with Python **{m['environment']['python']}**; all Python runtime dependencies are pinned. Use Python 3.13 for the closest cross-platform comparison. On Windows, install GNU Make or put a portable `make.exe` on PATH; commands below work in PowerShell with that prerequisite.

```bash
git clone https://github.com/kashakkhushi/ontime-delivery-risk.git
cd ontime-delivery-risk
make all
```

`make all` creates a fresh `.venv`, installs the lock, verifies/downloads raw files, builds the warehouse, runs all analysis, regenerates documentation and eight figures, and runs offline tests. Stage commands are also available:

```bash
make setup
make data       # network only here; valid SHA-256 cache is skipped
make build      # offline warehouse, models, tables and memo
make figures   # offline; reads saved tables only
make test      # offline; approximately sixty tests, under a minute
```

For a full-run determinism check (separate from the fast tests):

```bash
.venv/bin/python scripts/verify_reproducibility.py
# Windows: .venv\\Scripts\\python.exe scripts/verify_reproducibility.py
```

The check runs the entire statistical pipeline twice and requires byte-identical `outputs/metrics.json`. Same-platform pinned-environment reproducibility is tested; floating-point differences across operating systems or BLAS implementations are not promised to be bitwise identical. The GitHub Actions workflow provides a Linux reproduction path.

### Cohort accounting

{exclusion_table}

Chronological cutoffs are **{c.TRAIN_END}** and **{c.VALIDATION_END}**. Fold late rates are **{m['splits'][0]['late_rate']:.2%} / {m['splits'][1]['late_rate']:.2%} / {m['splits'][2]['late_rate']:.2%}** (train/validation/test). Training labels must already be known at the training cutoff; separate tuning/calibration/policy windows and the April maturity buffer are described in methods and `development_subsets.csv`.

## Data, attribution and limits

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), Olist and André Sionek, **CC BY-NC-SA 4.0**. Downloads use a pinned commit from Olist's public GitHub repository, with exact URLs, retrieval dates and SHA-256s in **[data/SOURCE.md](data/SOURCE.md)**. No Kaggle API is used. An earlier malformed mirror was rejected and documented. Raw CSVs and the DuckDB database are ignored; analytical tables, figures and documentation are tracked. Code is MIT; data-derived outputs retain CC BY-NC-SA attribution and terms.

This is a delivered-only, single-marketplace historical cohort. Late is strictly after the recorded promise timestamp, including later on that calendar date. Adjusted comparisons are associations, not causal effects; Poisson CIs omit fitted-expectation uncertainty and clustering. There is no carrier identity, actual route, intervention effect or commercial cost data. Dominant-seller attribution simplifies multi-seller orders, and checkout availability of extract attributes requires production validation.

## Repository layout

```text
data/SOURCE.md, manifest.json, dq_report.md  Provenance and quality report
sql/                                       Warehouse logic and ASOF joins
src/ontime/                                Thin runners and analytical modules
tests/                                    Offline leakage, schema, maths and cost tests
scripts/verify_reproducibility.py           Full statistical rerun comparison
outputs/metrics.json                       Machine-readable results
outputs/tables/                            Every quoted number and memo ledger
outputs/figures/                           Eight PNGs at 150 dpi plus captions
docs/DECISION_MEMO.md, METHODS.md           Recommendation and analytical contract
```
"""
    (c.ROOT / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    print(f"Generated memo ({len(memo.split())} words) and README.")


if __name__ == "__main__":
    generate()
