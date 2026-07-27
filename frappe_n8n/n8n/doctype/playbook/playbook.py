# Copyright (c) 2026, Aquiveal and contributors
# For license information, please see license.txt

import frappe
from frappe_n8n.integrations.n8n import (
	create_workflow as integration_create_workflow,
	enable_workflow as integration_enable_workflow,
	disable_workflow as integration_disable_workflow,
	delete_workflow as integration_delete_workflow,
	get_n8n_config,
)


@frappe.whitelist()
def get_builder_url(playbook_name):
	playbook_doc = frappe.get_doc("Playbook", playbook_name)
	config = get_n8n_config()
	base_url = config.get("base_url") or ""
	return f"{base_url.rstrip('/')}/workflow/{playbook_doc.n8n_workflow_id}"


@frappe.whitelist()
def trigger_test_execution(playbook_name):
	playbook_doc = frappe.get_doc("Playbook", playbook_name)

	waiting_exec = frappe.get_all(
		"Playbook Execution",
		filters={"playbook": playbook_name, "status": "waiting"},
		fields=["reference_doctype", "reference_name"],
		order_by="creation desc",
		limit=1
	)

	target_doc = None
	if waiting_exec:
		target_doc = frappe.get_doc(waiting_exec[0].reference_doctype, waiting_exec[0].reference_name)
	else:
		recent_docs = frappe.get_all(
			playbook_doc.document_type,
			order_by="creation desc",
			limit=50
		)
		for d in recent_docs:
			doc_instance = frappe.get_doc(playbook_doc.document_type, d.name)
			if playbook_doc.meets_condition(doc_instance):
				target_doc = doc_instance
				break

	if not target_doc:
		return {"status": "failed", "title": "No Document Found", "message": "No matching document found."}

	payload = target_doc.as_dict(convert_dates_to_str=True)
	execution_name = f"test-{playbook_doc.name}-{frappe.generate_hash(length=10)}"

	for node in playbook_doc.get("nodes", []):
		if node.get("node_type") == "n8n-nodes-base.webhook" and node.get("n8n_webhook_id"):
			from frappe_n8n.n8n.doctype.playbook_execution.playbook_execution import trigger_test_execution_sync
			import requests
			try:
				trigger_test_execution_sync(
					playbook_name=playbook_doc.name,
					reference_doctype=target_doc.doctype,
					reference_name=target_doc.name,
					payload=payload,
					execution_name=execution_name
				)
				return {"status": "success", "title": "Test Execution Sent", "message": "Test event sent."}
			except requests.exceptions.RequestException as e:
				msg = "Failed to send test event to n8n. Please ensure 'Listen for test events' is active in n8n."
				if getattr(e, "response", None) is not None:
					msg += f" (HTTP {e.response.status_code})"
				frappe.log_error(f"Failed to trigger n8n test execution: {e}", "n8n Execution Error")
				return {"status": "failed", "title": "Test Execution Failed", "message": msg}
			except Exception as e:
				frappe.log_error(f"Failed to trigger n8n test execution: {e}", "n8n Execution Error")
				return {"status": "failed", "title": "Error", "message": f"Failed to trigger n8n test execution: {str(e)}"}

	from frappe_controller.utils.background_jobs import enqueue
	enqueue(
		"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_test_execution_async",
		queue="high",
		playbook_name=playbook_doc.name,
		reference_doctype=target_doc.doctype,
		reference_name=target_doc.name,
		payload=payload,
		execution_name=execution_name
	)
	return {"status": "success", "title": "Test Execution Queued", "message": "Test event queued."}


def enqueue_create_workflow(playbook_name):
	frappe.enqueue(
		"frappe_n8n.n8n.doctype.playbook.playbook.create_workflow",
		playbook_name=playbook_name,
		queue="low"
	)


def create_workflow(playbook_name):
	return integration_create_workflow(playbook_name)


def toggle_workflow_status(playbook_name, is_active: bool):
	if is_active:
		integration_enable_workflow(playbook_name)
	else:
		integration_disable_workflow(playbook_name)


def delete_workflow(workflow_id):
	integration_delete_workflow(workflow_id)


def on_update(doc, method=None):
	if doc.provider != "n8n":
		return
	if not doc.n8n_workflow_id:
		enqueue_create_workflow(doc.name)
	elif doc.has_value_changed("enabled"):
		if doc.enabled:
			frappe.enqueue(
				"frappe_n8n.integrations.n8n.enable_workflow",
				playbook_name=doc.name,
				queue="low"
			)
		else:
			frappe.enqueue(
				"frappe_n8n.integrations.n8n.disable_workflow",
				playbook_name=doc.name,
				queue="low"
			)


def on_trash(doc, method=None):
	if doc.provider != "n8n" or not doc.n8n_workflow_id:
		return

	frappe.enqueue(
		"frappe_n8n.n8n.doctype.playbook.playbook.delete_workflow",
		workflow_id=doc.n8n_workflow_id,
		queue="low"
	)
