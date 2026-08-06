# C3 Component ERD

The C3 Component view details all internal DocTypes, Custom Fields, Python classes, integration modules, and data model attributes belonging to `frappe_n8n`.

```mermaid
erDiagram
    "n8n Settings" ||--|| "Playbook Provider" : "syncs enabled status"
    "Playbook Provider" ||--o{ "Playbook" : "manages provider workflows"
    "Playbook" ||--o{ "Playbook Execution" : "spawns executions"
    "Playbook" ||--o{ "Playbook Node" : "contains child nodes"
    "Playbook Execution" ||--o{ "ToDo" : "linked to manual task completion"
    "Custom Field" ||--o{ "Playbook" : "extends Playbook with n8n_workflow_id & n8n_webhook_url"
    "Custom Field" ||--o{ "Playbook Execution" : "extends Playbook Execution with n8n_execution_id"
    "n8n Integration Module" ||--|| "N8nClient" : "instantiates for REST API & Webhook calls"
    "n8n Settings" ||--|| "n8n Integration Module" : "provides configuration"
    "Playbook Execution Callback Controller" ||--|| "Playbook Execution" : "creates or updates doc from webhook payload"

    "n8n Settings" {
        string name PK "n8n Settings"
        string base_url "n8n Server URL"
        string api_key "n8n API Key (Password)"
        boolean enabled "Enable Integration"
        string status "Disabled | Authorized | Unauthorized"
        string webhook_secret "32-char Webhook Token (Password)"
        string webhook_credential_id "n8n Credential ID"
        string project_id "n8n Project ID"
    }

    "Playbook Provider" {
        string name PK "n8n"
        string provider_name "n8n"
        boolean enabled "Provider Status"
    }

    "Playbook" {
        string name PK
        string playbook_name "Playbook Name"
        string provider "n8n"
        boolean enabled "Active Status"
        string document_type "Target DocType"
        string playbook_data "JSON graph data"
        string n8n_workflow_id FK "Custom Field: n8n Workflow ID"
        string n8n_webhook_url "Custom Field: n8n Webhook URL"
    }

    "Playbook Node" {
        string name PK
        string parent FK "Playbook"
        string node_name "Node Name"
        string node_type "Node Type"
        boolean disabled "Node Disabled"
        boolean retry_on_fail "Retry on Failure"
        string on_error "Error Handling Rule"
        string n8n_node_id "n8n Node ID"
        string n8n_webhook_id "n8n Webhook ID"
    }

    "Playbook Execution" {
        string name PK
        string playbook FK "Playbook"
        string reference_doctype "Reference DocType"
        string reference_name "Reference Doc Name"
        string status "queued | running | completed | failed | canceled | waiting | error"
        string execution_data "JSON Execution Payload"
        string n8n_execution_id "Custom Field: n8n Execution ID"
    }

    "ToDo" {
        string name PK
        string status "Open | Closed"
        string playbook_execution FK "Playbook Execution"
        string callback_url "n8n Resume Callback URL"
        string response_body "JSON Response Payload"
    }

    "Custom Field" {
        string name PK
        string dt "Playbook | Playbook Execution"
        string fieldname "n8n_workflow_id | n8n_webhook_url | n8n_execution_id"
        string fieldtype "Data"
        boolean read_only "Read Only Flag"
    }

    "N8nClient" {
        string base_url "Normalized Base URL"
        string api_key "API Key"
        dict headers "X-N8N-API-KEY and Content-Type headers"
    }

    "n8n Integration Module" {
        function get_n8n_config "Fetch merged configuration"
        function update_credential "Create or update n8n credential"
        function rotate_credentials "Generate and sync new webhook security token"
        function create_workflow "Create workflow in n8n and store ID"
        function move_workflow "Transfer workflow to target n8n project"
        function enable_workflow "Activate n8n workflow"
        function disable_workflow "Deactivate n8n workflow"
        function delete_workflow "Delete n8n workflow"
        function trigger_test_execution "POST test event to n8n webhook-test"
        function trigger_execution "POST live event to n8n webhook"
        function stop_execution "POST stop request to n8n execution"
        function resume_execution "POST response payload to n8n wait callback URL"
    }

    "Playbook Execution Callback Controller" {
        function callback "Whitelisted endpoint receiving n8n callbacks"
        function _apply_payload_to_execution_doc "Sanitize and map payload fields"
    }
```

## Component Details

### DocTypes
1. **`n8n Settings`**: Single DocType holding server URL, API key, authorization status, webhook security token, credential ID, and project ID.
2. **`Playbook Provider`**: Provider registration DocType in `frappe_playbook` with `name="n8n"`.
3. **`Playbook`**: Playbook definition DocType extended with `n8n_workflow_id` and `n8n_webhook_url`.
4. **`Playbook Node`**: Child table on `Playbook` capturing n8n node mappings and webhook IDs.
5. **`Playbook Execution`**: Execution instance DocType tracking status, payload, and `n8n_execution_id`.
6. **`ToDo`**: Standard Frappe task DocType hooked to resume waiting playbook executions upon task completion.

### Fixture Definitions
- **`Custom Field`**: Custom field fixtures exported in `frappe_n8n/fixtures/custom_field.json` attaching `n8n_workflow_id` and `n8n_webhook_url` to `Playbook` and `n8n_execution_id` to `Playbook Execution`.

### Python Modules & Classes
- **`frappe_n8n.integrations.n8n.N8nClient`**: HTTP client wrapping n8n REST API endpoints using `requests`.
- **`frappe_n8n.integrations.n8n`**: Main integration module containing workflow, credential, and execution helper functions.
- **`frappe_n8n.playbook_execution`**: Callback handler module containing the `@frappe.whitelist(allow_guest=True)` function `callback`.
