import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.inspection import permutation_importance

def compute_continuous_metrics(y_pred: np.ndarray, y_obs: np.ndarray, raw_nwp_rmse: float = None, raw_nwp_mae: float = None) -> dict:
    """Calculates continuous forecast verification metrics: RMSE, MAE, Bias, Pearson r, R^2, and % improvements."""
    n = len(y_obs)
    if n == 0:
        return {"n": 0, "rmse": None, "mae": None, "bias": None, "r_corr": None, "r2": None}

    diff = y_pred - y_obs
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))
    bias = float(np.mean(diff))

    # Pearson r
    if np.std(y_pred) > 1e-9 and np.std(y_obs) > 1e-9:
        r_corr = float(pearsonr(y_pred, y_obs)[0])
    else:
        r_corr = 0.0

    # R^2 score
    ss_res = np.sum(diff ** 2)
    ss_tot = np.sum((y_obs - np.mean(y_obs)) ** 2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-9 else 0.0

    metrics = {
        "n": n,
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "bias": round(bias, 4),
        "r_corr": round(r_corr, 4),
        "r2": round(r2, 4)
    }

    if raw_nwp_rmse is not None and raw_nwp_rmse > 1e-9:
        rmse_imp = float(((raw_nwp_rmse - rmse) / raw_nwp_rmse) * 100.0)
        metrics["rmse_improvement_pct"] = round(rmse_imp, 2)
        metrics["rmse_status"] = "improvement" if rmse_imp >= 0 else "degradation"

    if raw_nwp_mae is not None and raw_nwp_mae > 1e-9:
        mae_imp = float(((raw_nwp_mae - mae) / raw_nwp_mae) * 100.0)
        metrics["mae_improvement_pct"] = round(mae_imp, 2)
        metrics["mae_status"] = "improvement" if mae_imp >= 0 else "degradation"

    return metrics

def compute_contingency_table(y_pred: np.ndarray, y_obs: np.ndarray, threshold: float) -> dict:
    """
    Computes categorical threshold metrics: Hits, Misses, FA, CN, POD, FAR, CSI, ETS, Frequency Bias.
    Returns 'N/A' when mathematically undefined (zero observed or forecast events).
    """
    n = len(y_obs)
    pred_event = (y_pred >= threshold)
    obs_event = (y_obs >= threshold)

    h = int(np.sum(pred_event & obs_event))
    m = int(np.sum(~pred_event & obs_event))
    fa = int(np.sum(pred_event & ~obs_event))
    cn = int(np.sum(~pred_event & ~obs_event))

    obs_events = h + m
    forecast_events = h + fa
    rare_warning = (obs_events > 0 and obs_events < 10)

    # POD = H / (H + M)
    pod = round(float(h / (h + m)), 4) if (h + m) > 0 else "N/A"

    # FAR = FA / (H + FA)
    far = round(float(fa / (h + fa)), 4) if (h + fa) > 0 else "N/A"

    # CSI = H / (H + M + FA)
    csi = round(float(h / (h + m + fa)), 4) if (h + m + fa) > 0 else "N/A"

    # Frequency Bias = (H + FA) / (H + M)
    frequency_bias = round(float((h + fa) / (h + m)), 4) if (h + m) > 0 else "N/A"

    # ETS = (H - H_random) / (H + M + FA - H_random)
    if n > 0:
        h_random = float(((h + m) * (h + fa)) / n)
        denom = float(h + m + fa - h_random)
        ets = round(float((h - h_random) / denom), 4) if abs(denom) > 1e-9 else "N/A"
    else:
        ets = "N/A"

    return {
        "threshold_mm": threshold,
        "total_records": n,
        "observed_events": obs_events,
        "forecast_events": forecast_events,
        "hits": h,
        "misses": m,
        "false_alarms": fa,
        "correct_negatives": cn,
        "pod": pod,
        "far": far,
        "csi": csi,
        "ets": ets,
        "frequency_bias": frequency_bias,
        "rare_event_warning": rare_warning
    }

def compute_brier_score(y_prob: np.ndarray, y_obs: np.ndarray, threshold: float) -> dict:
    """Calculates Brier Score for probability forecasts against binary threshold target."""
    y_binary = (y_obs >= threshold).astype(int)
    n = len(y_obs)
    if n == 0:
        return {"threshold": threshold, "brier_score": None, "sample_size": 0}

    bs = float(np.mean((y_prob - y_binary) ** 2))
    return {
        "threshold_mm": threshold,
        "brier_score": round(bs, 4),
        "sample_size": n,
        "positive_cases": int(np.sum(y_binary))
    }

def compute_permutation_feature_importance(model, X_val: pd.DataFrame, y_val: np.ndarray) -> list[dict]:
    """Calculates permutation feature importance on validation set."""
    r = permutation_importance(
        model, X_val.values, y_val, 
        n_repeats=3, max_samples=3000, random_state=42, 
        scoring='neg_root_mean_squared_error'
    )
    
    importances = []
    feature_names = list(X_val.columns)
    for i in r.importances_mean.argsort()[::-1]:
        importances.append({
            "feature": feature_names[i],
            "importance_score": round(float(r.importances_mean[i]), 5),
            "std": round(float(r.importances_std[i]), 5)
        })
    return importances
