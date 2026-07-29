# Copyright (c) 2026, Aurumor and Contributors
# See license.txt

import json
import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
from frappe_n8n.integrations.n8n import N8nClient, N8nError


class TestN8nTestExecutionUnit(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("webhook_security", "test_token")
		settings.db_set("api_key", "test_key")

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch("frappe_n8n.integrations.n8n.N8nClient.move_workflow")
	@patch("frappe_n8n.integrations.n8n.N8nClient.get_workflow", return_value={"id": "wf-1", "active": True, "nodes": [{"name": "Webhook", "type": "n8n-nodes-base.webhook", "webhookId": "wh-lifecycle-test"}]})
	@patch("frappe_n8n.integrations.n8n.N8nClient.trigger_test_execution")
	def test_synchronous_test_execution_lifecycle(self, mock_client_trigger, mock_get_wf, mock_move):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_client_trigger.return_value = mock_res

		playbook_name = "Test Playbook n8n Lifecycle"
		if frappe.db.exists("Playbook", playbook_name):
			frappe.delete_doc("Playbook", playbook_name)

		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": playbook_name,
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled",
			"n8n_workflow_id": "wf-lifecycle-123",
			"playbook_data": json.dumps({"nodes": [{"type": "n8n-nodes-base.webhook", "webhookId": "wh-lifecycle-test"}]}),
			"nodes": [
				{
					"node_name": "Webhook",
					"node_type": "n8n-nodes-base.webhook",
					"n8n_webhook_id": "wh-lifecycle-test"
				}
			]
		}).insert(ignore_permissions=True)

		todo = frappe.get_doc({
			"doctype": "ToDo",
			"description": "Test Integration Todo Lifecycle"
		}).insert(ignore_permissions=True)

		initial_executions = frappe.db.count("Playbook Execution")

		from frappe_n8n.n8n.doctype.playbook.playbook import trigger_test_execution
		result = trigger_test_execution(playbook.name)

		self.assertEqual(result.get("status"), "success")
		self.assertEqual(result.get("message"), "Test event sent to n8n.")

		final_executions = frappe.db.count("Playbook Execution")
		self.assertEqual(initial_executions, final_executions)

	@patch("frappe_n8n.integrations.n8n.N8nClient.trigger_execution")
	@patch("frappe_n8n.integrations.n8n.N8nClient.get_workflow", return_value={"active": True})
	@patch("frappe_playbook.playbook.doctype.playbook_execution.playbook_execution.enqueue")
	def test_after_insert_hook_triggers_webhook(self, mock_enqueue, mock_get_wf, mock_trigger):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Webhook Insert",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled",
			"enabled": 1,
			"n8n_workflow_id": "wf-123",
			"playbook_data": json.dumps({
				"nodes": [
					{
						"type": "n8n-nodes-base.webhook",
						"webhookId": "wh-insert-123"
					}
				]
			}),
			"nodes": [
				{
					"node_name": "Webhook",
					"node_type": "n8n-nodes-base.webhook",
					"n8n_webhook_id": "wh-insert-123"
				}
			]
		}).insert(ignore_permissions=True)

		todo = frappe.get_doc({"doctype": "ToDo", "description": "test"}).insert()

		execution = frappe.get_doc({
			"doctype": "Playbook Execution",
			"name": f"test-{frappe.generate_hash(length=8)}",
			"playbook": playbook.name,
			"reference_doctype": "ToDo",
			"reference_name": todo.name,
			"status": "queued",
			"execution_data": '{"test": "data"}'
		}).insert(ignore_permissions=True, ignore_links=True)

		mock_enqueue.assert_any_call(
			"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_execution",
			execution_name=execution.name,
			queue="high"
		)

		from frappe_n8n.n8n.doctype.playbook_execution.playbook_execution import trigger_execution
		trigger_execution(execution.name)

		execution.reload()
		self.assertEqual(execution.status, "queued")
		mock_trigger.assert_called_once()

	@patch("frappe_n8n.integrations.n8n.N8nClient.stop_execution")
	@patch("frappe.enqueue")
	def test_on_update_hook_stops_execution(self, mock_enqueue, mock_stop):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")

		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Webhook Update",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled"
		}).insert(ignore_permissions=True)

		todo = frappe.get_doc({"doctype": "ToDo", "description": "test"}).insert()

		execution = frappe.get_doc({
			"doctype": "Playbook Execution",
			"name": f"test-{frappe.generate_hash(length=8)}",
			"playbook": playbook.name,
			"reference_doctype": "ToDo",
			"reference_name": todo.name,
			"status": "waiting"
		})
		execution.db_set("n8n_execution_id", "exec-123")
		execution.insert(ignore_permissions=True, ignore_links=True)

		execution.status = "canceled"
		execution.save(ignore_permissions=True)

		mock_enqueue.assert_any_call(
			"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.stop_execution",
			n8n_execution_id="exec-123",
			queue="high"
		)

		from frappe_n8n.n8n.doctype.playbook_execution.playbook_execution import stop_execution
		stop_execution("exec-123")
		mock_stop.assert_called_once_with("exec-123")

	def test_callback_accepts_name_in_payload(self):
		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Callback Name Payload",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled"
		}).insert(ignore_permissions=True)

		todo = frappe.get_doc({"doctype": "ToDo", "description": "test"}).insert()

		execution = frappe.get_doc({
			"doctype": "Playbook Execution",
			"name": f"exec-{frappe.generate_hash(length=8)}",
			"playbook": playbook.name,
			"reference_doctype": "ToDo",
			"reference_name": todo.name,
			"status": "queued"
		}).insert(ignore_permissions=True, ignore_links=True)

		from frappe_n8n.playbook_execution import callback
		res = callback(name=execution.name, status="running")

		self.assertEqual(res.get("name"), execution.name)
		self.assertEqual(res.get("status"), "running")

		execution.reload()
		self.assertEqual(execution.status, "running")

	def test_callback_test_execution_existing_execution_minimal(self):
		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": f"PB-Minimal-{frappe.generate_hash(length=6)}",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled"
		}).insert(ignore_permissions=True)

		real_exec_name = f"EXEC-{frappe.generate_hash(length=8)}"
		execution = frappe.get_doc({
			"doctype": "Playbook Execution",
			"name": real_exec_name,
			"playbook": playbook.name,
			"status": "queued"
		}).insert(ignore_permissions=True, ignore_links=True)

		from frappe_n8n.playbook_execution import callback
		test_name = f"test-{real_exec_name}"
		res = callback(name=test_name, status="running")

		self.assertEqual(res.get("name"), test_name)
		self.assertEqual(res.get("status"), "running")
		self.assertEqual(res.get("playbook"), playbook.name)

		execution.reload()
		self.assertEqual(execution.status, "queued")

	def test_callback_test_execution_existing_playbook_minimal(self):
		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": f"PB-Direct-{frappe.generate_hash(length=6)}",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled"
		}).insert(ignore_permissions=True)

		test_name = f"test-{playbook.name}"
		from frappe_n8n.playbook_execution import callback
		res = callback(name=test_name, status="running")

		self.assertEqual(res.get("name"), test_name)
		self.assertEqual(res.get("status"), "running")
		self.assertEqual(res.get("playbook"), playbook.name)
		self.assertFalse(frappe.db.exists("Playbook Execution", test_name))

	def test_callback_test_execution_nonexistent_playbook_throws(self):
		from frappe_n8n.playbook_execution import callback
		with self.assertRaises(frappe.ValidationError):
			callback(name="test-NONEXISTENT-9999", status="running")

	def test_callback_production_execution_updates_db(self):
		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": f"PB-Prod-{frappe.generate_hash(length=6)}",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled"
		}).insert(ignore_permissions=True)

		real_exec_name = f"EXEC-PROD-{frappe.generate_hash(length=8)}"
		execution = frappe.get_doc({
			"doctype": "Playbook Execution",
			"name": real_exec_name,
			"playbook": playbook.name,
			"status": "queued"
		}).insert(ignore_permissions=True, ignore_links=True)

		from frappe_n8n.playbook_execution import callback
		res = callback(name=real_exec_name, status="running")

		self.assertEqual(res.get("name"), real_exec_name)
		self.assertEqual(res.get("status"), "running")

		execution.reload()
		self.assertEqual(execution.status, "running")


