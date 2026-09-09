"""Fixed model ladder, validation-only selection, and an isolated leaky control."""
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss
from threadpoolctl import threadpool_limits
from . import config as c
from .features import encoder, feature_frame
from .split import development_masks


def score(y, probability):
    p = np.asarray(probability, dtype=float)
    return {"roc_auc": float(roc_auc_score(y, p)), "pr_auc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)),
            "log_loss": float(log_loss(y, np.clip(p, 1e-6, 1-1e-6), labels=[0, 1])),
            "pr_auc_floor": float(np.mean(y))}


def logistic(C=1.0):
    # liblinear is deterministic and fast on this sparse, binary problem.
    return LogisticRegression(C=C, solver="liblinear", max_iter=2000, tol=1e-6, random_state=c.SEED)


def boosted():
    return LGBMClassifier(n_estimators=700, learning_rate=0.035, num_leaves=15,
                          max_depth=6, min_child_samples=150, reg_alpha=1.0, reg_lambda=10.0,
                          colsample_bytree=0.85, subsample=1.0, verbosity=-1,
                          deterministic=True, force_col_wise=True, random_state=c.SEED, n_jobs=1)


def fit_ladder(frame):
    masks = development_masks(frame)
    y = frame.is_late.to_numpy()
    predictions, models, results, validation = {}, {}, [], []
    tr, va, te = [masks[key].to_numpy() for key in ("train", "tune", "test")]
    mean = float(y[tr].mean())

    def record(name, p, obj=None, kind="full"):
        predictions[name] = np.asarray(p)
        models[name] = (obj, kind)
        results.append({"model": name, **score(y[te], p[te])})
        validation.append({"model": name, **score(y[va], p[va])})

    record("majority_never_late", np.zeros(len(frame)))
    record("base_rate_constant", np.full(len(frame), mean))
    encoders, matrices = {}, {}
    for kind in ("distance", "full", "leaky"):
        enc = encoder(kind)
        X = feature_frame(frame, kind)
        enc.fit(X.loc[tr])
        matrices[kind] = enc.transform(X)
        encoders[kind] = enc

    with threadpool_limits(limits=1):
        for name, kind, strength in (("distance_logistic", "distance", 1.0), ("full_logistic", "full", 1.0)):
            model = logistic(strength).fit(matrices[kind][tr], y[tr])
            record(name, model.predict_proba(matrices[kind])[:, 1], model, kind)
            print(f"fitted: {name}", flush=True)
        sweep, candidates = [], []
        for strength in (0.001, 0.01, 0.1, 1.0, 10.0):
            model = logistic(strength).fit(matrices["full"][tr], y[tr])
            p = model.predict_proba(matrices["full"])[:, 1]
            metric = score(y[va], p[va])
            sweep.append({"C": strength, **metric})
            candidates.append((metric["pr_auc"], -strength, model, p))
        chosen = max(candidates, key=lambda row: (row[0], row[1]))
        record("regularised_logistic", chosen[3], chosen[2])
        pd.DataFrame(sweep).to_csv(c.TABLES / "l2_sweep.csv", index=False)
        for name, kind in (("lightgbm", "full"), ("leaky_negative_control", "leaky")):
            X = matrices[kind]
            model = boosted().fit(X[tr], y[tr], eval_set=[(X[va], y[va])], eval_metric="average_precision",
                                  callbacks=[early_stopping(60, first_metric_only=True, verbose=False), log_evaluation(0)])
            record(name, model.predict_proba(X)[:, 1], model, kind)
            print(f"fitted: {name}, iterations={model.best_iteration_}", flush=True)
    val = pd.DataFrame(validation).set_index("model")
    gap = float(val.loc["lightgbm", "pr_auc"]-val.loc["regularised_logistic", "pr_auc"])
    champion = "regularised_logistic" if gap <= c.SIMPLICITY_AP_TOLERANCE else "lightgbm"
    reason = (f"Validation AP gain for LightGBM over L2 logistic was {gap:.6f}; "
              f"the predeclared practical tolerance was {c.SIMPLICITY_AP_TOLERANCE:.2f}. "
              "This is a simplicity decision rule, not a significance test.")
    return {"ladder": pd.DataFrame(results), "validation": pd.DataFrame(validation),
            "predictions": predictions, "champion": champion, "reason": reason,
            "estimator": models[champion][0], "encoder": encoders["full"], "masks": masks}
