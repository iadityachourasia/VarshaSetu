import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

try:
    from backend.app.version import API_VERSION, deployed_commit
    from backend.app.core.config import REPORTS_DIR
    from backend.app.data.audit import datasetAudit
    from backend.app.services.pipeline import ScientificPipelineService
except ModuleNotFoundError:
    from app.version import API_VERSION, deployed_commit
    from app.core.config import REPORTS_DIR
    from app.data.audit import datasetAudit
    from app.services.pipeline import ScientificPipelineService


router = APIRouter()
pipeline_service = ScientificPipelineService()


def _legacy_unavailable(reason: str) -> HTTPException:
    return HTTPException(
        status_code=410,
        detail={
            "code": "LEGACY_DATASET_UNAVAILABLE",
            "detail": "The quarantined legacy prototype dataset is not deployed here, so this legacy endpoint is retired. "
                      "Scientific output is served only by /api/science/*. " + reason,
        },
    )


def _load_current_state() -> tuple:
    """Legacy dataset state. Any load failure (for example the CSV is not part of a deployed image) is a structured 410,
    never an unhandled 500."""
    try:
        pipeline_service.ensure_loaded()
    except Exception as error:  # noqa: BLE001 - every failure to load the quarantined dataset means the same thing
        raise _legacy_unavailable(type(error).__name__) from error
    return pipeline_service.df, pipeline_service.file_metadata, pipeline_service.readiness


def _retired(endpoint: str, replacement: str) -> HTTPException:
    return HTTPException(
        status_code=410,
        detail={
            "code": "LEGACY_ENDPOINT_RETIRED",
            "detail": f"{endpoint} is retired: it returned fixed, hand-written audit statements that were not computed from the "
                      f"repository, which AGENTS.md forbids presenting as an executed audit. Use {replacement}.",
        },
    )


def _blocked(operation: str) -> None:
    _, _, readiness = _load_current_state()
    raise HTTPException(
        status_code=409,
        detail={
            "status": "blocked_by_scientific_readiness_gate",
            "operation": operation,
            "message": (
                "This endpoint is disabled so legacy artifacts cannot be presented "
                "as reproducible output from the checked-in dataset."
            ),
            "blockers": readiness.blockers,
        },
    )


def _legacy_report_identity() -> dict:
    report_path = Path(REPORTS_DIR) / "final_test_report.json"
    if not report_path.exists():
        return {"present": False}
    with report_path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)
    metadata = report.get("file_metadata", {})
    return {
        "present": True,
        "status": "quarantined_unverified_legacy_artifact",
        "filename": metadata.get("filename"),
        "sha256": metadata.get("sha256"),
        "experiment_id": report.get("experiment_id"),
        "reason": "The source dataset is absent and its hash does not match the checked-in CSV.",
    }


@router.get("/health")
def health_check():
    """Liveness of the deployed service. It does not depend on the quarantined legacy dataset, which is not part of the
    production image; the legacy readiness gate is reported separately and stays blocked."""
    return {
        "status": "ok",
        "system": "VarshaSetu scientific prototype",
        "version": API_VERSION,
        "commit": deployed_commit(),
        "scientific_api": "/api/science/status",
        "legacy_prototype": "quarantined_blocked_by_scientific_readiness_gate",
    }


@router.get("/status")
def get_status():
    _, metadata, readiness = _load_current_state()
    return {
        "project": "VarshaSetu",
        "phase": "Phase 0 — Stabilize and Reproduce",
        "scientific_readiness": readiness.to_dict(),
        "current_dataset": {
            "dataset_id": metadata["dataset_id"],
            "filename": metadata["filename"],
            "sha256": metadata["sha256"],
            "rows": metadata["total_rows"],
            "source_columns": metadata["total_columns"],
            "provenance_status": metadata["provenance_status"],
        },
        "legacy_report": _legacy_report_identity(),
    }


@router.get("/dataset/audit")
def get_dataset_audit():
    df, metadata, readiness = _load_current_state()
    result = datasetAudit(df, metadata)
    result["scientific_readiness"] = readiness.to_dict()
    return result


@router.get("/stations")
def get_stations():
    df, _, _ = _load_current_state()
    grouped = df.groupby("location_id").first().reset_index()
    return [
        {
            "location_id": int(row["location_id"]),
            "district_name": str(row["district_name"]),
            "taluka_name": str(row["taluka_name"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "elevation_m": int(row["elevation (m)"]),
            "record_count": int((df["location_id"] == row["location_id"]).sum()),
            "data_status": "prototype_provenance_unverified",
        }
        for _, row in grouped.iterrows()
    ]


@router.get("/dates")
def get_dates():
    df, _, _ = _load_current_state()
    dates_df = df[["date", "datetime"]].drop_duplicates().sort_values("datetime")
    partitions = {
        2020: "TRAIN",
        2021: "TRAIN",
        2022: "TRAIN",
        2023: "TRAIN",
        2024: "VALIDATION",
        2025: "TEST (FROZEN)",
    }
    return [
        {
            "date": str(row["date"]),
            "year": int(row["datetime"].year),
            "partition": partitions.get(int(row["datetime"].year), "OUTSIDE CONFIG"),
        }
        for _, row in dates_df.iterrows()
    ]


@router.get("/provenance")
def get_provenance():
    _, metadata, readiness = _load_current_state()
    return {
        "dataset_id": metadata["dataset_id"],
        "dataset_hash_sha256": metadata["sha256"],
        "filename": metadata["filename"],
        "total_rows": metadata["total_rows"],
        "total_columns": metadata["total_columns"],
        "manifest_file": Path(metadata["manifest_path"]).name,
        "provenance_status": metadata["provenance_status"],
        "training_eligible": metadata["training_eligible"],
        "scientific_readiness": readiness.to_dict(),
        "legacy_report": _legacy_report_identity(),
    }


@router.get("/audit")
def get_scientific_audit():
    raise _retired("GET /api/audit", "/api/science/evidence/ps-coverage and the Scientific Audit page")


@router.get("/jury-defense")
def get_jury_defense():
    raise _retired("GET /api/jury-defense", "docs/presentation/JUDGE_QA.md and /api/science/evidence/ps-coverage")


@router.get("/forecast")
def get_forecast(
    station_id: int = Query(...),
    date: str = Query(...),
    time: str | None = Query(None),
):
    del station_id, date, time
    _blocked("historical model replay")


@router.get("/metrics/overall")
def get_overall_metrics():
    _blocked("verification metrics")


@router.get("/metrics/thresholds")
def get_threshold_metrics():
    _blocked("threshold verification")


@router.get("/metrics/regimes")
def get_regime_metrics():
    _blocked("regime verification")


@router.get("/metrics/ablation")
def get_ablation_study():
    _blocked("model ablation")


@router.get("/metrics/features")
def get_feature_importance():
    _blocked("feature importance")


@router.get("/metrics/calibration")
def get_calibration():
    _blocked("probability calibration")


@router.post("/sandbox/predict")
def sandbox_predict():
    _blocked("manual model inference")
