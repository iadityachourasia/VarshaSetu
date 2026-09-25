try:
    from backend.app.services.pipeline import ScientificPipelineService
    from backend.app.data.readiness import ScientificReadinessError
except ModuleNotFoundError:
    from app.services.pipeline import ScientificPipelineService
    from app.data.readiness import ScientificReadinessError

def main():
    print("=" * 63)
    print("VARSHASETU — SIH26080 TRAINING READINESS GATE")
    print("=" * 63)
    
    service = ScientificPipelineService()
    try:
        report = service.run_full_pipeline()
    except ScientificReadinessError as exc:
        print("TRAINING BLOCKED BY SCIENTIFIC READINESS GATE")
        for blocker in exc.blockers:
            print(f" - {blocker}")
        raise SystemExit(2) from exc
    
    test_m = report["test_2025_metrics"]
    print("\n--- INDEPENDENT TEST SET SUMMARY RESULTS ---")
    print(f"Raw NWP Baseline RMSE:     {test_m['raw_nwp']['rmse']:.4f} mm | MAE: {test_m['raw_nwp']['mae']:.4f} mm | R2: {test_m['raw_nwp']['r2']:.4f}")
    print(f"Linear MOS Model RMSE:     {test_m['linear_mos']['rmse']:.4f} mm | MAE: {test_m['linear_mos']['mae']:.4f} mm | R2: {test_m['linear_mos']['r2']:.4f} | Imp: {test_m['linear_mos'].get('rmse_improvement_pct', 0.0)}%")
    print(f"Selected Global ML RMSE:   {test_m['selected_global_ml']['rmse']:.4f} mm | MAE: {test_m['selected_global_ml']['mae']:.4f} mm | R2: {test_m['selected_global_ml']['r2']:.4f} | Imp: {test_m['selected_global_ml'].get('rmse_improvement_pct', 0.0)}%")
    print(f"Regime-Aware ML RMSE:      {test_m['regime_aware_ml']['rmse']:.4f} mm | MAE: {test_m['regime_aware_ml']['mae']:.4f} mm | R2: {test_m['regime_aware_ml']['r2']:.4f} | Imp: {test_m['regime_aware_ml'].get('rmse_improvement_pct', 0.0)}%")
    print(f"Oracle Upper Bound RMSE:   {test_m['oracle_regime_ml']['rmse']:.4f} mm | MAE: {test_m['oracle_regime_ml']['mae']:.4f} mm | R2: {test_m['oracle_regime_ml']['r2']:.4f} (Diagnostic Reference)")
    print(f"\nRegime Classifier Accuracy: {report['regime_classifier']['overall_accuracy'] * 100:.2f}%")
    print("=" * 63)

if __name__ == "__main__":
    main()
