# Copyright (c) 2026, Aquiveal and contributors
# For license information, please see license.txt

import frappe
from frappe_n8n.integrations.n8n import (
	create_workflow as integration_create_workflow,
	enable_workflow as integration_enable_workflow,
	disable_workflow as integration_disable_workflow,
	delete_workflow as integration_delete_workflow,
	trigger_test_execution as integration_trigger_test_execution,
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

	exec_docs = frappe.get_all(
		"Playbook Execution",
		filters={"playbook": playbook_name, "status": "waiting"},
		fields=["name", "reference_doctype", "reference_name"],
		order_by="creation desc",
		limit=1
	)

	if not exec_docs:
		exec_docs = frappe.get_all(
			"Playbook Execution",
			filters={"playbook": playbook_name},
			fields=["name", "reference_doctype", "reference_name"],
			order_by="creation desc",
			limit=1
		)

	target_doc = None
	if exec_docs:
		target_doc = frappe.get_doc(exec_docs[0].reference_doctype, exec_docs[0].reference_name)
		execution_name = f"test-{exec_docs[0].name}"
	else:
		execution_name = f"test-{playbook_doc.name}"
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

	return integration_trigger_test_execution(
		playbook_name=playbook_doc.name,
		payload=payload,
		execution_name=execution_name,
	)


def enqueue_create_workflow(playbook_name):
	frappe.enqueue(
		"frappe_n8n.integrations.n8n.create_workflow",
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
	elif not doc.flags.in_insert and doc.get_doc_before_save() and doc.has_value_changed("enabled"):
		if doc.enabled:
			integration_enable_workflow(doc.name)
		else:
			integration_disable_workflow(doc.name)


def on_trash(doc, method=None):
	if doc.provider != "n8n" or not doc.n8n_workflow_id:
		return

	frappe.enqueue(
		"frappe_n8n.integrations.n8n.delete_workflow",
		workflow_id=doc.n8n_workflow_id,
		queue="low"
	)
