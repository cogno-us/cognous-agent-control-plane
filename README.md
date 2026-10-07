<!-- cognous-banner:start -->
```text
──────────────────────────────────────────────────
   __________  _______   ______  __  _______
  / ____/ __ \/ ____/ | / / __ \/ / / / ___/
 / /   / / / / / __/  |/ / / / / / / /\__ \
/ /___/ /_/ / /_/ / /|  / /_/ / /_/ /___/ /
\____/\____/\____/_/ |_/\____/\____//____/
               AGENT CONTROL PLANE
       g o v e r n e d   b y   d e s i g n
  github.com/cogno-us/cognous-open-control-stack
──────────────────────────────────────────────────
```
<!-- cognous-banner:end -->

# Agent Control Plane

**Evaluate proposals against authority and preserve the decision record.**

## Overview

A Python reference implementation for bounded agent authorization, effect-time revalidation and persistent runtime records. It connects declared actions, independently resolved authority, execution attempts and reconciliation without treating an earlier decision as a permanent credential.

**Implementation status:** this README describes merged public reference work. Component acceptance, selection in the hub and execution of a qualification are separate facts. The selected revision for this component is `248d899634d9db3518e831bc7ab568a48733f825`; the [hub lock](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/component-lock.json) is the source of that integration choice.

## Purpose and intended users

Organizations need to distinguish what an agent proposed from what policy allowed and what a destination actually did. A cached approval or fluent explanation cannot answer whether authority, evidence and approvals were still valid when an effect was attempted.

Engineers can inspect the reference contracts and examples; enterprise architecture, security and governance reviewers can examine the boundary and evidence. Evaluate this component for its named responsibility rather than as a complete governance platform.

## Key features

| Capability | Implemented or specified responsibility |
|---|---|
| **Bounded authorization** | Evaluate Manifest-bound proposals using the trusted Authority Context resolver and explicit policy. |
| **Effect-time checks** | Revalidate authorization-critical inputs before the supported execution path reaches a destination. |
| **Lifecycle records** | Keep decisions, attempts, observations and reconciliation distinguishable, including unknown acknowledgements. |
| **Persistent record transactions** | Reload and append under a stable Linux sidecar flock with atomic replacement and explicit persistence failures. |
| **Developer tools** | Use run validation, policy examples, replay export, redaction and integrity helpers with their documented assurance limits. |

## How it works

A synthetic refund is proposed under a bounded grant. The controller records its decision, rechecks current authority at effect time and invokes the constrained adapter. After a timeout, reconciliation concerns the original effect. Fresh observed absence does not authorize a replacement; accepted applied evidence can resolve delivery while preserving the interrupted acknowledgement history.

A valid signature, chain inclusion, message receipt, reasoning instruction or evidence-package digest does not authorize execution. Institutional authority must be supplied and evaluated through the appropriate trusted boundary.

## Getting started

From a fresh repository checkout, use Python 3.11+ and an activated virtual environment. Install only into that environment. Package installation needs network access; the commands below exercise local reference tooling. For the full selected integration, use the [hub quickstart](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/quickstart.md), whose runner supplies exact producer checkouts and test wiring.

```bash
python -m pip install -e ".[dev]"
acp --help
acp validate-run examples/sample_run_record.json
python examples/policy_config_demo.py
```

## Evidence and supported scope

The selected persistence repair is `248d899634d9db3518e831bc7ab568a48733f825`. The accepted hub generation includes the repair and compatible consumers. Twenty upstream persistence qualification cases ran in each release repetition; historical record-loss results at the older pin remain preserved, not rewritten.

The accepted [hub persistence-generation evidence](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/examples/control-plane-store-adoption/qualification-summary.json) records 915 Python tests in each of two repetitions, 35 matrix entries satisfying their gates and 120 separate mocked OpenShell tests. Those are aggregate hub results, not a per-component test count or a claim of production readiness. Optional behavioral layers receive static checks only. The [support ledger](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/release-status.md) separates implementation, execution and adoption.

## Limitations and deployment decisions

The repaired store supports cooperating writers on documented local Linux filesystems with shared canonical-path assumptions. Individual record transactions are protected; the entire decide/execute/reconcile workflow is not atomic. Production resolver authentication, distributed budgets, remote finality and exactly-once delivery are not established.

Review original artifacts and their exact source revisions before extending a claim to a new environment. New dependencies, authority sources, destinations or enforcement mechanisms need their own compatibility and qualification. A passing reference case is not a certification of an enterprise deployment.

## Repository guide

Use these sources for details; their historical checkpoints retain the status and scope of the work they recorded:

- [docs/bounded_authorization_effect.md](docs/bounded_authorization_effect.md)
- [docs/record-store-persistence.md](docs/record-store-persistence.md)
- [docs/workstreams/store-concurrency-checkpoint.md](docs/workstreams/store-concurrency-checkpoint.md)
- [docs/threat-model-lite.md](docs/threat-model-lite.md)

For a nontechnical introduction, read the [business overview](collateral/business-collateral.md) and [one-page overview](collateral/one-page-overview.md). Both describe this component's role and evidence limits, not additional runtime features.

## Contributing and attribution

[Contribution guidance](CONTRIBUTING.md) describes review and validation expectations. Keep evidence-linked claims, preserve historical records and separate proposed features from accepted implementation.

See [LICENSE](LICENSE) and [attribution](NOTICE) for the existing terms and third-party scope. Developed by [Cognous](https://cogno.us); no licensing change is part of this documentation update.

---

## Cognous stack components

[Stack hub](https://github.com/cogno-us/cognous-open-control-stack) · [Selected pins](https://github.com/cogno-us/cognous-open-control-stack/blob/main/component-lock.json) · [Evidence and limits](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/release-status.md)

Component links are navigation, not a requirement to install every component. The hub lock determines its supported integration.

| Component | Responsibility |
|---|---|
| [Agent Action Manifest](https://github.com/cogno-us/cognous-agent-action-manifest) | Declare the action before evaluating permission |
| [Agent Replay Bundle](https://github.com/cogno-us/cognous-agent-replay-bundle) | Reconstruct what the retained records support |
| [Agent Governance Evidence Pack](https://github.com/cogno-us/cognous-agent-governance-evidence-pack) | Turn traceable runtime records into reviewable governance evidence |
| [Open Decision Evidence Standard](https://github.com/cogno-us/open-decision-evidence-standard) | Portable decision evidence across system and organizational boundaries |
| [Alvorada Experimental Workbench](https://github.com/cogno-us/alvorada) | Governed exchange and continuity for a bounded synthetic workflow |
| [Moltbot Safe](https://github.com/cogno-us/moltbot-safe) | Constrained execution beneath independent current authorization |
| [BitRep](https://github.com/cogno-us/bitrep) | Verify issuer signatures under explicit trust assumptions |
| [The Index](https://github.com/cogno-us/the-index) | A local blockchain reference for claims, evidence commitments and lifecycle history |
| [Portable Reasoning Protocol v1.0](https://github.com/cogno-us/portable-reasoning-protocol) | Portable instructions for evidence-bounded reasoning |
| [Research Intelligence Protocol v1.0](https://github.com/cogno-us/research-intelligence-protocol) | Disciplined discovery and cross-domain abstraction, kept separate |
| [TFA Protocol (S43)](https://github.com/cogno-us/truth-freedom-agency-protocol) | Truth · Freedom · Agency |
| [Constitutional Governance for Institutions](https://github.com/cogno-us/constitutional-governance-for-institutions) | Alvorada: authority, challenge and correction for institutions |
