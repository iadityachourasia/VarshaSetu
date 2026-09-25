try:
    from backend.app.services.pipeline import ScientificPipelineService
except ModuleNotFoundError:
    from app.services.pipeline import ScientificPipelineService


def main() -> None:
    service = ScientificPipelineService()
    service.ensure_loaded()

    if service.final_report is None:
        print("EVALUATION UNAVAILABLE")
        print(
            "No report matching the checked-in dataset is available. "
            "The existing report is a quarantined legacy artifact."
        )
        for blocker in service.readiness.blockers:
            print(f" - {blocker}")
        raise SystemExit(2)

    report = service.final_report
    print(f"Experiment: {report['experiment_id']}")
    print(f"Dataset SHA-256: {report['file_metadata']['sha256']}")
    print("The report matches the configured dataset and passed the readiness gate.")


if __name__ == "__main__":
    main()
