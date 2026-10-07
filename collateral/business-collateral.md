# Agent Control Plane — Business Collateral

## 1. Executive Summary

A Python reference implementation for bounded agent authorization, effect-time revalidation and persistent runtime records. It connects declared actions, independently resolved authority, execution attempts and reconciliation without treating an earlier decision as a permanent credential.

## 2. The Business Problem

Organizations need to distinguish what an agent proposed from what policy allowed and what a destination actually did. A cached approval or fluent explanation cannot answer whether authority, evidence and approvals were still valid when an effect was attempted.

## 3. The Component in One View

| Capability | Practical role |
|---|---|
| Bounded authorization | Evaluate Manifest-bound proposals using the trusted Authority Context resolver and explicit policy. |
| Effect-time checks | Revalidate authorization-critical inputs before the supported execution path reaches a destination. |
| Lifecycle records | Keep decisions, attempts, observations and reconciliation distinguishable, including unknown acknowledgements. |
| Persistent record transactions | Reload and append under a stable Linux sidecar flock with atomic replacement and explicit persistence failures. |
| Developer tools | Use run validation, policy examples, replay export, redaction and integrity helpers with their documented assurance limits. |

## 4. Who Should Evaluate It

Engineers can inspect the reference contracts and examples; enterprise architecture, security and governance reviewers can examine the boundary and evidence. Evaluate this component for its named responsibility rather than as a complete governance platform.

## 5. A Bounded Workflow

A synthetic refund is proposed under a bounded grant. The controller records its decision, rechecks current authority at effect time and invokes the constrained adapter. After a timeout, reconciliation concerns the original effect. Fresh observed absence does not authorize a replacement; accepted applied evidence can resolve delivery while preserving the interrupted acknowledgement history.

This is a reference use case. Adopting the format or running the example does not establish a production deployment, institutional acceptance or measured business benefit.

## 6. Relationship to the Stack

This component contributes **evaluate proposals against authority and preserve the decision record**. The [Cognous Open Control Stack](https://github.com/cogno-us/cognous-open-control-stack) connects declared proposals, independent authority, constrained execution and retained review evidence. Components remain separately owned and versioned; the [selected lock](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/component-lock.json) determines which revisions participate in the supported integration.

A valid signature, chain inclusion, message receipt, reasoning instruction or evidence-package digest does not authorize execution. Institutional authority must be supplied and evaluated through the appropriate trusted boundary.

## 7. What the Evidence Supports

The selected persistence repair is `248d899634d9db3518e831bc7ab568a48733f825`. The accepted hub generation includes the repair and compatible consumers. Twenty upstream persistence qualification cases ran in each release repetition; historical record-loss results at the older pin remain preserved, not rewritten.

The [accepted hub evidence](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/examples/control-plane-store-adoption/qualification-summary.json) supports bounded synthetic integration at its exact pins. Aggregate test totals do not establish deployment benefit, compliance or independent real-world verification. The [support ledger](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/release-status.md) distinguishes the standard reference, separate protected-worker campaign and unqualified production work.

## 8. What It Does Not Establish

The repaired store supports cooperating writers on documented local Linux filesystems with shared canonical-path assumptions. Individual record transactions are protected; the entire decide/execute/reconcile workflow is not atomic. Production resolver authentication, distributed budgets, remote finality and exactly-once delivery are not established.

## 9. Evaluation Questions

- Which exact input, output and source revision will the receiving system consume?
- Who supplies trusted authority or evidence, and which assumptions remain outside this component?
- Can a reviewer trace the result to retained sources, including rejected or missing information?
- Which documented checks were actually executed in the intended environment?
- What deployment-specific work is required before relying on the result?

## 10. Why Open Reference Material Matters

Public formats, source, examples and evidence allow reviewers to inspect the claimed boundary and reproduce its checks. They also expose what has not been tested. Openness supports review; it does not substitute for independent assurance or operating responsibility.

## 11. Practical Next Step

Follow the [README](../README.md) and select one bounded use case. Inspect its inputs and expected outputs, reproduce the documented checks where prerequisites are available, and record failures and unresolved assumptions alongside passes. Use the [one-page overview](one-page-overview.md) for initial stakeholder orientation.

## 12. Status and Attribution

This collateral summarizes merged public material at repository `248d899634d9db3518e831bc7ab568a48733f825` and the accepted hub baseline `5737267d94d2b445735c95e8480a31de73a2abe8`. It does not anticipate pending branches. The protected-worker result applies only to its recorded Linux/bubblewrap fixture; live OpenShell and logical-intent prevention are not hub-supported at this snapshot.

[Cognous](https://cogno.us) · [Source repository](https://github.com/cogno-us/cognous-control-plane) · [Stack responsibilities](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/architecture.md). Existing licenses and third-party notices remain controlling.
