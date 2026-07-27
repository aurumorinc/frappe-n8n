# Copyright (c) 2026, Aurumor and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
from frappe_n8n.integrations.n8n import N8nError, N8nNotFoundError, N8nClient


class IntegrationTestn8nSettings(IntegrationTestCase):
	"""
	Integration tests for n8nSettings.
	"""

	def setUp(self):
		super().setUp()

		req_patcher = patch.object(N8nClient, "_request")
		self.mock_request = req_patcher.start()
		self.mock_request.return_value.status_code = 200
		self.mock_request.return_value.json.return_value = {"id": "test_id", "data": [{"id": "personal_123", "type": "personal"}]}
		self.addCleanup(req_patcher.stop)

		proj_patcher = patch("frappe_n8n.integrations.n8n.N8nClient.get_personal_project_id", return_value="personal_123")
		self.mock_get_proj = proj_patcher.start()
		self.addCleanup(proj_patcher.stop)

		enqueue_patcher = patch("frappe_controller.utils.background_jobs.enqueue")
		self.mock_enqueue = enqueue_patcher.start()
		self.addCleanup(enqueue_patcher.stop)

		if not frappe.db.exists("Playbook Provider", "n8n"):
			provider = frappe.get_doc({
				"doctype": "Playbook Provider",
				"provider_name": "n8n",
				"enabled": 0
			})
			provider.insert(ignore_permissions=True)

		self.settings = frappe.get_single("n8n Settings")
		self.settings.enabled = 1
		self.settings.status = "Authorized"
		self.settings.base_url = "https://n8n.example.com"
		self.settings.api_key = "test_api_key"
		self.settings.webhook_security = "test_webhook_token"
		self.settings.save()

	def test_n8n_settings_save_and_retrieve(self):
		settings = frappe.get_single("n8n Settings")
		self.assertEqual(settings.enabled, 1)
		self.assertEqual(settings.base_url, "https://n8n.example.com")
		self.assertEqual(settings.get_password("api_key"), "test_api_key")
		self.assertEqual(settings.get_password("webhook_security"), "test_webhook_token")

	def test_n8n_settings_registers_provider(self):
		self.assertTrue(frappe.db.exists("Playbook Provider", "n8n"))
		provider = frappe.get_doc("Playbook Provider", "n8n")
		self.assertEqual(provider.enabled, 1)

		# Disable settings
		self.settings.enabled = 0
		self.settings.save()

		provider.reload()
		self.assertEqual(provider.enabled, 0)

	@patch("frappe_n8n.integrations.n8n.N8nClient.get_personal_project_id", side_effect=N8nError("Connection failed"))
	def test_n8n_settings_validation_failure(self, mock_get_proj):
		settings = frappe.get_single("n8n Settings")
		settings.enabled = 1
		settings.base_url = "https://invalid.example.com"
		settings.api_key = "invalid_key"
		settings.save()

		self.assertEqual(settings.enabled, 0)
		self.assertEqual(settings.status, "Unauthorized")

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "create_credential", return_value="test_cred_id")
	@patch.object(N8nClient, "get_personal_project_id", return_value="proj-123")
	def test_update_webhook_credential(self, mock_proj, mock_create, mock_move, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_api_key")
		settings.db_set("webhook_security", "")
		settings.db_set("webhook_credential_id", "")

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import update_webhook_credential
		update_webhook_credential()

		settings.reload()
		self.assertEqual(settings.webhook_credential_id, "test_cred_id")
		mock_create.assert_called_once()
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "update_credential", return_value={})
	def test_update_webhook_credential_transfers_project(self, mock_update, mock_move, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_api_key")
		settings.db_set("webhook_credential_id", "test_cred_id")
		settings.db_set("project_id", "new_project_id")

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import update_webhook_credential
		update_webhook_credential()

		mock_move.assert_called_once_with("test_cred_id", "new_project_id")
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "create_credential", return_value="new_cred_id")
	@patch.object(N8nClient, "update_credential", side_effect=N8nNotFoundError("Not found", status_code=404))
	@patch.object(N8nClient, "get_credentials", return_value=[])
	def test_update_webhook_credential_recreates_if_deleted(self, mock_get_creds, mock_update, mock_create, mock_move, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_api_key")
		settings.db_set("webhook_credential_id", "old_cred_id")

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import update_webhook_credential
		update_webhook_credential()

		settings.reload()
		self.assertEqual(settings.webhook_credential_id, "new_cred_id")
		mock_create.assert_called_once()
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "update_credential", return_value={})
	@patch.object(N8nClient, "get_personal_project_id", return_value="personal_id")
	def test_update_webhook_credential_transfers_to_personal(self, mock_get_proj, mock_update, mock_move, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_api_key")
		settings.db_set("webhook_credential_id", "test_cred_id")
		settings.db_set("project_id", "")

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import update_webhook_credential
		update_webhook_credential()

		mock_move.assert_called_once_with("test_cred_id", "personal_id")
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "move_credential")
	@patch.object(N8nClient, "update_credential", return_value={})
	@patch.object(N8nClient, "get_credentials", return_value=[{"id": "found_cred_id", "name": "crm_n8n_api_key"}])
	def test_update_webhook_credential_finds_by_name(self, mock_get_creds, mock_update, mock_move, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_api_key")
		settings.db_set("webhook_credential_id", "")

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import update_webhook_credential
		update_webhook_credential()

		settings.reload()
		self.assertEqual(settings.webhook_credential_id, "found_cred_id")
		sec_token = settings.get_password("webhook_security") or settings.webhook_security
		mock_update.assert_called_once_with("found_cred_id", sec_token)
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "update_credential", return_value={})
	def test_rotate_credentials(self, mock_update, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.enabled = 1
		settings.status = "Authorized"
		settings.base_url = "https://n8n.example.com"
		settings.api_key = "test_api_key"
		settings.webhook_credential_id = "test_cred_id"
		settings.webhook_security = "test_webhook_token"
		settings.save()

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import rotate_credentials
		rotate_credentials()

		mock_update.assert_called_once()
		mock_emit.assert_any_call(key="n8n_credential_ready", argument={"status": "success"})

	def test_enqueue_rotate_credentials(self):
		self.mock_enqueue.reset_mock()
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_api_key")
		settings.db_set("webhook_credential_id", "test_cred_id")
		settings.db_set("webhook_security", "test_webhook_token")

		from frappe_n8n.n8n.doctype.n8n_settings.n8n_settings import enqueue_rotate_credentials
		enqueue_rotate_credentials()

		self.mock_enqueue.assert_called_once_with("frappe_n8n.n8n.doctype.n8n_settings.n8n_settings.rotate_credentials")
