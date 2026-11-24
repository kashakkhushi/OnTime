# OnTime — Decision memo

Do not deploy the checkout model as a paid-intervention trigger under the base assumptions. Prioritise investigation of the adjusted seller tail and Rio de Janeiro routes, with stage-specific operational audits. The validation-selected candidate loses money on the held-out test period, so no intervention is the better base-case policy.

## What is actually broken

The clearest operational signal is uneven delivery performance after accounting for the work being shipped. Rio de Janeiro has a standardised mortality ratio, used here as a standardised lateness ratio, of 1.66, with a 95% interval from 1.58 to 1.74. This corresponds to 658 more late orders than the mix model expects. The comparison accounts for category, distance band, freight class, item count and purchase month. It is a better starting point than ranking raw late rates, which partly ranks the difficulty of each state's shipment mix.

Rio is not automatically the highest-ratio state. AL leads this particular specification with a ratio of 2.05 and an interval from 1.66 to 2.51. Priorities should combine excess order volume, uncertainty, operational ownership and the cost of changing service. A large ratio on a small base is not interchangeable with a large number of affected customers. The route table provides the next level of investigation; it does not identify a specific carrier.

The seller screen flags 11 sellers covering 3,447 orders, or 3.6% of the eligible population. Their observed late rate is 15.4%, but the actionable comparison is their aggregate adjusted ratio of 1.82 and 239 excess late orders. Screening requires at least 100 orders and an excess signal that survives the specified false-discovery procedure. This identifies an audit queue, not a list of sellers proved to have caused customer harm. Selection itself makes the tail's apparent strength optimistic for a new period.

Every order is attributed to its largest seller by merchandise value. We retain 1,223 multi-seller orders rather than silently dropping them, but an order-level delivery timestamp cannot establish which seller's parcel caused its final arrival. Operational follow-up must resolve that attribution before assigning accountability. Likewise, comparisons remain sensitive to the mix variables available in this extract; service class, capacity and carrier routing are absent.

## Where the days are lost

Beyond 200 kilometres, the carrier-stage allocation accounts for 86.9% of observed late-vs-promise days under the stated decomposition. The calculation compares each late order's handling and transit durations with on-time median durations in the same distance band, then allocates its actual late days in proportion to positive stage excess. This preserves the total number of observed late days rather than treating every day in transit as an avoidable delay.

The implication is to inspect dispatch-to-delivery processes on longer routes: consolidation, sorting, last-mile handoffs, promised service and exception recovery. On short routes, use the corresponding stage split to decide whether dispatch readiness deserves equal attention. Handling is measured from purchase to carrier handoff, so it includes approval time; it is not a pure warehouse productivity measure. The transit stage also bundles activities beyond long-distance transport. Neither stage's accounting share is an estimate of how much an intervention would save.

There is a commercial warning in the reviews. Among reviewed late orders, 54.1% receive the lowest two scores, compared with 9.2% among reviewed on-time orders. The analysis separately records 639 missing reviews. Dissatisfied customers may respond differently, and product problems may affect both ratings and delivery experiences. These data support concern about customer experience; they do not supply a retention effect or a currency conversion for dissatisfaction.

## What the model can and cannot do

The selected model is regularised logistic. Its untouched test ROC area is 0.700 and average precision is 0.105, against a test-prevalence floor of 0.056. Average precision summarises how well late orders rise toward the top of a ranked queue. Improvement over the floor is useful evidence of ranking information, but it does not tell an operations director that most flagged orders need rescue, or that rescue will work.

The modelling cohorts have late rates of 7.7% in training, 12.0% in validation and 5.6% in test. This drift matters for costs: a flag means less when background risk falls. Isotonic calibration worsened test expected calibration error from 0.016 to 0.042. Calibration is learned from a past period and cannot guarantee the right probabilities after another regime change. The reliability table retains sparse and empty bins so apparent improvements cannot be hidden by selective plotting.

The negative control deliberately includes future delivery-stage durations and reviews. It reaches an average precision of 0.839; that result is evidence of how misleading unavailable information can be. The legitimate feature matrices exclude those columns. Seller and route histories only see deliveries strictly before each checkout, and their cold-start priors avoid the full-sample mean. Separate validation periods choose model settings, fit calibration and choose the intervention threshold, while a completion buffer limits label leakage. There is still uncertainty about whether static extract attributes exactly match their checkout versions.

## The economic decision

The base scenario assumes an intervention fee of R$8, value of R$80 per prevented late delivery, and effectiveness of 50%. These are named planning assumptions, not marketplace cost estimates. Effectiveness is the fraction of genuinely late flagged orders that can be saved. The programme pays the fee on false positives as well as genuinely late orders.

The validation-selected active candidate flags 1,529 test orders at a probability threshold of 0.225. Only 11.6% of its flagged orders are actually late. Its expected net value under the scenario is R$-0.289 per incoming order. Break-even therefore requires effectiveness of 86.4%; the interval induced by uncertainty in precision runs from 75.3% to 99.9%. This interval excludes the much larger question of whether any intervention has the assumed causal effect.

Across 27 cost, value and effectiveness scenarios, 3 produce positive test value after validation-based policy selection. Cells rejected by validation implement no intervention. These are scenario counts, not a probability that deployment succeeds. The test set is used to evaluate frozen choices, never to select the most flattering threshold. The uncalibrated model, calibrated model and no-action policy should all remain visible when planning a prospective trial.

## What to do next

Give the route and seller audit queues to operations alongside volumes, expected late counts and uncertainty, and trace representative failures through dispatch and delivery events. Verify seller assignment and promise changes before attributing a problem. Establish whether the available lever changes pickup readiness, transit service or merely the promised date. A more generous promise can improve this target while leaving the customer waiting just as long.

Before paying for model-triggered intervention, collect carrier and service identifiers, parcel-level milestones, original and revised promises, inventory readiness, actual intervention fees, margin and subsequent customer activity. Run a controlled pilot with an untreated comparison group and predeclared economics. Measure prevented lateness and net contribution directly, including false-positive cost and customer impact. Monitor calibration and policy value over time; retraining cannot substitute for establishing that an operational action works.

## Limitations

This is a single marketplace during 2016–2018, not evidence about today's network. Late means late against Olist's own promise, not late against customer need. The midnight timestamp convention can count an arrival on the promised calendar date as late. There is no carrier identity or observed intervention, margin, retention or cost data. Coordinates are zip-centroid straight-line proxies, and review response is selective.

The source contains 99,441 orders; the modelling cohort retains 95,082 after the published exclusion ladder. Delivered-only selection excludes cancellations and unresolved delivery failures, while monotonicity filters remove some genuine operational anomalies along with bad records. Mix-adjusted comparisons remain observational, and the confidence intervals omit model-estimation uncertainty and dependence between orders. Pooled descriptive adjustment and future forecasting serve different questions. Those limits support a targeted investigation and a measured pilot, rather than an unsupported claim that this historical model is deployment-ready.
