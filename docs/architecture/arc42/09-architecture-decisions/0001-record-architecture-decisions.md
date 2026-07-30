# 0001. Adopt Single-File REST API Client & Event-Driven Synchronization for frappe_n8n

- **Status**: Accepted
- **Date**: 2026-05-22
- **Deciders**: Architecture Team, Core Maintainers

## Context and Problem Statement

`frappe_n8n` requires a robust, maintainable strategy for connecting Frappe Bench applications (`frappe_playbook`) to an external n8n automation engine over HTTP REST APIs and Webhooks. The system must support asynchronous workflow creation, credential management, execution triggering, test execution, cancellation, and task resumption without causing race conditions or blocking WSGI web workers.

## Decision Drivers

- Clean decoupling between Frappe DocTypes and external n8n HTTP endpoints.
- Non-blocking execution of HTTP calls during administrative actions.
- Automatic recovery from deleted or desynchronized remote workflows (404 auto-healing).
- Strict security for incoming webhook callbacks.

## Considered Options

1. Inline HTTP requests inside DocType `on_update` hooks.
2. Direct synchronous execution triggering without event bus coordination.
3. Encapsulated `N8nClient` class + Redis Queue background workers + `frappe_controller` event bus coordination.

## Decision Outcome

Option 3: Adopt `N8nClient` + Redis Queue background jobs + `frappe_controller` event bus.

### Consequences

#### Positive
- **Decoupling**: `N8nClient` centralizes all header, URL, timeout, and HTTP error handling.
- **Asynchronous Execution**: Operations like workflow creation, project transfer, and credential updates execute in Redis Queue (`Worker FS`), preserving UI responsiveness.
- **Race Condition Prevention**: `frappe_controller.wait_for_event` ensures jobs wait for prerequisite states (e.g. `doc:n8n Settings:authorized`) before failing.
- **Resilience**: 404 error handling automatically recreates desynchronized n8n resources.

#### Negative
- Slight operational complexity due to background job queue dependencies (`Redis Queue` and `Worker FS` must be running).
