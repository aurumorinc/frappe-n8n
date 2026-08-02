# Copyright (c) 2026, Aurumor and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
from frappe_n8n.integrations.n8n import N8nNotFoundError


class TestN8nPlaybookProvider(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.settings = frappe.get_doc("n8n Settings")
		self.settings.db_set("enabled", 1)
		self.settings.db_set("status", "Authorized")
		self.settings.db_set("base_url", "https://n8n.example.com")
		self.settings.db_set("api_key", "test_api_key")
		frappe.db.commit()

		if frappe.db.exists("Playbook", "Test Stale Playbook Provider"):
			frappe.delete_doc("Playbook", "Test Stale Playbook Provider")

		self.playbook = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Stale Playbook Provider",
			"provider": "n8n",
			"document_type": "ToDo",
			"status": "Enabled",
			"n8n_workflow_id": "stale-wf-999"
		}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch("frappe_n8n.integrations.n8n.N8nClient.get_workflow")
	def test_retrieve_workflow_success(self, mock_get_wf):
		mock_get_wf.return_value = {
			"id": "stale-wf-999",
			"name": "Test Stale Playbook Provider",
			"active": True,
			"nodes": [],
			"connections": {}
		}

		from frappe_n8n.n8n.doctype.playbook_provider.playbook_provider import retrieve_workflow
		result = retrieve_workflow(self.playbook.name)

		self.assertIsNotNone(result)
		self.assertEqual(result.get("id"), "stale-wf-999")
		mock_get_wf.assert_called_once_with("stale-wf-999")

	@patch("frappe_n8n.integrations.n8n.create_workflow")
	@patch("frappe_n8n.integrations.n8n.N8nClient.get_workflow", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_retrieve_workflow_404_resets_id_and_reprovisions(self, mock_get_wf, mock_create):
		from frappe_n8n.n8n.doctype.playbook_provider.playbook_provider import retrieve_workflow
		result = retrieve_workflow(self.playbook.name)

		self.assertIsNone(result)
		self.playbook.reload()
		self.assertIsNone(self.playbook.n8n_workflow_id)
		mock_create.assert_called_once_with(self.playbook.name)

	@patch("frappe_n8n.integrations.n8n.create_workflow")
	@patch("frappe_n8n.integrations.n8n.N8nClient.get_workflow", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_update_a_playbook_handles_404_gracefully(self, mock_get_wf, mock_create):
		from frappe_n8n.n8n.doctype.playbook_provider.playbook_provider import update_a_playbook
		update_a_playbook(self.playbook.name)

		self.playbook.reload()
		self.assertIsNone(self.playbook.n8n_workflow_id)
		mock_create.assert_called_once_with(self.playbook.name)

	@patch("frappe_n8n.integrations.n8n.N8nClient.deactivate_workflow")
	@patch("frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.integration_disable_workflow")
	def test_provider_disabled_cascades_disable_to_playbooks(self, mock_disable_wf, mock_client_deactivate):
		provider = frappe.get_doc("Playbook Provider", "n8n")
		provider.enabled = 1
		provider.save()

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Cascade Provider PB",
			"provider": "n8n",
			"document_type": "ToDo",
			"enabled": 1,
			"status": "Enabled",
			"n8n_workflow_id": "wf-cascade-p1"
		}).insert(ignore_permissions=True)

		provider.reload()
		provider.enabled = 0
		provider.save()

		pb.reload()
		self.assertEqual(pb.enabled, 0)

