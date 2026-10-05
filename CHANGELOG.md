# Changelog

## Unreleased

### Fixed — Governor validation gaps
- Resolver records are now rebound to requested identifiers, source references, institution and authority domain instead of trusting lookup keys.
- Identity, mandate and approval observations now have explicit freshness limits; future observations beyond clock tolerance fail closed.
- Runtime authorization now enforces the Authority Context requirement envelope independently from both Manifest and grant scope.
- Executed decisions must exactly match the persisted issued decision and deterministic effect identity.
- Effect execution consumes a frozen validated envelope; the unchecked post-revalidation Authority Context reread was removed.
- Legacy reviewer labels resolve only through an explicit versioned institution-scoped alias mapping whose digest/version are decision-bound.


### Added
- Bounded Manifest v1.1 and Alvorada Authority Context 0.1.0 integration surface.
- Explicit resolver contracts for grant/status, identity/delegation, issuer mandate,
  approvals, policy state, and evidence freshness.
- Stable effect and distinct attempt records with destination observation and
  reconciliation.
- Durable synthetic refund destination with restart recovery, effect deduplication,
  partial-delivery handling, and a local cumulative max_effects guard.
- Adversarial acceptance tests for substitution, revocation, staleness, delegation,
  evidence, lost acknowledgements, restart, duplicates, partial delivery, and
  concurrent attempts.

### Changed
- Legacy policy fingerprints now include payload content.
- Legacy tool execution rejects adapter name/action-type substitution before effect.

### Boundaries
- Synthetic resolver inputs are not institutionally authenticated.
- BitRep verification and Index chain inclusion are not execution grants.
- No production credentials, remote refunds, public-chain writes, scheduler, fleet
  coordinator, distributed budget service, or exactly-once guarantee is added.
