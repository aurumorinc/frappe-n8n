# 0003. Decouple Playbook Trigger Execution via Native Frappe Whitelisted Method Overrides

- **Status**: Accepted
- **Date**: 2026-08-01
- **Deciders**: Architecture Team, Core Maintainers

## Context and Problem Statement

Previously, `frappe_playbook` contained hardcoded provider conditionals (`if provider == "n8n"`) and explicitly enqueued provider-specific background job paths (`frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_execution`). This created tight coupling between the core provider-agnostic engine (`frappe_playbook`) and specific provider extension apps (`frappe_n8n`), violating the Single Responsibility and Dependency Inversion Principles.

## Decision Drivers

- Maintain complete separation of concerns between core playbook orchestration (`frappe_playbook`) and provider plugins (`frappe_n8n`).
- Eliminate hardcoded provider string checks and explicit package path imports inside core `frappe_playbook`.
- Enable seamless plug-and-play integration for new provider plugins via standard Frappe framework conventions.
- Ensure all queued `Playbook Execution` records trigger background jobs consistently.

## Considered Options

1. Keep hardcoded `if provider == "n8n"` checks inside core `frappe_playbook`.
2. Implement custom dynamic hook registration dictionaries (`playbook_execution_triggers`).
3. Define `@frappe.whitelist()` stub methods in `frappe_playbook` and override them in provider plugins (`frappe_n8n/hooks.py`) using native `override_whitelisted_methods`.

## Decision Outcome

Option 3: Core `frappe_playbook` exposes a base `@frappe.whitelist()` stub `trigger_execution()` method and enqueues `"frappe_playbook.playbook.doctype.playbook_execution.playbook_execution.trigger_execution"`. `frappe_n8n` maps this whitelisted method to its implementation via `override_whitelisted_methods` in `hooks.py`.

### Consequences

#### Positive
- **Zero Core Coupling**: `frappe_playbook` contains no imports or references to `frappe_n8n`.
- **Native Frappe Idiom**: Uses Frappe's standard `override_whitelisted_methods` hook mechanism without custom registration logic.
- **Extensible**: New provider apps simply register their override in `hooks.py`.
- **Database Consistency**: A migration patch (`enqueue_trigger_executions.py`) ensures queued executions missing an active `FS Job` are enqueued safely.

#### Negative
- Provider plugins must ensure `override_whitelisted_methods` and `controller_events` entries are declared in `hooks.py`.
