# Cognous Control Plane — One-Page Overview

## Purpose

A Python reference implementation for bounded agent authorization, effect-time revalidation and persistent runtime records. It connects declared actions, independently resolved authority, execution attempts and reconciliation without treating an earlier decision as a permanent credential.

## Problem

Organizations need to distinguish what an agent proposed from what policy allowed and what a destination actually did. A cached approval or fluent explanation cannot answer whether authority, evidence and approvals were still valid when an effect was attempted.

## What It Provides

- **Bounded authorization:** Evaluate Manifest-bound proposals using the trusted Authority Context resolver and explicit policy.
- **Effect-time checks:** Revalidate authorization-critical inputs before the supported execution path reaches a destination.
- **Lifecycle records:** Keep decisions, attempts, observations and reconciliation distinguishable, including unknown acknowledgements.
- **Persistent record transactions:** Reload and append under a stable Linux sidecar flock with atomic replacement and explicit persistence failures.

## Where It Fits

A synthetic refund is proposed under a bounded grant. The controller records its decision, rechecks current authority at effect time and invokes the constrained adapter. After a timeout, reconciliation concerns the original effect. Fresh observed absence does not authorize a replacement; accepted applied evidence can resolve delivery while preserving the interrupted acknowledgement history.

A valid signature, chain inclusion, message receipt, reasoning instruction or evidence-package digest does not authorize execution. Institutional authority must be supplied and evaluated through the appropriate trusted boundary.

## Evidence and Limits

The [accepted hub lock](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/component-lock.json) selects this component at `248d899634d9db3518e831bc7ab568a48733f825`. Read the component's [README](../README.md) for version-specific acceptance and the [hub support ledger](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/release-status.md) for the executed scope. Component acceptance is not automatic adoption of newer revisions or production qualification.

The repaired store supports cooperating writers on documented local Linux filesystems with shared canonical-path assumptions. Individual record transactions are protected; the entire decide/execute/reconcile workflow is not atomic. Production resolver authentication, distributed budgets, remote finality and exactly-once delivery are not established.

## Practical Next Step

Choose one bounded example and follow the [README](../README.md). Compare expected and observed results and retain uncertainty. The [business collateral](business-collateral.md) supplies evaluation questions and the component's wider context.

[Cognous](https://cogno.us) · [Source](https://github.com/cogno-us/cognous-control-plane) · [All stack components](https://github.com/cogno-us/cognous-open-control-stack). Existing licenses and notices apply.
