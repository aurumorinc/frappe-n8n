# 05: Playbook Execution Lifecycle

This workflow models the execution lifecycle including live execution triggering, dependency synchronization (waiting for authorization, workflow ID, activation, and webhook ID), cancellation/stopping, debug URL retrieval, and replaying.

```mermaid
flowchart TD
    Start([Playbook Execution Event / Action]) --> ActionType{Action Type}
    
    ActionType -- trigger_execution --> CheckQueued{status == 'queued'?}
    CheckQueued -- No --> End([End Execution Lifecycle Workflow])
    CheckQueued -- Yes --> CheckSettingsAuth{n8n Settings Authorized?}
    
    CheckSettingsAuth -- No --> WaitSettingsAuth["frappe_controller wait_for_event('doc:n8n Settings:authorized')"]
    WaitSettingsAuth --> CheckSettingsAuth2{n8n Settings Authorized?}
    CheckSettingsAuth2 -- No --> SetFailedAuth[Set Playbook Execution status = 'failed' & save doc] --> End
    CheckSettingsAuth2 -- Yes --> CheckWfId
    CheckSettingsAuth -- Yes --> CheckWfId{n8n_workflow_id present?}
    
    CheckWfId -- No --> CreateWf["Call create_workflow(playbook_name)"]
    CreateWf --> WaitWfId["frappe_controller wait_for_event('doc:Playbook:{playbook}:n8n_workflow_id')"]
    WaitWfId --> CheckWfId2{n8n_workflow_id present?}
    CheckWfId2 -- No --> SetFailedWf[Set Playbook Execution status = 'failed' & save doc] --> End
    CheckWfId2 -- Yes --> CheckPbEnabled
    CheckWfId -- Yes --> CheckPbEnabled{Playbook enabled?}
    
    CheckPbEnabled -- No --> WaitPbEnabled["frappe_controller wait_for_event('doc:Playbook:{playbook}:enabled')"]
    WaitPbEnabled --> CheckPbEnabled2{Playbook enabled?}
    CheckPbEnabled2 -- No --> SetFailedDisabled[Set Playbook Execution status = 'failed' & save doc] --> End
    CheckPbEnabled2 -- Yes --> ExtractPayload
    CheckPbEnabled -- Yes --> ExtractPayload[Parse execution_data JSON]
    
    ExtractPayload --> ResolveWebhook[Extract webhook_id from nodes or playbook_data]
    ResolveWebhook --> HasWebhook{webhook_id found?}
    
    HasWebhook -- No --> WaitWebhook["frappe_controller wait_for_event('doc:Playbook:{playbook}:webhook_id')"]
    WaitWebhook --> ResolveWebhook2[Reload playbook & re-extract webhook_id]
    ResolveWebhook2 --> HasWebhook2{webhook_id found?}
    HasWebhook2 -- No --> LogErr[Log 'No webhook ID found for execution after wait'] --> SetFailedWebhook[Set Playbook Execution status = 'failed' & save doc] --> End
    
    HasWebhook2 -- Yes --> TriggerApi["n8n Webhook POST /webhook/{webhook_id}"]
    HasWebhook -- Yes --> TriggerApi
    TriggerApi --> TriggerSuccess{Trigger succeeded?}
    TriggerSuccess -- Yes --> End
    TriggerSuccess -- No --> SetFailedApi[Set Playbook Execution status = 'failed' & save doc] --> End
    
    ActionType -- on_update --> CheckCanceled{status changed to 'canceled'?}
    CheckCanceled -- No --> End
    CheckCanceled -- Yes --> CheckProv{Playbook provider == 'n8n'?}
    CheckProv -- Yes --> CheckExecId{n8n_execution_id present?}
    CheckProv -- No --> End
    CheckExecId -- Yes --> EnqStop["Enqueue stop_execution in Redis Queue (high)"]
    EnqStop --> WorkerStop["Worker FS calls n8n API POST /api/v1/executions/{id}/stop"] --> End
    CheckExecId -- No --> End
    
    ActionType -- get_debug_url --> CheckExecIdDebug{n8n_execution_id present?}
    CheckExecIdDebug -- No --> ReturnNone([Return None])
    CheckExecIdDebug -- Yes --> ReadBase[Read n8n_base_url & n8n_workflow_id]
    ReadBase --> FormatDebug["Construct {base_url}/workflow/{workflow_id}/debug/{n8n_execution_id}"]
    FormatDebug --> ReturnDebug([Return debug URL string])
    
    ActionType -- replay --> CheckFinished{status in success/failed/error/canceled?}
    CheckFinished -- No --> ThrowReplayErr[Throw ValidationError: Replay disallowed in active status] --> End
    CheckFinished -- Yes --> SetQueued[Set status = 'queued' & save doc]
    SetQueued --> ReadExecData[Parse execution_data JSON]
    ReadExecData --> CallTrigger["Call integration_trigger_execution"] --> End
```
