# 11 Risks and Technical Debt

This chapter identifies technical risks, single points of failure, and technical debt in `frappe_n8n`.

## Risk Matrix

| Risk ID | Risk Description | Severity | Impact | Mitigation Strategy |
|---------|------------------|----------|--------|---------------------|
| **R-01** | **Network Latency or Outage during Webhook Trigger**: External n8n server is unreachable when `trigger_execution` is called. | High | Execution marked as `failed`. | Implement exponential backoff retry policy using `frappe.enqueue` retry parameters. |
| **R-02** | **Guest Callback Endpoint Abuse**: Whitelisted callback endpoint (`allow_guest=True`) exposed to brute-force or spam POST requests. | Medium | Potential execution doc spam. | Enforce webhook token verification (`webhook_secret`) and rate-limiting at Nginx gateway level. |
| **R-03** | **Unsynced Playbook Schemas**: User modifies workflow nodes directly in n8n UI without updating Frappe. | Medium | Discrepancy in `Playbook Node` child table. | Periodic background sync (`enqueue_update_playbooks`) runs on scheduler to fetch latest nodes and connections. |

## Technical Debt Inventory

1. **Hardcoded Timeout (10 seconds)**:
   - `N8nClient._request` hardcodes a 10-second request timeout (`timeout=10`). Large workflow payloads or slow networks may require configurable timeouts.
2. **Synchronous Execution Calls in Certain Controllers**:
   - `trigger_execution` issues synchronous HTTP POST requests to n8n webhooks. If n8n response is slow, web/worker thread remains blocked for up to 10 seconds.
