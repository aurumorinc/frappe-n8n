# 0002. Cascading Prerequisite Verification and In-Flight Asset Synchronization via Event Bus

- **Status**: Updated
- **Date**: 2026-07-30 (Updated 2026-08-15)
- **Deciders**: Architecture Team, Core Maintainers

## Context and Problem Statement

When triggering a `Playbook Execution` in `frappe_n8n`, execution prerequisites belong to a cascading hierarchy: `n8n Settings` (Authorized) -> `Playbook Provider` (Enabled) -> `Playbook` (Enabled) -> Asset Population (`n8n_workflow_id`, `webhook_id`). Previously, `trigger_execution` attempted to suspend execution jobs via `wait_for_event` for settings authorization or playbook enablement, and issued synchronous `get_workflow` and `activate_workflow` REST API calls on every execution. This caused unnecessary delays and redundant API overhead.

## Decision Drivers

- Enforce cascading prerequisite constraints at document lifecycle boundaries (`validate`, `on_update`).
- Fail fast immediately during execution triggering if `n8n Settings` is unauthorized or `Playbook` is disabled (zero event waits for administrative settings/status).
- Eliminate redundant synchronous REST API calls (`get_workflow`, `activate_workflow`) during execution triggering.
- Retain `frappe_controller` event bus waiting (`wait_for_event`) ONLY for in-flight async asset creation completion (`n8n_workflow_id`, `webhook_id`).

## Decision Outcome

Option 3 (Refined): Implement cascading validation hooks across `Playbook`, `Playbook Provider`, and `n8n Settings`. In `trigger_execution`, fail fast on unauthorized settings or disabled playbooks, and wait only on `n8n_workflow_id` or `webhook_id` when asset creation is in-flight.

### Consequences

#### Positive
- **Performance**: Eliminates synchronous GET/POST HTTP REST overhead per execution trigger.
- **Fail-Fast Predictability**: Execution background jobs fail fast immediately if settings or playbooks are disabled/unauthorized rather than lingering suspended.
- **Cascading Integrity**: Disabling `n8n Settings` or `Playbook Provider` automatically cascades `enabled = 0` to child `Playbook` documents.
- **In-Flight Asset Synchronization**: Retains event bus waiting for async workflow or webhook ID generation without dropping execution events.

#### Negative
- Disabling settings or provider causes a cascading update across all associated playbooks in MariaDB/PostgreSQL.
