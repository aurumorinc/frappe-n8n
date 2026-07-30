# 10 Quality Requirements

This chapter details concrete quality scenarios and non-functional requirements for `frappe_n8n`.

## Quality Tree

- **Reliability**
  - Robust error handling for HTTP failures.
  - Automatic 404 resource recovery and re-creation.
  - Non-destructive test callbacks (`test-*`) that avoid DB mutation.
- **Security**
  - Encrypted storage for API keys and secrets via Frappe `Password` fieldtype.
  - High-entropy 32-char webhook security token.
  - Strict input sanitization blocking `DISALLOWED_FIELDS` in callbacks.
- **Performance**
  - Offloading REST API calls to asynchronous Redis Queue workers.
  - 10-second request timeout on external HTTP calls to prevent socket exhaustion.
- **Maintainability**
  - 100% unit test coverage for payload sanitization and hook configurations.

## Quality Scenarios

| Quality Characteristic | Stimulus | System Behavior / Reaction | Target Metric |
|-----------------------|----------|----------------------------|---------------|
| **Reliability** | n8n returns HTTP 404 when activating a workflow. | `frappe_n8n` catches `N8nNotFoundError`, clears `n8n_workflow_id`, and calls `create_workflow` to re-provision the workflow. | Automatic recovery within 1 retry cycle. |
| **Security** | Malicious actor sends a callback payload containing `doctype` or `owner` field overrides. | `_apply_payload_to_execution_doc` filters out all keys in `DISALLOWED_FIELDS`. | Zero unauthorized field mutation. |
| **Performance** | Administrator saves `n8n Settings` with 100+ associated playbooks. | `n8n_settings.on_update` enqueues individual `move_workflow` background jobs in Redis Queue. | Web worker response time < 200ms. |
| **Resilience** | Execution trigger is invoked before `n8n Settings` authorization completes. | `trigger_execution` calls `wait_for_event("doc:n8n Settings:authorized")` and resumes execution seamlessly upon emission. | Zero dropped execution events during initialization. |
