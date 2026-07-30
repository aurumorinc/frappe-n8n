# 05 Building Block View

This chapter provides a static breakdown of the system into physical containers and logical components.

## C2 Container Level

The container topology illustrates the physical distribution across WSGI web processes, background workers, database storage, and external services:

[C2 Container Model](../c4/02-container.md)

## C3 Component Level

The component view details all DocTypes, custom fields, helper modules, and API client components:

[C3 Component Model](../c4/03-component.md)

## Component Specifications

### 1. `n8n Settings` (`frappe_n8n.n8n.doctype.n8n_settings.n8n_settings`)
- **Type**: Single DocType.
- **Responsibilities**: Stores `base_url`, `api_key`, `enabled`, `status`, `webhook_security`, `webhook_credential_id`, and `project_id`. Validates connection on save and enqueues credential and workflow migration tasks.

### 2. `N8nClient` (`frappe_n8n.integrations.n8n.N8nClient`)
- **Type**: Python REST API Client class.
- **Responsibilities**: Wraps HTTP requests (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) to n8n endpoints (`/api/v1/projects`, `/api/v1/credentials`, `/api/v1/workflows`, `/api/v1/executions`, `/webhook/*`, `/webhook-test/*`). Handles error translation and status checks.

### 3. `n8n Integration Module` (`frappe_n8n.integrations.n8n`)
- **Type**: Helper Functions Module.
- **Responsibilities**: Exposes functional integration methods (`update_credential`, `rotate_credentials`, `create_workflow`, `move_workflow`, `enable_workflow`, `disable_workflow`, `delete_workflow`, `retrieve_workflow`, `trigger_test_execution`, `trigger_execution`, `stop_execution`, `resume_execution`).

### 4. `Playbook Callback Controller` (`frappe_n8n.playbook_execution`)
- **Type**: Public Whitelisted Controller (`@frappe.whitelist(allow_guest=True)`).
- **Responsibilities**: Receives incoming execution status webhooks from n8n, strips disallowed administrative fields (`DISALLOWED_FIELDS`), creates or updates `Playbook Execution` records, and handles test execution evaluation without DB persistence.
