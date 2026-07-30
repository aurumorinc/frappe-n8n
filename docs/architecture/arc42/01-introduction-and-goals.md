# 01 Introduction and Goals

`frappe_n8n` is a specialized n8n Provider Plugin for the `frappe_playbook` application within the Frappe Bench ecosystem. It seamlessly bridges Frappe Bench applications with an external n8n automation instance, enabling low-code/no-code workflow execution, automated event triggers, and bidirectional task synchronization.

## Requirements Overview

1. **n8n Connectivity & Credential Management**: Validate connections to n8n, manage `httpHeaderAuth` credentials with `Bearer` tokens, and rotate security tokens automatically.
2. **Playbook Workflow Synchronization**: Bi-directionally map Frappe `Playbook` definitions to n8n workflows, supporting activation, deactivation, project transfer, and deletion.
3. **Execution Triggering & Monitoring**: Trigger live and test executions via n8n Webhooks (`/webhook/{id}` and `/webhook-test/{id}`), receive execution callbacks, track execution status, and support execution cancellation and debugging.
4. **Human-in-the-Loop Task Resumption**: Intercept `ToDo` task status changes in Frappe and resume paused n8n execution wait nodes via callback URLs.

## Quality Goals

| Goal # | Quality Category | Description |
|--------|------------------|-------------|
| **QG-01** | Reliability | Ensure zero loss of execution state through atomic database operations and fallback error handling. |
| **QG-02** | Security | Protect webhook security tokens and API keys using encrypted password fields and header authorization. |
| **QG-03** | Interoperability | Maintain strict compatibility with `frappe_playbook` interfaces and n8n REST API schemas. |
| **QG-04** | Maintainability | Decouple n8n HTTP interactions inside a dedicated client (`N8nClient`) and integration module (`frappe_n8n.integrations.n8n`). |

## Stakeholder Matrix

| Role | Expectation |
|------|-------------|
| **System Administrator** | Simple configuration via `n8n Settings`, automatic token rotation, and robust health reporting. |
| **Workflow Designer** | Smooth experience opening n8n builder URLs, triggering test runs, and viewing node configurations. |
| **End User** | Instant task resumption upon completing assigned `ToDo` items without manual intervention. |
| **Developer / Maintainer** | Clean modular architecture adhering to Frappe hooks, controller event bus, and background jobs. |
