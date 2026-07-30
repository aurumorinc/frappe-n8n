# System Architecture Documentation: frappe_n8n

Welcome to the system architecture documentation for `frappe_n8n` (n8n Provider Plugin for Frappe Playbook).

## Architecture Structure

```text
docs/architecture/
├── README.md                           # Master Architecture Index
├── c4/                                 # C4 Model Entity Relationship Diagrams (erDiagram)
│   ├── 01-context.md                   # C1 System Context ERD
│   ├── 02-container.md                 # C2 Container ERD
│   └── 03-component.md                 # C3 Component ERD
├── bpmn/                               # Behavioral BPMN Flowcharts
│   ├── README.md                       # BPMN Workflows Catalog Index
│   ├── 01-n8n-settings-update.md
│   ├── 02-playbook-lifecycle.md
│   ├── 03-playbook-builder-url.md
│   ├── 04-playbook-test-execution.md
│   ├── 05-playbook-execution-lifecycle.md
│   ├── 06-todo-status-update.md
│   ├── 07-playbook-provider-sync.md
│   ├── 08-external-webhook-callback.md
│   ├── 09-scheduled-cron-events.md
│   └── 10-app-installation.md
└── arc42/                              # Standard arc42 Architecture Documentation
    ├── 01-introduction-and-goals.md    # Requirements & Quality Goals
    ├── 02-architecture-constraints.md # Technical & Organizational Constraints
    ├── 03-context-and-scope.md        # System Context & Interfaces
    ├── 04-solution-strategy.md        # Fundamental Strategies & Patterns
    ├── 05-building-block-view.md      # Static Building Blocks & C4 Embedding
    ├── 06-runtime-view.md             # Behavioral Workflows & BPMN Embedding
    ├── 07-deployment-view.md          # Infrastructure & Node Mapping
    ├── 08-cross-cutting-concepts.md   # Security, Event Bus, & Resilience
    ├── 09-architecture-decisions/     # Architecture Decision Records
    │   ├── 0001-record-architecture-decisions.md
    │   ├── 0002-wait-for-webhook-id-and-execution-dependencies.md
    │   └── 0003-decouple-playbook-trigger-execution-via-native-hooks.md
    ├── 10-quality-requirements.md     # Quality Scenarios & Tree
    ├── 11-risks-and-technical-debt.md # Risk Matrix & Technical Debt
    └── 12-glossary.md                 # Technical Dictionary
```

## Section Catalogs & Quick Links

### C4 ERD Models
- [C1 System Context ERD](./c4/01-context.md)
- [C2 Container ERD](./c4/02-container.md)
- [C3 Component ERD](./c4/03-component.md)

### Behavioral BPMN Flowcharts
- [BPMN Workflows Catalog](./bpmn/README.md)
- [01: n8n Settings Update](./bpmn/01-n8n-settings-update.md)
- [02: Playbook Document Lifecycle](./bpmn/02-playbook-lifecycle.md)
- [03: Playbook Builder URL Request](./bpmn/03-playbook-builder-url.md)
- [04: Playbook Test Execution](./bpmn/04-playbook-test-execution.md)
- [05: Playbook Execution Lifecycle](./bpmn/05-playbook-execution-lifecycle.md)
- [06: ToDo Task Completion](./bpmn/06-todo-status-update.md)
- [07: Playbook Provider Synchronization](./bpmn/07-playbook-provider-sync.md)
- [08: External Webhook Callback](./bpmn/08-external-webhook-callback.md)
- [09: Scheduled Cron Events](./bpmn/09-scheduled-cron-events.md)
- [10: App Installation](./bpmn/10-app-installation.md)

### arc42 Architecture Documentation
1. [01 Introduction and Goals](./arc42/01-introduction-and-goals.md)
2. [02 Architecture Constraints](./arc42/02-architecture-constraints.md)
3. [03 Context and Scope](./arc42/03-context-and-scope.md)
4. [04 Solution Strategy](./arc42/04-solution-strategy.md)
5. [05 Building Block View](./arc42/05-building-block-view.md)
6. [06 Runtime View](./arc42/06-runtime-view.md)
7. [07 Deployment View](./arc42/07-deployment-view.md)
8. [08 Cross-Cutting Concepts](./arc42/08-cross-cutting-concepts.md)
9. [09 Architecture Decisions (ADR 0001)](./arc42/09-architecture-decisions/0001-record-architecture-decisions.md), [ADR 0002](./arc42/09-architecture-decisions/0002-wait-for-webhook-id-and-execution-dependencies.md) & [ADR 0003](./arc42/09-architecture-decisions/0003-decouple-playbook-trigger-execution-via-native-hooks.md)
10. [10 Quality Requirements](./arc42/10-quality-requirements.md)
11. [11 Risks and Technical Debt](./arc42/11-risks-and-technical-debt.md)
12. [12 Glossary](./arc42/12-glossary.md)
