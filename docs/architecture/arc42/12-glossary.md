# 12 Glossary

Alphabetical dictionary of domain and technical terms used in `frappe_n8n` documentation.

| Term | Definition |
|------|------------|
| **`frappe_controller`** | Auxiliary Frappe application providing event emission and event wait utilities (`frappe_controller.utils.controller`). |
| **`frappe_playbook`** | Core workflow management application in Frappe Bench defining `Playbook`, `Playbook Execution`, and `Playbook Provider` DocTypes. |
| **`N8nClient`** | Python wrapper class (`frappe_n8n.integrations.n8n.N8nClient`) communicating with n8n REST API v1. |
| **`n8n Settings`** | Single DocType in `frappe_n8n` storing API credentials, server URL, authorization status, and webhook security tokens. |
| **`Playbook`** | DocType representing a workflow definition, linked to a target DocType and provider. Extended in `frappe_n8n` with `n8n_workflow_id` and `n8n_webhook_url`. |
| **`Playbook Execution`** | DocType representing an instance execution of a Playbook, tracking status and payload data. Extended with `n8n_execution_id`. |
| **`Playbook Node`** | Child table on `Playbook` recording individual workflow nodes, types, and n8n webhook IDs. |
| **`Playbook Provider`** | Registration DocType for workflow providers (`name="n8n"`). |
| **`webhook_secret`** | 32-character high-entropy secret token generated in `frappe_n8n` and provisioned as an HTTP Header credential in n8n (`crm_n8n_api_key`). |
