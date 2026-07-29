# Copyright (c) 2026, Aurumor and Contributors
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
	retrieve_workflow,
	trigger_test_execution,
	trigger_execution,
	stop_execution,
	resume_execution,
)


class TestN8nInternalIntegration(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def test_get_n8n_config_site_config_override(self):
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

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "update_credential", return_value={})
	@patch.object(N8nClient, "move_credential")
	def test_update_credential_creation_and_event(self, mock_move, mock_update, mock_emit):
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

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "get_credentials", return_value=[])
	@patch.object(N8nClient, "update_credential", side_effect=N8nNotFoundError("Not found", status_code=404))
	@patch.object(N8nClient, "create_credential", return_value="new_cred_999")
	@patch.object(N8nClient, "move_credential")
	def test_update_credential_404_reprovisions(self, mock_move, mock_create, mock_update, mock_get_creds, mock_emit):
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

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "update_credential", return_value={})
	def test_rotate_credentials_generates_new_key(self, mock_update, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")
		settings.db_set("webhook_credential_id", "cred_123")
		settings.db_set("webhook_security", "old_sec")

		rotate_credentials()
		settings.reload()
		self.assertNotEqual(settings.webhook_security, "old_sec")
		mock_update.assert_called_once()

	@patch.object(N8nClient, "move_workflow")
	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "create_workflow", return_value={"id": "wf-new-777", "nodes": [], "connections": {}})
	def test_create_workflow_populates_db_and_emits_event(self, mock_create, mock_emit, mock_move):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Create WF PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"enabled": 0
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		wf_id = create_workflow(pb.name)
		self.assertEqual(wf_id, "wf-new-777")
		pb.reload()
		self.assertEqual(pb.n8n_workflow_id, "wf-new-777")
		mock_emit.assert_any_call(key="n8n_workflow_created", argument={"playbook_name": pb.name})

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "activate_workflow")
	def test_enable_workflow_synchronously_activates_n8n_workflow(self, mock_activate, mock_emit):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Enable Sync PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "wf-enable-123"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		enable_workflow(pb.name)
		mock_activate.assert_called_once_with("wf-enable-123")
		mock_emit.assert_any_call(key=f"doc:Playbook:{pb.name}:enabled", argument={"status": "enabled"})

	@patch.object(N8nClient, "deactivate_workflow")
	def test_disable_workflow_synchronously_deactivates_n8n_workflow(self, mock_deactivate):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Disable Sync PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "wf-disable-123"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		disable_workflow(pb.name)
		mock_deactivate.assert_called_once_with("wf-disable-123")

	@patch.object(N8nClient, "move_workflow")
	def test_move_workflow_same_destination_idempotent(self, mock_move):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Move WF Same Dest PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "wf-move-123"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		# Simulating that move_workflow returns cleanly without raising exception
		move_workflow(pb.name, "proj-destination-123")
		mock_move.assert_called_once_with("wf-move-123", "proj-destination-123")

	@patch.object(N8nClient, "get_workflow", side_effect=N8nNotFoundError("Not found", status_code=404))
	@patch("frappe_n8n.integrations.n8n.create_workflow")
	def test_retrieve_workflow_404_reprovisions(self, mock_create, mock_get_wf):
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Retrieve Stale PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "stale_wf"
		}).insert(ignore_permissions=True)

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		res = retrieve_workflow(pb.name)
		self.assertIsNone(res)
		pb.reload()
		self.assertIsNone(pb.n8n_workflow_id)
		mock_create.assert_called_once_with(pb.name)

	def test_trigger_test_execution_unauthorized_returns_ui_error(self):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 0)
		settings.db_set("status", "Unauthorized")

		res = trigger_test_execution("Any Playbook", {}, "test-exec-1")
		self.assertEqual(res["status"], "failed")
		self.assertEqual(res["title"], "n8n Unauthorized")

	@patch.object(N8nClient, "move_workflow")
	@patch.object(N8nClient, "trigger_test_execution")
	@patch("frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.update_a_playbook")
	def test_trigger_test_execution_syncs_workflow_first(self, mock_sync_playbook, mock_client_trigger, mock_move):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_client_trigger.return_value = mock_res

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")
		settings.db_set("webhook_security", "sec_123")

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Sync Test Exec PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"n8n_workflow_id": "wf-sync-1",
			"nodes": [{"node_name": "Webhook", "node_type": "n8n-nodes-base.webhook", "n8n_webhook_id": "wh-sync-test"}]
		}).insert(ignore_permissions=True)

		res = trigger_test_execution(pb.name, {"key": "val"}, "test-exec-name")
		mock_sync_playbook.assert_called_once_with(pb.name)
		mock_client_trigger.assert_called_once_with(
			webhook_id="wh-sync-test",
			payload={"key": "val"},
			execution_name="test-exec-name",
			webhook_security="sec_123"
		)
		self.assertEqual(res["status"], "success")

	@patch.object(N8nClient, "move_workflow")
	@patch("frappe_n8n.integrations.n8n.create_workflow")
	@patch.object(N8nClient, "trigger_test_execution")
	@patch("frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.update_a_playbook")
	def test_trigger_test_execution_provisions_workflow_if_missing(self, mock_sync, mock_client_trigger, mock_create_wf, mock_move):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_client_trigger.return_value = mock_res

		def mock_create_impl(playbook_name):
			p = frappe.get_doc("Playbook", playbook_name)
			p.db_set("n8n_workflow_id", "wf-newly-created")

		mock_create_wf.side_effect = mock_create_impl

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Provision Unset WF PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"nodes": [{"node_name": "Webhook", "node_type": "n8n-nodes-base.webhook", "n8n_webhook_id": "wh-auto-123"}]
		}).insert(ignore_permissions=True)

		res = trigger_test_execution(pb.name, {"key": "val"}, "test-exec-name")
		mock_create_wf.assert_called_once_with(pb.name)
		self.assertEqual(res["status"], "success")

	@patch("frappe_controller.utils.controller.wait_for_event")
	@patch.object(N8nClient, "trigger_execution")
	@patch.object(N8nClient, "get_workflow", return_value={"active": False})
	def test_trigger_execution_waits_for_authorized_and_enabled_events(self, mock_get_wf, mock_trigger, mock_wait):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Unauthorized")

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Exec Wait PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"enabled": 0,
			"n8n_workflow_id": "wf-wait-123",
			"nodes": [{"node_name": "Webhook", "node_type": "n8n-nodes-base.webhook", "n8n_webhook_id": "wh-wait"}]
		}).insert(ignore_permissions=True)

		try:
			frappe.flags.current_job_id = "job-123"
			trigger_execution(pb.name, {"a": 1}, "exec-wait")
			mock_wait.assert_any_call("doc:n8n Settings:authorized")
		finally:
			frappe.flags.current_job_id = None

	@patch("frappe_controller.utils.controller.emit_event")
	@patch.object(N8nClient, "get_workflow", return_value={"active": True})
	@patch.object(N8nClient, "trigger_execution")
	def test_trigger_execution_syncs_active_workflow_state(self, mock_trigger, mock_get_wf, mock_emit):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Exec Active Sync PB",
			"document_type": "ToDo",
			"provider": "n8n",
			"enabled": 0,
			"n8n_workflow_id": "wf-active-123",
			"nodes": [{"node_name": "Webhook", "node_type": "n8n-nodes-base.webhook", "n8n_webhook_id": "wh-active"}]
		}).insert(ignore_permissions=True)

		trigger_execution(pb.name, {"data": "test"}, "exec-active")
		pb.reload()
		self.assertEqual(pb.enabled, 1)
		mock_emit.assert_any_call(key=f"doc:Playbook:{pb.name}:enabled", argument={"status": "enabled"})
		mock_trigger.assert_called_once()

	@patch("frappe.log_error")
	@patch.object(N8nClient, "stop_execution", side_effect=N8nNotFoundError("Not found", status_code=404))
	def test_stop_execution_handles_404_gracefully(self, mock_client_stop, mock_log_error):
		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		res = stop_execution("stale-exec-123")
		self.assertIsNone(res)
		mock_log_error.assert_called_once()

	@patch.object(N8nClient, "resume_execution")
	def test_resume_execution_updates_status_on_failure(self, mock_client_resume):
		mock_res = MagicMock()
		mock_res.status_code = 500
		mock_client_resume.return_value = mock_res

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")
		settings.db_set("base_url", "https://n8n.example.com")
		settings.db_set("api_key", "test_key")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "test"}).insert(ignore_permissions=True)
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Resume PB",
			"document_type": "ToDo",
			"provider": "n8n"
		}).insert(ignore_permissions=True)

		exec_doc = frappe.get_doc({
			"doctype": "Playbook Execution",
			"name": f"test-resume-{frappe.generate_hash(length=8)}",
			"playbook": pb.name,
			"reference_doctype": "ToDo",
			"reference_name": todo.name,
			"status": "running"
		}).insert(ignore_permissions=True, ignore_links=True)

		resume_execution("https://n8n.example.com/resume/123", {"data": "val"}, execution_id=exec_doc.name)
		exec_doc.reload()
		self.assertEqual(exec_doc.status, "error")
