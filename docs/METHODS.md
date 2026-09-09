# Analytical contract

## Question and estimand

The forecasting estimand is the probability of **delivered-after-promise conditional
on eventually being delivered with complete, internally consistent timestamps**.
It does not measure all-checkout failure risk: cancellation, missing outcomes,
undelivered orders and some operational anomalies are outside this cohort. A
deployment decision for all checkout traffic would need those outcomes too.

Lateness compares the recorded delivery TIMESTAMP strictly to the recorded promise
TIMESTAMP. The latter is generally midnight. An order arriving later on the same
calendar date therefore counts late, exactly as specified; changing this business
definition would change the outcome. `days_late` is the positive difference in
fractional 24-hour days, not an integer count of calendar dates.

## Grain and quality

Raw text is persisted in DuckDB and typed through views in `sql/00_staging.sql`.
There is no warehouse SQL embedded in Python. DQ findings do not crash the build;
unexpected parsing/schema failures do. `data/dq_report.md` separates failures from
documented treatments. Geo zip prefixes are not raw primary keys. Their intended
dimension grain is established by the median of latitude and longitude inside a
broad Brazil bounding box. Unknown centroids remain unknown, rather than becoming
zero-distance routes. Great-circle distance is a proxy for route length, not the
actual travelled distance. Earth radius is 6,371.0088 km.

An order's dominant seller is the seller with greatest summed item price, breaking
ties on seller ID. Its dominant category uses the same value-based rule. The
warehouse retains item count, number of sellers and full order totals. Seller and
route analyses attribute the entire order to that dominant seller; the data has
only order-level final delivery timestamps and cannot assign separate parcel
lateness to every participating seller. Payment type/instalments are taken from
the payment record with greatest value, then lowest sequence. Review score is the
latest answered review per order with deterministic tie-breaking. Missing reviews
are excluded from the reviewed-order rate and counted separately.

Only delivered orders with complete and monotone purchase/approval/carrier/customer
timestamps, valid promises, linked customers and valid items enter `order_fact`.
The exact sequential counts are exported; product measurements are cleaned to
null and imputed within training, not used to discard orders. Missing categories,
payments and geolocation remain explicit. Bad item money/linkage excludes the
order; exact duplicate item lines are deduplicated before roll-up.

## Information availability

All legitimate model matrices use an explicit `at_*` allowlist. IDs, raw
timestamps and targets are not numerical/categorical predictors. `post_*`
durations and reviews enter only the intentionally leaky negative control. That
control still uses the same training and test cohorts, making the performance
gap interpretable as availability leakage rather than a different test sample.

The published extract lacks attribute revision history. We assume quoted freight,
promised delivery, chosen payment plan, product dimensions/category, checkout
addresses and seller assignment were known then and unchanged in the extract.
That assumption needs confirmation against production event logs. The holiday
flag covers federal fixed-date holidays applicable during the data period;
local holidays, Carnival and optional observances are not inferred.

Each seller/route/distance prior uses only orders delivered **strictly before**
the scored purchase timestamp. Equal-time delivery events are grouped before
cumulative windows. Strict DuckDB ASOF inequalities exclude all ties. Additive
smoothing has weight 20 toward the expanding, also strictly prior global mean.
Before any observed delivery the explicitly assumed cold-start values are 0.08
late probability and 3 handling days; these do not use full-sample outcomes.
Histories incorporate newly delivered orders within validation and test, as an
online production history service would, while fitted models remain frozen.

## Forecasting and calibration protocol

All orders are stably sorted by purchase timestamp then ID. Training purchases
precede 2018-03-01, validation purchases precede 2018-06-01, and later purchases
form the untouched test cohort. Training labels must already be delivered before
2018-03-01. Validation is divided into March for model selection, April 1–15
for isotonic calibration and April 16–30 for threshold choice. May provides a
maturation buffer. All validation fitting labels must be available before June 1.
The report exports these development cohorts separately from the full fold rates.
There remains outcome-dependent censoring in every finite completion window; it
is a limitation, not permission to use outcomes delivered after deployment.

Imputers, scalers and encoders fit only on training. L2 C candidates are 0.001,
0.01, 0.1, 1 and 10; the best March average precision selects C. LightGBM uses
fixed conservative complexity and early stopping. A predeclared absolute
validation-AP tolerance of 0.01 favours L2 logistic over boosting. This practical
simplicity rule is not a statistical statement that models are indistinguishable.
Isotonic mapping is learned only after selection; it may worsen later calibration
under temporal drift. ECE uses ten equal-width bins with empirical count weights.
Log loss clips probabilities to [0.000001, 0.999999], including constants and
isotonic endpoints; the raw probabilities are used for the other metrics.

PR-AUC means scikit-learn's **average precision**, not trapezoidal interpolation.
For constant scores, its reference is the held-out prevalence. Thresholding a
majority classifier to never late gives the same ranking floor, with different
Brier/log-loss values from the training-prevalence constant.

## Mix adjustment and uncertainty

The descriptive expected-lateness model uses only category, distance band,
freight class, item count and month. Five interleaved held-out subsets of the
chronologically sorted pooled population provide predictions from models that
did not fit an order's own outcome. This cross-fitting is **not** the forecasting
train/validation/test split: it estimates pooled descriptive expectations, not
future accuracy. No seller/state/history/after-checkout predictor is allowed.

For any segment, E is the sum of expected probabilities, O the observed late
count, SMR=O/E and excess=O−E. Exact central Poisson limits on O are divided by E.
These intervals condition on fitted expectations and independent Poisson counts;
they omit expectation-model error, temporal dependence, repeat-customer/seller
clustering and selection effects. They are not causal estimates. The seller
action screen requires at least 100 orders, lower pointwise CI above 1 and a
one-sided Poisson excess test with Benjamini–Hochberg q≤0.05 among eligible sellers.
Selection makes the aggregate tail CI descriptive rather than post-selection
confirmatory inference. Seller IDs are anonymised, so a real intervention also
requires an operational identity mapping.

## Stage decomposition and business case

For each distance band, compute median handling and carrier-stage days among
on-time orders. For a late order, take each stage's positive excess over these
medians. Allocate its actual `days_late` in proportion to those excesses. If both
excesses are zero, allocate by its actual stage-duration shares and count this
fallback. Allocated days sum exactly to observed late days. Benchmark medians
are retrospective and used only for description. The carrier stage also includes
sorting, last mile and unobserved handoffs: no carrier identity exists.

Economic assumptions in config are fictional scenarios in BRL, not estimates
from the review association. Cost is paid for every flagged order, including
false positives. Value accrues only to would-be late orders actually saved.
Effectiveness means the fraction of would-be late flagged orders saved, not the
precision of the model. Net per incoming order = flag rate × (effectiveness ×
value × precision − cost); break-even effectiveness = cost/(value × precision).
Results above 100% indicate impossibility under that scenario.

Thresholds sweep 0–1 in steps of 0.005 plus an explicit no-intervention option.
An active candidate needs at least 100 validation flags. The base candidate is
chosen on validation, then frozen for test, even when it loses to no action. The
27 sensitivity cells use three values each for cost, value and effectiveness;
each cell repeats validation selection and enables intervention only if its
validation net is positive. Test net is a counterfactual calculation under assumed
efficacy, not measured programme return. Exact binomial precision intervals
propagate into break-even intervals but do not capture causal-effect uncertainty.

## Primary references

- [Olist dataset and data dictionary](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Pinned raw files and hashes](../data/SOURCE.md)
- [DuckDB ASOF joins](https://duckdb.org/docs/stable/guides/sql_features/asof_join)
- [scikit-learn probability calibration](https://scikit-learn.org/1.7/modules/calibration.html)
- [scikit-learn average precision](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html)
- [LightGBM deterministic parameters](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html)
- [SciPy chi-square distribution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2.html)
