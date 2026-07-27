# Copyright (c) 2026, Aurumor and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock, patch
import requests
import frappe
from frappe_n8n.integrations.n8n import (
	N8nClient,
	N8nError,
	N8nNotFoundError,
)


class TestN8nClient(unittest.TestCase):
	def setUp(self):
		self.base_url = "http://n8n.test:5678/"
		self.api_key = "test-api-key"
		self.client = N8nClient(self.base_url, self.api_key)

	def test_n8n_client_request_headers_and_base_url_normalization(self):
		self.assertEqual(self.client.base_url, "http://n8n.test:5678")
		self.assertEqual(self.client.headers["X-N8N-API-KEY"], self.api_key)
		self.assertEqual(self.client.headers["Accept"], "application/json")
		self.assertEqual(self.client.headers["Content-Type"], "application/json")

	@patch("frappe_n8n.integrations.n8n.get_n8n_config")
	def test_n8n_client_from_settings_authorized(self, mock_get_config):
		mock_get_config.return_value = {
			"enabled": True,
			"status": "Authorized",
			"base_url": "http://n8n.test:5678",
			"api_key": "valid-key"
		}
		client = N8nClient.from_settings(wait_if_unauthorized=False)
		self.assertIsNotNone(client)
		self.assertEqual(client.base_url, "http://n8n.test:5678")

	@patch("frappe_n8n.integrations.n8n.get_n8n_config")
	def test_n8n_client_from_settings_unauthorized_returns_none_in_sync_context(self, mock_get_config):
		mock_get_config.return_value = {
			"enabled": False,
			"status": "Unauthorized",
			"base_url": "http://n8n.test:5678",
			"api_key": "invalid-key"
		}
		client = N8nClient.from_settings(wait_if_unauthorized=False)
		self.assertIsNone(client)

	@patch("frappe_n8n.integrations.n8n.frappe")
	@patch("frappe_n8n.integrations.n8n.controller.wait_for_event")
	@patch("frappe_n8n.integrations.n8n.get_n8n_config")
	def test_n8n_client_from_settings_unauthorized_suspends_in_bg_job(self, mock_get_config, mock_wait, mock_frappe):
		mock_frappe.flags.current_job_id = "job-123"
		mock_get_config.side_effect = [
			{"enabled": True, "status": "Unauthorized", "base_url": "http://n8n.test", "api_key": "k"},
			{"enabled": True, "status": "Authorized", "base_url": "http://n8n.test", "api_key": "k"}
		]
		client = N8nClient.from_settings(wait_if_unauthorized=True)
		mock_wait.assert_called_once_with("doc:n8n Settings:authorized")
		self.assertIsNotNone(client)

	@patch("requests.get")
	def test_n8n_client_request_translates_404_to_n8n_not_found_error(self, mock_get):
		mock_res = MagicMock()
		mock_res.status_code = 404
		mock_get.return_value = mock_res
		with self.assertRaises(N8nNotFoundError):
			self.client._request("GET", "/api/v1/workflows/non-existent")

	@patch("requests.get")
	def test_n8n_client_request_translates_500_to_n8n_error(self, mock_get):
		mock_res = MagicMock()
		mock_res.status_code = 500
		mock_res.text = "Internal Server Error"
		mock_get.return_value = mock_res
		with self.assertRaises(N8nError):
			self.client._request("GET", "/api/v1/workflows/123")

	@patch("requests.get")
	def test_n8n_client_get_personal_project_id(self, mock_get):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {
			"data": [
				{"id": "proj-1", "type": "team"},
				{"id": "proj-2", "type": "personal"}
			]
		}
		mock_get.return_value = mock_res
		project_id = self.client.get_personal_project_id()
		self.assertEqual(project_id, "proj-2")

	@patch("requests.get")
	def test_n8n_client_get_credentials(self, mock_get):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {"data": [{"id": "cred-1", "name": "cred"}]}
		mock_get.return_value = mock_res
		creds = self.client.get_credentials()
		self.assertEqual(len(creds), 1)

	@patch("requests.post")
	def test_n8n_client_create_credential(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {"id": "new-cred-123"}
		mock_post.return_value = mock_res
		cred_id = self.client.create_credential("crm_key", "sec-token")
		self.assertEqual(cred_id, "new-cred-123")

	@patch("requests.patch")
	def test_n8n_client_update_credential(self, mock_patch):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {"id": "cred-123", "name": "crm_n8n_api_key"}
		mock_patch.return_value = mock_res
		res = self.client.update_credential("cred-123", "sec-token")
		self.assertEqual(res["id"], "cred-123")

	@patch("requests.put")
	def test_n8n_client_move_credential(self, mock_put):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_put.return_value = mock_res
		self.client.move_credential("cred-123", "proj-456")
		mock_put.assert_called_once()

	@patch("requests.get")
	def test_n8n_client_get_workflow(self, mock_get):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {"id": "wf-123", "name": "Test Workflow"}
		mock_get.return_value = mock_res
		wf = self.client.get_workflow("wf-123")
		self.assertEqual(wf["id"], "wf-123")

	@patch("requests.post")
	def test_n8n_client_create_workflow(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {"id": "wf-new-123"}
		mock_post.return_value = mock_res
		wf = self.client.create_workflow("New Workflow")
		self.assertEqual(wf["id"], "wf-new-123")

	@patch("requests.put")
	def test_n8n_client_move_workflow(self, mock_put):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_put.return_value = mock_res
		self.client.move_workflow("wf-123", "proj-789")
		mock_put.assert_called_once()

	@patch("requests.post")
	def test_n8n_client_activate_workflow(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_post.return_value = mock_res
		self.client.activate_workflow("wf-123")
		mock_post.assert_called_once()

	@patch("requests.post")
	def test_n8n_client_deactivate_workflow(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_post.return_value = mock_res
		self.client.deactivate_workflow("wf-123")
		mock_post.assert_called_once()

	@patch("requests.delete")
	def test_n8n_client_delete_workflow(self, mock_delete):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_delete.return_value = mock_res
		self.client.delete_workflow("wf-123")
		mock_delete.assert_called_once()

	@patch("requests.post")
	def test_n8n_client_stop_execution(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_res.json.return_value = {"status": "stopped"}
		mock_post.return_value = mock_res
		res = self.client.stop_execution("exec-123")
		self.assertEqual(res["status"], "stopped")

	@patch("requests.post")
	def test_n8n_client_trigger_execution(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_post.return_value = mock_res
		res = self.client.trigger_execution("hook-1", {"a": 1}, "exec-1", webhook_security="sec")
		self.assertEqual(res.status_code, 200)

	@patch("requests.post")
	def test_n8n_client_trigger_test_execution(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_post.return_value = mock_res
		res = self.client.trigger_test_execution("hook-1", {"a": 1}, "test-exec-1", webhook_security="sec")
		self.assertEqual(res.status_code, 200)

	@patch("requests.post")
	def test_n8n_client_resume_execution(self, mock_post):
		mock_res = MagicMock()
		mock_res.status_code = 200
		mock_post.return_value = mock_res
		res = self.client.resume_execution("http://n8n.test/resume/123", {"a": 1}, webhook_security="sec")
		self.assertEqual(res.status_code, 200)
