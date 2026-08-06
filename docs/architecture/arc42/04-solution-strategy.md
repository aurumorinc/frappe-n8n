# 04 Solution Strategy

This chapter summarizes the fundamental architectural decisions and solution strategies behind `frappe_n8n`.

## Fundamental Strategies

1. **Provider Plugin Architecture**:
   - Extends `frappe_playbook` by providing an n8n-specific implementation of workflow creation, execution, and builder UI methods without mutating core playbook schemas.

2. **Decoupled REST API Client (`N8nClient`)**:
   - All HTTP interactions with n8n are encapsulated in `frappe_n8n.integrations.n8n.N8nClient`. The client handles authentication (`X-N8N-API-KEY`), error wrapping (`N8nError`, `N8nNotFoundError`), base URL normalization, and retry wait logic.

3. **Asynchronous Background Synchronization**:
   - Long-running operations (credential rotation, workflow creation, project transfer, workflow deletion, and playbook schema synchronization) are enqueued to Redis Queue (`Worker FS`) to prevent blocking WSGI/web request workers.

4. **Event-Driven Coordination & Cascading Verification (`frappe_controller`)**:
   - Enforces cascading validation checks (`n8n Settings` Authorized -> `Playbook Provider` Enabled -> `Playbook` Enabled). Triggering an execution fails fast if settings are unauthorized or playbooks are disabled, and uses `frappe_controller.utils.controller` (`emit_event`, `wait_for_event`) to synchronize in-flight asset creation (`doc:Playbook:{name}:n8n_workflow_id` and `doc:Playbook:{name}:webhook_id`) before HTTP dispatch.

5. **Shared Webhook Security & Credential Provisioning**:
   - Automatically generates a 32-character high-entropy secret (`webhook_secret`) and provisions an `httpHeaderAuth` credential (`crm_n8n_api_key`) inside n8n. This credential injects `Bearer {webhook_secret}` into outgoing n8n requests.

6. **Unified Webhook Callback Endpoint**:
   - Exposes a single `@frappe.whitelist(allow_guest=True)` endpoint (`frappe_n8n.playbook_execution.callback`) that dynamically distinguishes between test executions (`test-*`) and production executions, sanitizing input fields against privilege escalation.
