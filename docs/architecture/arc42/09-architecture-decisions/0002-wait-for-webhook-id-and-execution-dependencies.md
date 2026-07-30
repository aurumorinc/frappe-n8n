# 0002. Asynchronous Execution Dependency Synchronization via Event Bus

- **Status**: Accepted
- **Date**: 2026-07-30
- **Deciders**: Architecture Team, Core Maintainers

## Context and Problem Statement

When triggering a `Playbook Execution` in `frappe_n8n`, required execution prerequisites—such as `n8n Settings` authorization status, Playbook `n8n_workflow_id`, Playbook `enabled` state, and `webhook_id`—may not be immediately available on the local document or remote engine due to asynchronous background provisioning or concurrent schema synchronization. Previously, if `webhook_id` was unpopulated, the execution handler logged "No webhook ID found" and terminated, causing dropped execution events.

## Decision Drivers

- Guarantee zero dropped execution events during initialization, provisioning, or concurrent playbook sync.
- Prevent race conditions when triggering executions before webhook IDs or workflow IDs are written to the database.
- Utilize standard `frappe_controller` event bus mechanisms (`wait_for_event` and `emit_event`) across background worker jobs (`Worker FS`).
- Enforce clean exception handling and explicit transition to `status = 'failed'` if dependencies cannot be satisfied post-wait.

## Considered Options

1. Immediately log error and terminate execution when any dependency (`webhook_id`, `n8n_workflow_id`, `enabled`, `authorized`) is missing.
2. Implement custom polling loops with `time.sleep()` inside background workers.
3. Suspend background job execution using `frappe_controller.utils.controller.wait_for_event` and emit targeted document events (`doc:Playbook:{name}:webhook_id`, `doc:Playbook:{name}:n8n_workflow_id`, `doc:Playbook:{name}:enabled`, `doc:n8n Settings:authorized`) when dependencies are populated.

## Decision Outcome

Option 3: Suspend execution jobs via `frappe_controller.utils.controller.wait_for_event` and emit targeted document events upon dependency population.

### Consequences

#### Positive
- **Resilience**: Asynchronous background jobs suspend execution gracefully when `webhook_id` or `n8n_workflow_id` is missing and resume immediately upon population via `emit_event`.
- **Zero Dropped Executions**: Prevents premature execution failures during playbook provisioning or setting authorization.
- **Traceability**: If dependencies remain unsatisfied after the event wait timeout, the execution document explicitly transitions to `status = 'failed'` with actionable diagnostics in system error logs.

#### Negative
- Execution background jobs may remain suspended in Redis Queue until the prerequisite event is emitted or the event wait times out.
