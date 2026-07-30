# 03 Context and Scope

This chapter defines the system context, external boundaries, and business interfaces of `frappe_n8n`.

## System Context Diagram

The structural system context is modeled in C1 System Context ERD:
[C1 System Context Model](../c4/01-context.md)

## External Interfaces

| Interface | Protocol | Direction | Description |
|-----------|----------|-----------|-------------|
| **n8n REST API** | HTTPS / REST | Outbound | Used by `N8nClient` to manage credentials (`/api/v1/credentials`), projects (`/api/v1/projects`), workflows (`/api/v1/workflows`), and executions (`/api/v1/executions`). |
| **n8n Webhook Endpoint** | HTTPS / POST | Outbound | Used by `trigger_execution` to send live workflow execution payloads to `/webhook/{webhook_id}`. |
| **n8n Webhook Test Endpoint** | HTTPS / POST | Outbound | Used by `trigger_test_execution` to send test workflow payloads to `/webhook-test/{webhook_id}`. |
| **n8n Wait Resume Callback** | HTTPS / POST | Outbound | Used by `resume_execution` to POST response payloads back to paused n8n wait nodes. |
| **Frappe Webhook Callback API** | HTTPS / POST | Inbound | Whitelisted guest endpoint `/api/method/frappe_n8n.playbook_execution.callback` receiving execution updates from n8n. |
| **Frappe Event Controller** | In-Memory / Redis | Internal | Uses `frappe_controller.utils.controller` for emitting and waiting on synchronization events (e.g. `n8n_credential_ready`, `doc:n8n Settings:authorized`). |
