# Copyright (c) 2026, Aquiveal and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
from frappe_n8n.integrations.n8n import (
	get_n8n_config,
	N8nClient,
	N8nError,
	N8nNotFoundError,
	update_credential,
	rotate_credentials,
	create_workflow,
	move_workflow,
	enable_workflow,
	disable_workflow,
	delete_workflow,
)


class TestN8nInternalIntegration(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def test_n8n_config_resolution_from_site_config(self):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("base_url", "https://db.example.com")
		settings.db_set("api_key", "db_key")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")

		with patch.dict(frappe.conf, {
			"n8n_base_url": "https://conf.example.com",
			"n8n_api_key": "conf_key",
			"n8n_project_id": "conf_proj",
			"n8n_enabled": 1
		}):
			config = get_n8n_config()
			self.assertEqual(config["base_url"], "https://conf.example.com")
			self.assertEqual(config["api_key"], "conf_key")
			self.assertEqual(config["project_id"], "conf_proj")
			self.assertTrue(config["enabled"])

	@patch.object(N8nClient, "get_personal_project_id", return_value="personal_123")
	def test_n8n_settings_validation_sets_status_authorized(self, mock_get_proj):
		settings = frappe.get_single("n8n Settings")
		settings.enabled = 1
		settings.base_url = "https://n8n.example.com"
		settings.api_key = "valid_key"
		settings.validate()
		self.assertEqual(settings.status, "Authorized")

	@patch.object(N8nClient, "get_personal_project_id", side_effect=N8nError("Invalid key", status_code=401))
	def test_n8n_settings_validation_sets_status_unauthorized_on_error(self, mock_get_proj):
		settings = frappe.get_single("n8n Settings")
		settings.enabled = 1
		settings.base_url = "https://n8n.example.com"
		settings.api_key = "invalid_key"
		settings.validate()
		self.assertEqual(settings.status, "Unauthorized")
		self.assertEqual(settings.enabled, 0)

	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_n8n_client_from_settings_suspends_when_unauthorized(self, mock_wait):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Unauthorized")

		frappe.flags.current_job_id = "test_job_123"
		try:
			N8nClient.from_settings(wait_if_unauthorized=True)
			mock_wait.assert_called_once_with("doc:n8n Settings:authorized")
		finally:
			frappe.flags.current_job_id = None

	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "update_credential", return_value={})
	@patch("frappe_controller.utils.controller.emit_event")
	def test_update_credential_successful_move(self, mock_emit, mock_update, mock_move):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")
		settings.db_set("webhook_security", "token_123")
		settings.db_set("webhook_credential_id", "cred_123")
		settings.db_set("project_id", "proj_456")

		update_credential()
		mock_update.assert_called_once_with("cred_123", "token_123")
		mock_move.assert_called_once_with("cred_123", "proj_456")
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "create_credential", return_value="new_cred_999")
	@patch.object(N8nClient, "update_credential", side_effect=N8nNotFoundError("Not found", status_code=404))
	@patch.object(N8nClient, "get_credentials", return_value=[])
	@patch("frappe_controller.utils.controller.emit_event")
	def test_update_credential_patch_404_reprovisions(self, mock_emit, mock_get_creds, mock_update, mock_create, mock_move):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")
		settings.db_set("webhook_credential_id", "stale_cred_id")
		settings.db_set("project_id", "proj_456")

		update_credential()
		settings.reload()
		self.assertEqual(settings.webhook_credential_id, "new_cred_999")
		mock_create.assert_called_once()
		mock_move.assert_called_once_with("new_cred_999", "proj_456")

	@patch.object(N8nClient, "move_credential", side_effect=[N8nNotFoundError("Not found", status_code=404), None])
	@patch.object(N8nClient, "create_credential", return_value="recreated_cred")
	@patch.object(N8nClient, "update_credential", return_value={})
	@patch("frappe_controller.utils.controller.emit_event")
	def test_update_credential_move_404_reprovisions(self, mock_emit, mock_update, mock_create, mock_move):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")
		settings.db_set("webhook_credential_id", "old_cred")
		settings.db_set("project_id", "target_proj")

		update_credential()
		settings.reload()
		self.assertEqual(settings.webhook_credential_id, "recreated_cred")
		self.assertEqual(mock_move.call_count, 2)

	@patch.object(N8nClient, "move_workflow")
	def test_move_workflow_successful_move(self, mock_move):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Move PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "wf_123"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		move_workflow(pb.name, "proj_new")
		mock_move.assert_called_once_with("wf_123", "proj_new")

	@patch("frappe_n8n.integrations.n8n.create_workflow")
	@patch.object(N8nClient, "move_workflow", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_move_workflow_404_reprovisions(self, mock_move, mock_create):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Stale Move PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "stale_wf"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		move_workflow(pb.name, "proj_new")
		pb.reload()
		self.assertIsNone(pb.n8n_workflow_id)
		mock_create.assert_called_once_with(pb.name)

	@patch("frappe_n8n.integrations.n8n.create_workflow")
	@patch.object(N8nClient, "activate_workflow", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_enable_workflow_404_reprovisions(self, mock_activate, mock_create):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Enable PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "stale_wf"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		enable_workflow(pb.name)
		pb.reload()
		self.assertIsNone(pb.n8n_workflow_id)
		mock_create.assert_called_once_with(pb.name)

	@patch.object(N8nClient, "deactivate_workflow", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_disable_workflow_404_clears_id(self, mock_deactivate):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Disable PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "stale_wf"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		disable_workflow(pb.name)
		pb.reload()
		self.assertIsNone(pb.n8n_workflow_id)

	@patch.object(N8nClient, "_request", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_delete_workflow_404_ignored(self, mock_request):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		delete_workflow("non_existent_wf")
		mock_request.assert_called_once_with("DELETE", "/api/v1/workflows/non_existent_wf")
