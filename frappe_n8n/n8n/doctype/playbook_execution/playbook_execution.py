# Copyright (c) 2026, Aquiveal and contributors
# For license information, please see license.txt

import json
import frappe
from frappe_controller.utils.background_jobs import enqueue
from frappe_controller.utils.controller import wait_for_event
from frappe_n8n.integrations.n8n import (
	trigger_execution as integration_trigger_execution,
	stop_execution as integration_stop_execution,
	resume_execution as integration_resume_execution,
	get_n8n_config,
)


def after_insert(doc, method=None):
	enqueue_trigger_execution(doc)


def enqueue_trigger_execution(doc):
	provider = frappe.db.get_value("Playbook", doc.playbook, "provider")
	if provider == "n8n":
		enqueue(
			"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_execution",
			execution_name=doc.name,
			queue="high"
		)


def trigger_execution(execution_name):
	doc = frappe.get_doc("Playbook Execution", execution_name)
	if doc.status != "queued":
		return

	payload = json.loads(doc.execution_data) if doc.execution_data else {}
	try:
		integration_trigger_execution(
			playbook_name=doc.playbook,
			payload=payload,
			execution_name=doc.name
		)
	except Exception as e:
		frappe.log_error(f"Failed to trigger n8n execution: {e}", "n8n Execution Error")
		doc.status = "failed"
		doc.save(ignore_permissions=True)
		raise


def on_update(doc, method=None):
	if doc.has_value_changed("status") and doc.status == "canceled":
		playbook = frappe.db.get_value("Playbook", doc.playbook, "provider")
		if playbook == "n8n" and doc.n8n_execution_id:
			frappe.enqueue(
				"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.stop_execution",
				n8n_execution_id=doc.n8n_execution_id,
				queue="high"
			)


def stop_execution(n8n_execution_id):
	return integration_stop_execution(n8n_execution_id)


@frappe.whitelist()
def get_debug_url(execution_name):
	doc = frappe.get_doc("Playbook Execution", execution_name)
	if not doc.get("n8n_execution_id"):
		return None

	playbook = frappe.get_doc("Playbook", doc.playbook)
	config = get_n8n_config()
	base_url = config.get("base_url") or ""

	if not base_url or not playbook.n8n_workflow_id:
		return None

	return f"{base_url.rstrip('/')}/workflow/{playbook.n8n_workflow_id}/debug/{doc.n8n_execution_id}"


@frappe.whitelist()
def replay(execution_name):
	doc = frappe.get_doc("Playbook Execution", execution_name)
	if doc.status not in ["success", "failed", "error", "canceled"]:
		frappe.throw(f"Cannot replay execution in '{doc.status}' status. Replay is only allowed when execution is finished.")

	doc.status = "queued"
	doc.save(ignore_permissions=True)
	payload = json.loads(doc.execution_data) if doc.execution_data else {}
	integration_trigger_execution(
		playbook_name=doc.playbook,
		payload=payload,
		execution_name=doc.name
	)


def resume_execution(url, payload, execution_id=None):
	integration_resume_execution(url=url, payload=payload, execution_id=execution_id)
