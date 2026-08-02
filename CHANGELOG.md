# Changelog v16.1.0

## New Features

* **n8n Integration & Playbook Management**
  - Implement comprehensive n8n integration including `N8nClient`, settings doctype, workflow lifecycle management, credential rotation, and asynchronous background job queues.
  - Commits: [f98ccd2](https://github.com/aurumorinc/frappe-n8n/commit/f98ccd21), [90ca8f1](https://github.com/aurumorinc/frappe-n8n/commit/90ca8f13), [7df52fc](https://github.com/aurumorinc/frappe-n8n/commit/7df52fc7)

## Improvements

* **Architecture & Integration Layer Refactoring**
  - Refactor n8n integration logic into dedicated modules, streamline execution and validation checks, and update controller events.
  - Commits: [921f8cd](https://github.com/aurumorinc/frappe-n8n/commit/921f8cd1), [39a8817](https://github.com/aurumorinc/frappe-n8n/commit/39a8817b), [cced7fa](https://github.com/aurumorinc/frappe-n8n/commit/cced7fa1)

* **Test Suite Consolidation & Expansion**
  - Add comprehensive unit and integration tests covering `N8nClient`, playbook provider execution, error scenarios, and idempotency checks.
  - Commits: [d7e188a](https://github.com/aurumorinc/frappe-n8n/commit/d7e188a0), [8d3fe02](https://github.com/aurumorinc/frappe-n8n/commit/8d3fe02c), [3f31a04](https://github.com/aurumorinc/frappe-n8n/commit/3f31a042)

## Fixes

* **Execution Flow & Error Handling**
  - Standardize execution header (`frappe-id`), improve error handling with explicit exceptions, and refine webhook retrieval logic.
  - Commits: [9f8ebc3](https://github.com/aurumorinc/frappe-n8n/commit/9f8ebc3a), [4f6878c](https://github.com/aurumorinc/frappe-n8n/commit/4f6878ce), [384386f](https://github.com/aurumorinc/frappe-n8n/commit/384386f7)

## Infrastructure

* **Project Metadata, Configuration & Dependencies**
  - Configure project metadata, dependencies (`cloudevents`, `bumpver`), copyright headers, and app initialization structure.
  - Commits: [e68a92b](https://github.com/aurumorinc/frappe-n8n/commit/e68a92be), [db7c1d2](https://github.com/aurumorinc/frappe-n8n/commit/db7c1d2b), [0d5b6d2](https://github.com/aurumorinc/frappe-n8n/commit/0d5b6d29)

## Docs

* **Architecture Documentation & Pull Request Template**
  - Add detailed system architecture documentation (C4, BPMN, arc42), versioning analysis rules, and a standardized pull request template.
  - Commits: [1e58a6c](https://github.com/aurumorinc/frappe-n8n/commit/1e58a6c9), [7f18b02](https://github.com/aurumorinc/frappe-n8n/commit/7f18b02e), [bd43b49](https://github.com/aurumorinc/frappe-n8n/commit/bd43b49a)
