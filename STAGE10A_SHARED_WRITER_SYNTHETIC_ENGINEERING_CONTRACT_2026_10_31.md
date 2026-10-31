# Stage-10A — shared-writer synthetic engineering contract

**Date:** 31 October 2026 (Asia/Riyadh)  
**Role:** WARM prospective engineering design; **not** a scientific protocol amendment, operational implementation acceptance, second changing-state authority, or treatment release. The HOT `STAGE10A_CURRENT_STATE_AND_RESUME.md` governs current progress.

## Why one shared writer is the primary causal design

The frozen Stage-10A question isolates the **symbolic lifecycle** against an otherwise identical neural/control trajectory, using five paired seeds and the frozen arms C, D-drift and D-periodic. Stage-8 code already separates `cd_primary_phase_a.py` (shared control-plane trajectory) from `cd_primary_phase_b.py` (symbolic arms). Its hard-error monitor reads **neural probabilities** (`cd_control_plane.py`), not arm-specific fused decisions. The proposed Stage-10A architecture therefore retains this separation: one trusted Phase-A writer **per seed**, a sealed write-once shared trace, and three strictly read-only Phase-B symbolic consumers bound to that exact trace. This is a controlled direct-effect estimand **conditional on the frozen neural trajectory**, not a claim about arbitrary systems where symbolic feedback controls the neural model.

Independent three-neural-model reruns would add stochastic or implementation divergence to the causal comparison and make an accidental Class-A mismatch harder to diagnose. An independent **read-only verifier** is still mandatory: the writer does not certify itself, and three identical self-reported digests are not evidence of actual shared raw bytes. If implementation later exposes symbolic-to-neural or fusion-to-monitor feedback, **STOP**; do not silently select this design or reinterpret the estimand. The frozen primary question would require prospective protocol-level decision before outcomes.

## Synthetic-only contract scope

`tools/stage10/stage10a_shared_writer_synthetic.py` creates an exclusive fixture writer for each seed 0–4, emits synthetic neural **tokens**, fsyncs each prediction before the fixture's 5,000-row-matured label event, seals the raw JSONL digest, and lets each of the three arms store a write-once **read-only binding**. The independent verifier re-derives the entire expected synthetic event sequence from the fixture specification, hashes actual JSONL bytes, verifies seals, arm references, seed separation and file inventory. It rejects duplicate attempts, reordered/forged events, early labels, prediction label/boundary leaks, cross-seed/unknown-arm bindings, second writers, changed hashes and unauthorized artifacts. Synthetic fixtures use only 5,001–5,003 rows to straddle latency; never the original 138,530-row stream.

The synthetic verifier **does not** prove real checkpoint loading, real shared neural state, detector adaptation, active symbolic lifecycle, real prediction journaling or immutable experiment outcomes. It will always report `real_neural_control_trajectory_verified=false`, `model_loaded_or_predicted=false`, `stage10a_release_ready=false` and `stage10a_treatment_execution_authorized=false`.

## Requirements before any future real executor

1. Trusted Phase-A witness binds exact clean Git HEAD, frozen configuration, original five seed checkpoint identities, R0.v2, preprocessing, raw row ordering, label maturity, deterministic neural RNG and optimizer chain, replay/detector/ADWIN and fusion/window identities to recomputable write-once raw traces.
2. Phase-A must produce and *seal* every seed's complete 138,530-row shared prediction/label/control trajectory before any Phase-B arm starts; failure/incomplete attempts remain write-once. The arm runner must consume the sealed trace in immutable read-only mode and must not influence Phase-A.
3. Independent, separately implemented verifier must recompute raw-file digests and trace invariants, not trust copied digest strings. An agreed manifest/trace schema is still required to bind checkpoints, intermediate update states, replay samples and source-only evaluator firewall; no post-outcome schema adjustment.
4. The frozen evaluator-only boundary 69,260 and unavailable labels must be excluded from all adaptation/monitor/candidate generation inputs. The writer may use only labels whose source row prediction was durably committed and whose 5,000-row maturity elapsed.
5. No inference, metrics, real C/D/D-periodic predictions, checkpoint deserialization or experimental outcomes may be generated until the actual operational implementation passes independent validation and a **separate versioned Stage-10A RELEASE** is explicitly approved. The source receipt and checkpoint source-only gate already accepted are not rerun.

The currently frozen master and Stage-10A manifest remain unchanged with their execution flags `false`; five seeds remain the only causal replication units. Existing Stage-8/9 evidence is not overwritten.
