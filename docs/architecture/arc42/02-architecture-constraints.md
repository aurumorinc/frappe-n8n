# 02 Architecture Constraints

This chapter documents the technical, organizational, and regulatory constraints governing the architecture of `frappe_n8n`.

## Technical Constraints

| Constraint | Category | Description |
|------------|----------|-------------|
| **Python Version** | Language Runtime | Must run on Python >= 3.14 as specified in `pyproject.toml`. |
| **Frappe Framework** | Framework | Must integrate with Frappe Bench (v16+) using standard DocType definitions, hooks, and whitelisted methods. |
| **Required Apps** | Dependency | Depends directly on `frappe_playbook` (workflow model) and `frappe_controller` (event bus). |
| **n8n REST API v1** | External System | Interoperates with n8n v1 API (`/api/v1/*`) and n8n webhook endpoints (`/webhook/*`, `/webhook-test/*`). |
| **Database Engine** | Persistence | Compatible with MariaDB or PostgreSQL via Frappe ORM (`frappe.db`). |
| **Task Queue** | Concurrency | Asynchronous operations must use Redis Queue (RQ) via `frappe.enqueue`. |

## Organizational & Operational Constraints

| Constraint | Description |
|------------|-------------|
| **Open Source Licensing** | Released under the MIT License (`license.txt`). |
| **Publisher** | Maintained by Aurumor (`hello@aurumor.com`). |
| **Stateless Callbacks** | Incoming webhook callbacks (`/api/method/frappe_n8n.playbook_execution.callback`) must support unauthenticated guest access (`allow_guest=True`) for external n8n instances while enforcing token verification. |
