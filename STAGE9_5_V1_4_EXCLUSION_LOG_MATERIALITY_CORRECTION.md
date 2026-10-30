# Stage 9.5 v1.4 Exclusion-Log Materiality Correction

**Status:** VERSIONED SCANNER/REGISTRY CORRECTION AFTER v1.3 FALSE PASS  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**v1.3 scan canonical SHA-256:** `61025a57a38466408414a4678aa33f4464d1ce04ec0a097649dd78036d37d572`  
**v1.3 CI artifact ZIP SHA-256:** `013602cbba69f1be5b2ac616d175c57be9a97b4f3217f3fd3a20219cd1cb0ac2`

## 1. Defect

The v1.3 scan returned zero unclassified material candidates, but an adversarial review of its retained exclusion log found scientifically material constants that the semantic-name matcher had excluded:

- `EXPECTED_PRE_ROWS=69260`;
- `EXPECTED_POST_ROWS=69270`;
- `PRIMARY_PHASES=(phase_a_shared_control_plane, phase_b_symbolic_arms, phase_c_offline_evaluation)`;
- `PRIMARY_ARMS=(c_frozen_symbolic, d_drift, d_periodic)`;
- `PRIMARY_WEIGHTS=(0.50,0.70,0.90,1.00)`;
- `PRIMARY_NEURAL_WEIGHT=0.50`.

The v1.3 pass is therefore not accepted as Stage-9.5-0 closure evidence.

## 2. Scientific disposition

This is a **Stage-9.5 audit-harness completeness defect**, not evidence of a Stage-8/Stage-9 scientific invalidity. The values themselves are already part of the accepted scenario/design/fusion surface and are not being changed.

No Stage-8/9 result, treatment, threshold, endpoint, seed, statistical family, or artifact is modified.

## 3. v1.4 correction

v1.4:

1. extends material-name discovery to row-count, arm, phase, and primary fusion-weight identifiers;
2. registers fixed stream row counts as scenario-construction constants;
3. registers primary phase separation and arm identity as causal-design constants;
4. registers the evaluated fusion-weight set and directly maps `PRIMARY_NEURAL_WEIGHT` to the frozen primary-lambda family;
5. adds a scanner regression test proving these identifiers cannot again fall into the exclusion log.

The closure standard remains stricter than the base protocol: zero unclassified material candidates and zero unclassified high-leverage candidates.

Any new residual is preserved and dispositioned; v1.4 does not introduce an allow-list to force a pass.
