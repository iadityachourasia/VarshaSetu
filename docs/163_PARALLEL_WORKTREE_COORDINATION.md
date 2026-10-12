# Parallel research-pilot worktree coordination

Date: 2026-10-07. Integration checkout: `C:\SIH26\Varsha-NXT` on `master`.
The four worktrees were created with the project's **working-tree** starting
state while the integration checkout had 232 changed or untracked files. Before
release, 243 required paths (the dirty file set plus mandatory governance
documents) were checked in every worktree. All were present and content-equal
after CRLF normalization; no scientific data values were decoded by this
verification. No task started from a clean `master` fallback.

| Task | Worktree | Branch | Owned result |
|---|---|---|---|
| 1: 2026 source/version | `C:\Users\Adity\.codex\worktrees\e949\Varsha-NXT` | `codex/2026-source-clearance` | `docs/159_2026_SOURCE_VERSION_CLEARANCE.md` and task-prefixed source audit files |
| 2: extreme probability | `C:\Users\Adity\.codex\worktrees\0343\Varsha-NXT` | `codex/extreme-probability-research` | `docs/160_EXTREME_EVENT_PROBABILITY_RESEARCH.md` and `extreme_*` files |
| 3: regime evidence | `C:\Users\Adity\.codex\worktrees\5513\Varsha-NXT` | `codex/independent-regime-evidence` | `docs/161_INDEPENDENT_REGIME_EVIDENCE.md` and regime annotation/winter files |
| 4: India product | `C:\Users\Adity\.codex\worktrees\f8d0\Varsha-NXT` | `codex/india-corrected-product` | `docs/162_INDIA_WIDE_CORRECTED_PRODUCT.md` and `india_*` files |

The 125 ignored 2026 IMD daily grids are absent from these worktrees. They
remain in the original checkout and passed the read-only `--check-2026` hash
check (manifest SHA-256
`638e713868e664509176aef207a6117213de437d924dc60f41dc2958cce50db4`).
Tasks may use verified ignored artifacts read-only from the original path.
They must not copy large corpora or decode, pair, or score 2026 rainfall values.

Each task owns distinct files and must report branch, worktree, changes, tests,
findings, and blockers. Frozen protocols, 2026 forecasts, source receipts,
and consumed-test results are read-only. The main chat grants an exclusive
slot before any RAM-intensive decode or training job. Completed work is
reviewed and integrated **one task at a time** into the original checkout,
with relevant checks after each integration. Scientific promotion and public
warning gates remain unchanged.

## Integration record

1. **Task 1:** Five owned files were copied into the integration checkout with
   matching SHA-256. The audit `--check` reproduced four open blockers, three
   focused tests passed, and the 2026 scorer preflight still refused before
   observation access.
2. **Task 4:** Three owned files were copied with matching hashes. The five
   new stage unit tests passed in the integration checkout. A broader
   evidence-backed run produced 17 initial passes but was stopped while the
   Task 2 compute slot was active; it is not recorded as a full-suite pass.
3. **Task 3:** Five committed, owned files were copied with matching hashes.
   Eleven annotation and existing packet tests passed in the integration
   checkout. No human labels or winter cases were admitted.
4. **Task 2:** Twelve owned files, including its sealed protocol, predictions,
   score and receipts, were copied with matching hashes. The main chat
   completed the result interpretation after the task's verification turn
   stopped making visible progress. Four focused tests passed; rerunning the
   scorer against the same original-checkout 2024 sources reproduced the
   sealed result byte-for-byte. The prespecified candidate failed its gate.

These copies do not include unrelated pre-existing dirty files or ignored
data. The main checkout remains the integration target. No new model is
promoted and the 2026 independent-test preflight remains blocked.

## Integrated four-task disposition, 8 October

All four task-owned changes are present in the original checkout and their handoffs are closed as engineering work. The independent scientific and external gates remain open. `scripts/audit_four_workstreams.py --check` reproduces the write-once `four_workstreams_closeout_v1.json` from sealed source, probability, regime and east-coast evidence without reading 2026 rainfall values. Its disposition is: source clearance externally blocked; ordinal extreme probability failed its prespecified gate; independent regime handoff ready but no expert labels or winter cases; east-coast 2023-fit/consumed-2024 stage model failed the Raw comparison and is not a product. The post-stage full backend suite passed 817 tests; the new audit integrity tests passed 2/2 afterward. See `docs/164` for exact commands and limitations. This record does not mark any blocked scientific gate as passed.

## Final original-checkout merge verification

On 8 October, all **25 distinct task-owned paths** from the four worktree handoffs were compared by SHA-256 against the original `master` working tree. Nineteen are byte-equal. Six differ only because the original checkout has later integrated work: `docs/159` adds the source follow-up, `docs/160` replaces the task's pending-result paragraph with the actual failed score and later diagnostics, `docs/161` and `docs/162` append the reviewer handoff and east-coast experiment, and the regime validator plus its test strengthen evidence-overlap handling. Exact diffs were inspected for the three files that were not simple append-only documents. Task 3's five-file commit is fully represented in the original checkout. The other three task branches share the original `e2aa635` HEAD, with task outputs already copied as uncommitted/untracked files. No `git merge` or commit was needed or made; the original checkout remains the only integration tree, and its more recent work was preserved.
