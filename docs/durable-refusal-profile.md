# O6-P1B durable effect-time refusal evidence

Status: scoped Control Plane qualification for issue #21. This does not select or activate C1 and does not change grant issuance, release locks, or Execution Runtime behavior.

## Source boundary

- Task branch base: `4b399f446cea4936050b7b532dcd052068df2d8d`.
- The selected/default path remains C0 pre-effect revalidation followed by dispatch.
- The optional same-host C1 profile remains separately qualified and opt-in.
- No C2/C3 or destination-commit atomicity claim is introduced.

## Refusal record

When an immutable authorized decision reaches effect-time revalidation and current decision-critical inputs no longer resolve to the persisted authorization binding, the Control Plane now retains one minimal `EffectTimeRefusal` row before raising the existing refusal exception.

The row binds:

- `decision_id`;
- `effect_id`;
- exact current `_resolve` reason codes;
- minimized changed-input entries containing only input type, stable input identifier, expected version/state descriptor, and observed version/state descriptor;
- effect-time refusal stage and record time.

Raw proposal payload is not copied into the refusal row or ordinary refusal diagnostics.

## Qualified cases

Scoped tests establish:

- a revoked grant retains `grant_not_active` rather than only the previous generic exception text;
- the observed grant revision/status version is retained;
- disabling the refusal writer causes the evidence assertion itself to fail;
- two concurrent refusals for distinct revoked grant IDs remain attributed to their own decision/effect and grant item;
- destination state remains untouched for pre-dispatch refusal.

## Limitations

This record is evidence of Control Plane refusal, not proof of remote non-effect. C0 still has a residual change-after-check/before-destination-commit race. C1 remains optional, same-host only, and is not activated by this work. The refusal record does not issue authority, close Execution Runtime attempts, reconcile remote settlement, or establish distributed atomicity.
