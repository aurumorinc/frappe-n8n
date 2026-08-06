# ADR 0001: Adopt Single-File REST API Client and Event-Driven Synchronization

## Status
Accepted

## Date
2026-05-22

## Context
`frappe_n8n` requires a robust, maintainable strategy for connecting Frappe Bench applications (`frappe_playbook`) to an external n8n automation engine over HTTP REST APIs and Webhooks. The system must support asynchronous workflow creation, credential management, execution triggering, test execution, cancellation, and task resumption without causing race conditions or blocking WSGI web workers.

Previously, the `frappe_n8n` integration relied on Frappe's `override_whitelisted_methods` to hijack the native execution path of `frappe_playbook`. This created obscure execution traces, tightly coupled the two applications, and caused background jobs to run under misleading method names.

Decision drivers include clean decoupling between Frappe DocTypes and external n8n HTTP endpoints, non-blocking execution of HTTP calls during administrative actions, automatic recovery from deleted or desynchronized remote workflows (404 auto-healing), and strict security for incoming webhook callbacks.

## Decision
We adopted an encapsulated `N8nClient` class alongside Redis Queue background workers and `frappe_controller` event bus coordination. 

Additionally, we removed the `trigger_execution` and `replay` overrides. We now use standard Frappe `doc_events` to subscribe to the `Playbook Execution` document's `after_insert` hook. Upon insertion, `frappe_n8n` inspects the execution's provider. If it is `"n8n"`, it explicitly enqueues its own `trigger_execution` logic into the background queue.

## Consequences
### Positive
- `N8nClient` centralizes all header, URL, timeout, and HTTP error handling. Zero coupling to `frappe_playbook`'s internal execution stubs.
- Operations like workflow creation, project transfer, and credential updates execute in Redis Queue (`Worker FS`), preserving UI responsiveness.
- `frappe_controller.wait_for_event` ensures jobs wait for prerequisite states (e.g., `doc:n8n Settings:authorized`) before failing, preventing race conditions.
- 404 error handling automatically recreates desynchronized n8n resources.
- Background jobs correctly surface `frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_execution` in logs and the UI.
- Simplifies testing and debugging by relying on explicit event-driven execution (EDA) rather than complex monkey-patching.

### Negative & Risks
- Slight operational complexity due to background job queue dependencies (`Redis Queue` and `Worker FS` must be running).
- Enqueue logic must be maintained locally within `frappe_n8n`, increasing boilerplate slightly.
- Mitigation strategy: Encapsulate the checking and enqueuing logic clearly within the `frappe_n8n.n8n.doctype.playbook_execution` module.
