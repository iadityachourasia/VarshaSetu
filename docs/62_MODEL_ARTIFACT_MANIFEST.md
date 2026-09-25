# Phase 2B Model Artifact Manifest

This append-only manifest points to the frozen selection record, hash-addressed deterministic feature caches, safe model files, and reports. Full SHA-256 references, source lineage, code hashes, runtime versions, hardware benchmark context, and protected-lock history are in `data/manifests/phase2b/artifact_manifest.json`.

- Freeze manifest SHA-256: `b9f0634e4db9de606406f7bfd77d23036740513047be557349aefefdd9ecf08d`
- 2019 Phase 1F source Zarr tree SHA-256: `13fc4ea03f0724fc6a3c0506de1a30b1acb5be4f8dc803c9ea46bb2b5377cb9e`
- Models: native XGBoost JSON and safe JSON Ridge only.
- Feature caches: safe `.npy` arrays loaded with `allow_pickle=False`; each array and cache manifest is hash-verified.
- Execution device: `cpu`; CPU/CUDA equivalence details are preserved in `cpu_gpu_benchmark.json`.
- Phase 1B historical lock: unchanged (`14e106b95ee5900e71bbca43b003a604d9c0eb44fee092f9e843f756666ac0a9`); the versioned supersession explicitly covers the two later blocked-API/readiness files while the other 16 remain unchanged.
- Pickle/joblib authority: none.
- Test results: `2019_final_results.json`; no post-test selection or retuning.
