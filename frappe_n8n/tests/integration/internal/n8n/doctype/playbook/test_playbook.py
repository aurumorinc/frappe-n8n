# Copyright (c) 2026, Aurumor and Contributors
# See license.txt

import json
import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
from frappe_n8n.integrations.n8n import N8nClient


class TestN8nPlaybook(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch.object(N8nClient, "move_workflow")
	@patch.object(N8nClient, "activate_workflow")
	@patch.object(N8nClient, "create_workflow", return_value={"id": "wf-12345", "nodes": [{"name": "Webhook", "type": "n8n-nodes-base.webhook", "id": "node-1", "webhookId": "wh-1"}], "connections": {}})
	@patch("frappe.enqueue")
	def test_on_playbook_after_insert_creates_workflow(self, mock_enqueue, mock_create, mock_activate, mock_move):
		settings = frappe.get_doc("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		provider = frappe.get_doc("Playbook Provider", "n8n")
		provider.db_set("enabled", 1)

		playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test N8n Playbook Hook",
			"provider": "n8n",
			"document_type": "ToDo", 
			"status": "Enabled"
		}).insert()

		mock_enqueue.assert_called_with(
			"frappe_n8n.integrations.n8n.create_workflow",
			playbook_name=playbook.name,
			queue="low"
		)

		from frappe_n8n.integrations.n8n import create_workflow
		create_workflow(playbook.name)

		playbook.reload()
		self.assertEqual(playbook.n8n_workflow_id, "wf-12345")
		self.assertEqual(len(playbook.nodes), 1)
		self.assertEqual(playbook.nodes[0].node_name, "Webhook")

	def test_validate_cannot_enable_playbook_when_provider_disabled(self):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")

		provider = frappe.get_doc("Playbook Provider", "n8n")
		provider.db_set("enabled", 0)

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test PB Provider Disabled",
			"provider": "n8n",
			"document_type": "ToDo",
			"enabled": 1,
			"status": "Enabled"
		})
		with self.assertRaises(frappe.ValidationError) as cm:
			pb.insert()
		self.assertIn("Playbook Provider is disabled", str(cm.exception))

	def test_validate_cannot_enable_playbook_when_settings_unauthorized(self):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 0)
		settings.db_set("status", "Unauthorized")

		provider = frappe.get_doc("Playbook Provider", "n8n")
		provider.db_set("enabled", 1)

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test PB Settings Unauthorized",
			"provider": "n8n",
			"document_type": "ToDo",
			"enabled": 1,
			"status": "Enabled"
		})
		with self.assertRaises(frappe.ValidationError) as cm:
			pb.insert()
		self.assertIn("Settings are not authorized", str(cm.exception))


class TestN8NTestExecutionGracefulExit(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.patcher = patch("frappe_n8n.integrations.n8n.create_workflow", return_value="wf-mock-123")
		self.mock_create_workflow = self.patcher.start()

		self.patcher2 = patch("frappe_n8n.n8n.doctype.playbook.playbook.toggle_workflow_status")
		self.mock_toggle = self.patcher2.start()

		self.patcher3 = patch("frappe_n8n.n8n.doctype.playbook.playbook.on_trash")
		self.mock_trash = self.patcher3.start()

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")

		if not frappe.db.exists("Playbook Provider", "n8n"):
			frappe.get_doc({
				"doctype": "Playbook Provider",
				"provider_name": "n8n",
				"enabled": 1
			}).insert(ignore_permissions=True)
		else:
			provider = frappe.get_doc("Playbook Provider", "n8n")
			provider.db_set("enabled", 1)

		self.playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Playbook",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled",
			"playbook_data": json.dumps({
				"nodes": [{"type": "n8n-nodes-base.webhook", "webhookId": "test-webhook-id"}]
			}),
			"nodes": [{"node_type": "n8n-nodes-base.webhook", "n8n_webhook_id": "test-webhook-id"}]
		}).insert()

	def tearDown(self):
		self.patcher.stop()
		self.patcher2.stop()
		self.patcher3.stop()
		frappe.db.rollback()
		super().tearDown()

	@patch("frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.update_a_playbook")
	@patch("frappe_n8n.integrations.n8n.N8nClient.trigger_test_execution")
	def test_trigger_test_execution_graceful_failure(self, mock_client_trigger, mock_update_pb):
		from frappe_n8n.n8n.doctype.playbook.playbook import trigger_test_execution

		response = MagicMock()
		response.status_code = 404
		response.text = "Not found"
		mock_client_trigger.return_value = response

		settings = frappe.get_doc("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "test"}).insert(ignore_permissions=True)

		result = trigger_test_execution(self.playbook.name)
		self.assertEqual(result.get("status"), "failed")
		self.assertEqual(result.get("title"), "Test Execution Failed")

	def test_whitelisting_playbook_overrides(self):
		from frappe_n8n import hooks
		self.assertIn("frappe_playbook.playbook.doctype.playbook.playbook.get_builder_url", hooks.override_whitelisted_methods)
		self.assertIn("frappe_playbook.playbook.doctype.playbook.playbook.trigger_test_execution", hooks.override_whitelisted_methods)


class TestN8NDecoupledPlaybookOperations(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.settings = frappe.get_doc("n8n Settings")
		self.settings.db_set("enabled", 1)
		self.settings.db_set("status", "Authorized")
		self.settings.db_set("base_url", "https://n8n.example.com")
		self.settings.db_set("api_key", "test_api_key")

		if frappe.db.exists("Playbook Provider", "n8n"):
			provider = frappe.get_doc("Playbook Provider", "n8n")
			provider.db_set("enabled", 1)

		frappe.db.commit()

		if frappe.db.exists("Playbook", "Test Decoupled Playbook"):
			frappe.delete_doc("Playbook", "Test Decoupled Playbook")

		self.playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Decoupled Playbook",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled",
			"n8n_workflow_id": "wf-test-123"
		}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch("frappe.enqueue")
	def test_on_trash_enqueues_deletion(self, mock_enqueue):
		self.playbook.delete()
		mock_enqueue.assert_any_call(
			"frappe_n8n.integrations.n8n.delete_workflow",
			workflow_id="wf-test-123",
			queue="low"
		)

	@patch("frappe_n8n.integrations.n8n.N8nClient.delete_workflow")
	def test_delete_workflow_success(self, mock_delete):
		from frappe_n8n.n8n.doctype.playbook.playbook import delete_workflow
		delete_workflow("wf-test-123")
		mock_delete.assert_called_once_with("wf-test-123")

	@patch("frappe.enqueue")
	def test_on_update_enqueues_creation(self, mock_enqueue):
		new_pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "New Decoupled Playbook",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled"
		}).insert(ignore_permissions=True)

		mock_enqueue.assert_any_call(
			"frappe_n8n.integrations.n8n.create_workflow",
			playbook_name=new_pb.name,
			queue="low"
		)
