# 07 Deployment View

This chapter documents the deployment topology, network nodes, and runtime environment mapping for `frappe_n8n`.

## Infrastructure & Node Mapping

```mermaid
erDiagram
    "Client Browser / API Client" ||--o{ "Nginx Reverse Proxy (Port 80/443)" : "HTTPS requests"
    "Nginx Reverse Proxy (Port 80/443)" ||--o{ "Gunicorn Web Server (Port 8000)" : "HTTP WSGI traffic"
    "Gunicorn Web Server (Port 8000)" ||--|| "MariaDB / PostgreSQL DB Node (Port 3306/5432)" : "SQL connections"
    "Gunicorn Web Server (Port 8000)" ||--|| "Redis Cache Server (Port 6379)" : "In-memory caching"
    "Gunicorn Web Server (Port 8000)" ||--|| "Redis Queue Server (Port 6379)" : "Enqueues background jobs"
    "Frappe Scheduler Node" ||--|| "Redis Queue Server (Port 6379)" : "Enqueues scheduled cron tasks"
    "Worker FS Process" ||--|| "Redis Queue Server (Port 6379)" : "Pulls queued tasks"
    "Worker FS Process" ||--|| "MariaDB / PostgreSQL DB Node (Port 3306/5432)" : "SQL updates"
    "Gunicorn Web Server (Port 8000)" ||--o{ "External n8n Instance (Port 5678/443)" : "Outbound REST API & Webhooks"
    "Worker FS Process" ||--o{ "External n8n Instance (Port 5678/443)" : "Outbound REST API calls"
    "External n8n Instance (Port 5678/443)" ||--o{ "Nginx Reverse Proxy (Port 80/443)" : "Inbound webhook callbacks"
```

## Deployment Elements

### 1. Web Application Tier
- **Nginx**: Front-end proxy handling TLS termination and static asset serving.
- **Gunicorn**: WSGI app worker executing `frappe_n8n` request handlers, whitelisted endpoints, and public webhook callbacks.

### 2. Async Execution Tier
- **Worker FS**: Background worker process dedicated to executing enqueued long-running jobs (credential provisioning, workflow migration, playbook synchronization).
- **Scheduler**: Bench scheduler daemon executing periodic cron events (quarterly credential rotation and periodic playbook sync).

### 3. State & Queue Storage Tier
- **MariaDB / PostgreSQL**: Primary relational database storing site data, DocTypes, custom fields, and execution histories.
- **Redis Cache & Queue**: Dual Redis instances handling configuration/flag caching and RQ task queue management.

### 4. External Integration Target
- **n8n Instance**: Self-hosted or cloud n8n server accessible over HTTP/HTTPS (default port 5678 or standard 443).
