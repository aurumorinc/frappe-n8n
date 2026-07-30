# 06 Runtime View

This chapter documents the behavioral execution paths and event-driven workflows across `frappe_n8n`.

For full details and individual Mermaid flowchart diagrams for every trigger, see the [BPMN Workflows Directory](../bpmn/README.md).

## Summary of Trigger Workflows

1. **[01: n8n Settings Update](../bpmn/01-n8n-settings-update.md)**: Validates n8n connectivity, sets status ('Authorized'/'Unauthorized'), enqueues credential updates and workflow project transfers.
2. **[02: Playbook Document Lifecycle](../bpmn/02-playbook-lifecycle.md)**: Handles Playbook creation (`create_workflow`), activation (`enable_workflow`), deactivation (`disable_workflow`), and trash deletion (`delete_workflow`).
3. **[03: Playbook Builder URL Request](../bpmn/03-playbook-builder-url.md)**: Whitelisted method returning the n8n editor URL (`{base_url}/workflow/{n8n_workflow_id}`).
4. **[04: Playbook Test Execution](../bpmn/04-playbook-test-execution.md)**: Evaluates test documents and dispatches test payloads to `/webhook-test/{webhook_id}`.
5. **[05: Playbook Execution Lifecycle](../bpmn/05-playbook-execution-lifecycle.md)**: Dispatches live executions to `/webhook/{webhook_id}`, handles cancellations by calling `/api/v1/executions/{id}/stop`, returns debug URLs, and supports replaying.
6. **[06: ToDo Task Completion](../bpmn/06-todo-status-update.md)**: Listens for closed `ToDo` items linked to playbook executions and resumes waiting n8n execution nodes via callback URL.
7. **[07: Playbook Provider Synchronization](../bpmn/07-playbook-provider-sync.md)**: Toggles provider-wide playbook enablement and synchronizes workflow schemas from n8n into Frappe `Playbook Node` child tables.
8. **[08: External Webhook Callback](../bpmn/08-external-webhook-callback.md)**: Public endpoint receiving live and test execution state callbacks from n8n.
9. **[09: Scheduled Cron Events](../bpmn/09-scheduled-cron-events.md)**: Quarterly credential rotation (`rotate_credentials`) and periodic playbook schema synchronization.
10. **[10: App Installation](../bpmn/10-app-installation.md)**: Post-install hook initializing the `Playbook Provider` "n8n" record.
