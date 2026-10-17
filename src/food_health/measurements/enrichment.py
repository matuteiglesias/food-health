"""Missing-only *same-row* measurement inference with explicit provenance.

Predictor graph: each target is predicted from direct observations in that
calendar row, never from earlier imputations, a hidden date interpolation,
or present/targeted values. The model is a deterministic Gaussian-kernel
conditional average (Nadaraya-Watson), not a physiological model.

Validation uses a chronological holdout grouped by calendar date, comparing
against the training-set median. Prediction bands use holdout absolute errors
and local training variation: they are heuristic uncertainty bands, not
calibrated clinical confidence intervals or posterior probabilities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
from typing import Mapping

import numpy as np

MODEL_VERSION = "observed-kernel-v1"
MIN_TRAIN = 28
MIN_HOLDOUT = 10
MIN_NEIGHBORS = 5.0
FEATURE_BANDWIDTH = 1.2

ALL_METRICS = (
    "Weight", "Waist", "Belly", "Hips", "Chest", "Shoulder",
    "Arm", "Flexed", "Forearm", "Neck", "Butt", "Butt#2",
    "Thigh", "Calf", "Body Fat", "Muscle",
)
BODY_DEVICE = frozenset({"Body Fat", "Muscle"})
# Directed graph: the first node may be more informative; sparse fallback
# leaves remain useful for 128 historical weight-only input rows.
PREDICTOR_GRAPH = {
    "Weight": (
        ("Waist", "Belly"), ("Waist", "Hips"), ("Waist",),
        ("Belly",), ("Chest",), ("Hips",),
    ),
    "Body Fat": (
        ("Weight", "Waist", "Belly"), ("Weight", "Waist"),
        ("Weight", "Belly"), ("Weight",), ("Waist",),
    ),
    "Muscle": (
        ("Weight", "Waist", "Belly"), ("Weight", "Waist"),
        ("Weight", "Belly"), ("Weight",), ("Waist",),
    ),
    "Waist": (
        ("Weight", "Belly", "Hips"), ("Weight", "Belly"),
        ("Belly", "Hips"), ("Weight",), ("Belly",),
    ),
    "Belly": (
        ("Weight", "Waist", "Hips"), ("Weight", "Waist"),
        ("Waist", "Hips"), ("Weight",), ("Waist",),
    ),
    "Hips": (
        ("Weight", "Waist", "Belly"), ("Weight", "Waist"),
        ("Waist", "Belly"), ("Weight",), ("Waist",),
    ),
    "Butt": (
        ("Weight", "Hips", "Waist"), ("Hips", "Waist"),
        ("Weight", "Hips"), ("Hips",), ("Weight",),
    ),
    "Butt#2": (
        ("Weight", "Hips", "Waist"), ("Hips", "Waist"),
        ("Weight", "Hips"), ("Hips",), ("Weight",),
    ),
    "Thigh": (
        ("Weight", "Hips", "Waist"), ("Weight", "Hips"),
        ("Hips", "Waist"), ("Hips",), ("Weight",),
    ),
    "Calf": (
        ("Weight", "Thigh", "Waist"), ("Weight", "Thigh"),
        ("Weight", "Waist"), ("Thigh",), ("Weight",),
    ),
    "Chest": (("Weight", "Shoulder", "Waist"), ("Shoulder", "Waist"),
              ("Weight", "Waist"), ("Shoulder",), ("Weight",)),
    "Shoulder": (("Weight", "Chest", "Waist"), ("Chest", "Waist"),
                 ("Weight", "Chest"), ("Chest",), ("Weight",)),
    "Arm": (("Weight", "Flexed", "Chest"), ("Flexed", "Chest"),
            ("Weight", "Flexed"), ("Flexed",), ("Weight",)),
    "Flexed": (("Weight", "Arm", "Chest"), ("Arm", "Chest"),
               ("Weight", "Arm"), ("Arm",), ("Weight",)),
    "Forearm": (("Weight", "Arm", "Flexed"), ("Weight", "Arm"),
                ("Arm", "Flexed"), ("Arm",), ("Weight",)),
    "Neck": (("Weight", "Chest", "Waist"), ("Chest", "Waist"),
             ("Weight", "Chest"), ("Chest",), ("Weight",)),
}
assert set(PREDICTOR_GRAPH) == set(ALL_METRICS)
assert all(target not in features for target,sets in PREDICTOR_GRAPH.items() for features in sets)


def _usable(value, *, target=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(float(value)) or float(value) <= 0:
        return False
    if target in BODY_DEVICE and float(value) >= 100:
        return False
    return True


def source_fingerprint(rows: list[dict]) -> str:
    """Stable digest changes on corrected values/dates, not input ordering."""
    return hashlib.sha256(json.dumps(
        sorted(rows, key=lambda r: (r["date"], r["source_row"])),
        sort_keys=True, separators=(",",":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _feature_examples(rows, target, features):
    candidates = []
    for row in rows:
        observed = row["observed"]
        if _usable(observed.get(target), target=target) and all(
            _usable(observed.get(feature), target=feature) for feature in features
        ):
            candidates.append((
                row["date"], row["source_row"],
                [float(observed[x]) for x in features], float(observed[target]),
            ))
    return sorted(candidates, key=lambda r: (r[0], r[1]))


def _kernel_predict(train_x, train_y, center, *, allow_extrapolation=False):
    """Kernel average, standardized distances, local effective n and dispersion."""
    scales = np.std(train_x, axis=0)
    scales = np.where(scales >= 1e-6, scales, 1.0)
    normalized = (train_x - np.mean(train_x, axis=0)) / scales
    query = (np.asarray(center) - np.mean(train_x, axis=0)) / scales
    distances = np.sqrt(np.sum((normalized - query) ** 2, axis=1))
    if not allow_extrapolation and float(np.min(distances)) > 2.5:
        return None
    weights = np.exp(-0.5 * (distances / FEATURE_BANDWIDTH) ** 2)
    total = float(weights.sum())
    if total < 1e-12:
        return None
    effective = float(total**2 / (np.square(weights).sum() + 1e-15))
    if effective < MIN_NEIGHBORS:
        return None
    predicted = float(np.dot(weights, train_y) / total)
    dispersion = math.sqrt(float(np.dot(weights, (train_y-predicted)**2) / total))
    return predicted, dispersion, effective, float(np.min(distances))


def _kernel_quantiles(train_x, train_y, center):
    """Kernel-weighted empirical conditional quantiles (descriptive, uncalibrated).

    These are *not* Bayesian posteriors and do not account for measurement
    noise or drift. The separate predictive band accounts heuristically for
    observed chronological holdout error and historical staleness.
    """
    scales=np.std(train_x,axis=0)
    scales=np.where(scales>=1e-6,scales,1.0)
    means=np.mean(train_x,axis=0)
    distances=np.sqrt(np.sum(((train_x-np.asarray(center))/scales)**2,axis=1))
    weights=np.exp(-0.5*(distances/FEATURE_BANDWIDTH)**2)
    ordering=np.argsort(train_y)
    vals=train_y[ordering]
    wgts=weights[ordering]
    total=float(wgts.sum())
    if total<1e-12:
        return None
    cdf=np.cumsum(wgts)/total
    return {
        key:float(np.interp(q,cdf,vals))
        for key,q in (("p10",0.10),("p50",0.50),("p90",0.90))
    }


def _quantile90(residuals):
    if not residuals:
        return None
    return float(np.quantile(np.asarray(residuals), 0.90))


def _fit_candidate(examples, target, features):
    """Fit/evaluate a fixed model on strictly earlier calendar dates."""
    if len(examples) < MIN_TRAIN + MIN_HOLDOUT:
        return None
    dates = sorted(set(row[0] for row in examples))
    if len(dates) < MIN_TRAIN + MIN_HOLDOUT:
        return None
    cutoff = dates[max(MIN_TRAIN, int(len(dates)*.75))]
    train = [r for r in examples if r[0] < cutoff]
    validation = [r for r in examples if r[0] >= cutoff]
    if len(train) < MIN_TRAIN or len(validation) < MIN_HOLDOUT:
        return None
    train_x = np.array([r[2] for r in train], dtype=float)
    train_y = np.array([r[3] for r in train], dtype=float)
    prior = float(np.median(train_y))
    errors, baseline_errors = [], []
    for row in validation:
        res = _kernel_predict(train_x, train_y, row[2])
        if res is not None:
            errors.append(abs(res[0] - row[3]))
            baseline_errors.append(abs(prior - row[3]))
    if len(errors) < MIN_HOLDOUT:
        return None
    mae = float(np.mean(errors))
    baseline_mae = float(np.mean(baseline_errors))
    skill = None if baseline_mae < 1e-8 else 1 - mae / baseline_mae
    val_band = max(_quantile90(errors) or 0, _quantile90(baseline_errors) or 0)
    return {
        "target":target, "features":features,
        "train_rows":len(examples),"train_days":len(dates),
        "calibration_size":len(errors),
        "calibration_last_date":max(r[0] for r in validation),
        "last_target_date":max(r[0] for r in examples),
        "val_mae":mae, "baseline_mae":baseline_mae,
        "skill_vs_prior":skill, "val_abs_error_q90":_quantile90(errors),
        "base_uncertainty":max(val_band,1e-4),
        "trained_x":np.asarray([r[2] for r in examples],dtype=float),
        "trained_y":np.asarray([r[3] for r in examples],dtype=float),
        # Marginal prior retained as separate reference only; not a source imputation.
        "training_prior":float(np.median([r[3] for r in examples])),
    }


def fit_predictor_graph(rows: list[dict]) -> dict:
    """Select candidates per directed edge; keep both validated and weak routes."""
    models={}
    for target, options in PREDICTOR_GRAPH.items():
        viable=[]
        for order, features in enumerate(options):
            tested=_fit_candidate(_feature_examples(rows,target,features),target,features)
            if tested is not None:
                tested["route_priority"]=order
                viable.append(tested)
        models[target]=viable
    return models


def infer_missing(rows: list[dict]) -> dict:
    """Train only on OBSERVED targets; enrich rows without modifying originals.

    Each same-row prediction uses only directly observed predictor features,
    never another estimated feature. No interpolation and no date creation.
    """
    if not rows:
        raise ValueError("Empty source cannot be enriched")
    if len({r["source_row"] for r in rows}) != len(rows):
        raise ValueError("Duplicate source rows")
    models = fit_predictor_graph(rows)
    projections=[]
    estimates=0
    methods={}
    for row in rows:
        date_value=date.fromisoformat(row["date"])
        observed=row["observed"]
        predicted={}
        for target in ALL_METRICS:
            # No replacement or overwrite, even if the observation looks unusual.
            if target in observed:
                continue
            choices=[]
            for model in models[target]:
                features=model["features"]
                if not all(_usable(observed.get(f),target=f) for f in features):
                    continue
                result=_kernel_predict(
                    model["trained_x"],model["trained_y"],
                    [observed[f] for f in features],
                )
                if result is None:
                    continue
                center,local_sd,effective,nearest=result
                # Score routes by validated skill, using richer features
                # only if they have demonstrable out-of-sample benefit.
                skill=model["skill_vs_prior"]
                candidatescore=(skill if skill is not None else -1.0)
                choices.append((candidatescore, -model["route_priority"],
                                model, center, local_sd, effective, nearest))
            if not choices:
                continue  # abstain: never unconditional fill absent evidence
            # Validated route preferred; otherwise nearest available route is
            # still an *explicit low-confidence* educated guess.
            best=max(choices,key=lambda x:(x[0]>=.05,x[0],x[1]))
            skill,_,model,center,local_sd,effective,nearest=best
            conditional=_kernel_quantiles(
                model["trained_x"],model["trained_y"],
                [observed[f] for f in model["features"]],
            )
            if conditional is None:
                continue
            gap=max(0,(date_value - date.fromisoformat(model["last_target_date"])).days)
            # Deliberately inflate retrospective error bands as transfer becomes
            # stale; heuristic, not a measured coverage probability.
            drift_multiplier=math.sqrt(1+gap/365)
            half_width=max(model["base_uncertainty"],1.64*local_sd)*drift_multiplier
            bounded_center=min(100.,max(0.,center)) if target in BODY_DEVICE else center
            lower=max(0.,bounded_center-half_width)
            upper=min(100.,bounded_center+half_width) if target in BODY_DEVICE else bounded_center+half_width
            if not math.isfinite(bounded_center+upper+lower):
                continue
            confidence="weak" if skill < .05 else "validated_on_historical_holdout"
            if target in BODY_DEVICE and gap > 365:
                confidence="historical_device_proxy__temporal_transfer_unvalidated"
            item={
                "value":round(bounded_center,5),
                "lower":round(lower,5),"upper":round(upper,5),
                "status":"estimated_not_observed",
                "method":"nadaraya_watson_gaussian_kernel",
                "features":list(model["features"]),
                "model_version":MODEL_VERSION,
                "source_type":"old_scale_proxy" if target in BODY_DEVICE else "body_circumference_or_weight",
                "confidence":confidence,
                "band_semantics":"heuristic predictive range; not guaranteed 90% coverage",
                "conditional_distribution":{
                    "method":"kernel_weighted_empirical_cdf",
                    "p10":round(conditional["p10"],5),
                    "p50":round(conditional["p50"],5),
                    "p90":round(conditional["p90"],5),
                    "semantics":"uncalibrated conditional source-value quantiles; not Bayesian posterior",
                },
                "training_rows":model["train_rows"],
                "validation_days":model["calibration_size"],
                "holdout_mae":round(model["val_mae"],5),
                "median_baseline_mae":round(model["baseline_mae"],5),
                "skill_vs_baseline":None if model["skill_vs_prior"] is None else round(model["skill_vs_prior"],4),
                "effective_neighbor_count":round(effective,2),
                "closest_standardized_distance":round(nearest,3),
                "latest_direct_target_observation":model["last_target_date"],
                "target_observation_staleness_days":gap,
            }
            predicted[target]=item
            estimates+=1
            methods[confidence]=methods.get(confidence,0)+1
        projections.append({
            "date":row["date"],"source_row":row["source_row"],
            "estimated":predicted,
        })
    return {
        "schema_version":1, "model_version":MODEL_VERSION,
        "source_observation_sha256":source_fingerprint(rows),
        "input_rows":len(rows),"estimation_count":estimates,
        "estimated_status_counts":methods,
        "target_diagnostics":{
            target:[{
                "features":list(model["features"]),
                "training_rows":model["train_rows"],
                "calibration_days":model["calibration_size"],
                "holdout_mae":round(model["val_mae"],5),
                "median_baseline_mae":round(model["baseline_mae"],5),
                "skill_vs_baseline":None if model["skill_vs_prior"] is None else round(model["skill_vs_prior"],4),
                "last_target_observation":model["last_target_date"],
            } for model in edges]
            for target,edges in models.items()
        },
        "rows":projections,
    }
