# Copyright (c) 2026, Aquiveal and contributors
# For license information, please see license.txt

import json
import frappe
from frappe_controller.utils.background_jobs import enqueue
from frappe_n8n.integrations.n8n import (
	retrieve_workflow as integration_retrieve_workflow,
	enable_workflow as integration_enable_workflow,
	disable_workflow as integration_disable_workflow,
)


def on_update(doc, method=None):
	if doc.has_value_changed("enabled"):
		playbooks = frappe.get_all("Playbook", filters={"provider": "n8n", "enabled": 1})
		for pb in playbooks:
			if doc.enabled:
				integration_enable_workflow(pb.name)
			else:
				integration_disable_workflow(pb.name)


def enqueue_update_playbooks():
	playbooks = frappe.get_all("Playbook", filters={"provider": "n8n"})
	for p in playbooks:
		enqueue("frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.update_a_playbook", playbook_name=p.name)


def retrieve_workflow(playbook_name):
	return integration_retrieve_workflow(playbook_name)


def update_a_playbook(playbook_name):
	playbook_data = retrieve_workflow(playbook_name)
	if not playbook_data:
		return

	playbook_doc = frappe.get_doc("Playbook", playbook_name)

	# Status
	playbook_doc.enabled = playbook_data.get("active", False)

	# Vue-Flow Elements (playbook_data)
	vue_flow_data = {
		"nodes": playbook_data.get("nodes", []),
		"connections": playbook_data.get("connections", {})
	}
	playbook_doc.playbook_data = json.dumps(vue_flow_data)

	# Child Table Nodes
	playbook_doc.set("nodes", [])
	for node in playbook_data.get("nodes", []):
		playbook_doc.append("nodes", {
			"node_name": node.get("name"),
			"node_type": node.get("type"),
			"disabled": node.get("disabled", False),
			"retry_on_fail": node.get("retryOnFail", False),
			"on_error": node.get("onError", ""),
			"n8n_node_id": node.get("id"),
			"n8n_webhook_id": node.get("webhookId", "")
		})

	frappe.flags.in_playbook_sync = True
	try:
		playbook_doc.save(ignore_permissions=True)
	finally:
		frappe.flags.in_playbook_sync = False
