# 08 Cross-Cutting Concepts

This chapter documents overall cross-cutting patterns, security architectures, error handling mechanisms, and persistence concepts applied across `frappe_n8n`.

## 1. Security & Authentication Architecture

- **n8n API Key Storage**: Stored as a Frappe `Password` field in `n8n Settings` (`api_key`) and retrieved securely via `settings.get_password("api_key")`.
- **Webhook Authorization Secret**: Generated as a 32-character random hash (`webhook_security`) stored as a `Password` field. Provisioned in n8n as an `httpHeaderAuth` credential (`crm_n8n_api_key`) injecting `Bearer {webhook_security}` into outgoing n8n webhooks.
- **Quarterly Automated Rotation**: Scheduled cron job (`enqueue_rotate_credentials`) automatically rotates `webhook_security` every 3 months and updates n8n credentials without downtime.
- **Payload Sanitization**: The callback endpoint (`_apply_payload_to_execution_doc`) explicitly blocks updates to administrative system fields (`DISALLOWED_FIELDS` = `{"name", "owner", "creation", "modified", "modified_by", "idx", "docstatus", "doctype", "playbook", "reference_doctype", "reference_name"}`) to prevent privilege escalation.

## 2. Event-Driven Event Bus & Synchronization (`frappe_controller`)

- Uses `frappe_controller.utils.controller` (`emit_event`, `wait_for_event`) to coordinate async operations:
  - `doc:n8n Settings:authorized`: Emitted when settings become valid to notify background tasks.
  - `n8n_credential_ready`: Emitted when `crm_n8n_api_key` credential creation/update completes in n8n.
  - `n8n_workflow_created` / `doc:Playbook:{name}:n8n_workflow_id`: Emitted when an n8n workflow is created or updated with a workflow ID. Trigger execution blocks and waits on `doc:Playbook:{name}:n8n_workflow_id` if in-flight workflow creation is pending.
  - `doc:Playbook:{name}:enabled`: Emitted when a playbook is enabled to notify listening workers.
  - `doc:Playbook:{name}:webhook_id`: Emitted when a playbook's webhook ID is populated during provider sync, workflow creation, or document save. Trigger execution blocks and waits on this event if in-flight webhook ID extraction is pending.

## 3. Resilience & Error Handling

- **Custom Exception Hierarchy**:
  - `N8nError`: Extends `requests.exceptions.HTTPError` with explicit status codes and HTTP response attributes.
  - `N8nNotFoundError`: Subclasses `N8nError` for HTTP 404 responses. Allows downstream logic to cleanly handle missing remote workflows or credentials by re-creating them on-demand.
- **404 Auto-Healing Pattern**:
  - When updating, enabling, disabling, moving, or retrieving a workflow returns 404 from n8n, `frappe_n8n` automatically clears `n8n_workflow_id` on the `Playbook` document and triggers `create_workflow` to recover gracefully.

## 4. Configuration & Flag Overrides

- Supports environment-level overrides via `frappe.conf` keys:
  - `n8n_base_url`: Overrides `base_url` in settings.
  - `n8n_api_key`: Overrides `api_key` in settings.
  - `n8n_webhook_security`: Overrides `webhook_security` in settings.
  - `n8n_project_id`: Overrides `project_id` in settings.
  - `n8n_enabled`: Overrides `enabled` state in settings.
- Uses runtime flags like `frappe.flags.in_playbook_sync` to bypass recursive change detection during schema synchronization.
