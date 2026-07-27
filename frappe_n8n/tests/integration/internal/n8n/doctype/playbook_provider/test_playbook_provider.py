import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
import requests

class TestN8nPlaybookProvider(IntegrationTestCase):
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.settings = frappe.get_doc("n8n Settings")
        self.settings.db_set("enabled", 1)
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

    @patch("requests.get")
    def test_retrieve_workflow_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
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
        mock_get.assert_called_once_with(
            "https://n8n.example.com/api/v1/workflows/stale-wf-999",
            headers={"X-N8N-API-KEY": "test_api_key", "Accept": "application/json"},
            timeout=10
        )

    @patch("frappe_n8n.n8n.doctype.playbook.playbook.enqueue_create_workflow")
    @patch("requests.get")
    def test_retrieve_workflow_404_resets_id_and_reprovisions(self, mock_get, mock_enqueue):
        response = MagicMock()
        response.status_code = 404
        mock_get.side_effect = requests.exceptions.HTTPError(response=response)

        from frappe_n8n.n8n.doctype.playbook_provider.playbook_provider import retrieve_workflow

        # Act
        result = retrieve_workflow(self.playbook.name)

        # Assert
        self.assertIsNone(result)
        
        # Verify n8n_workflow_id was cleared in DB
        self.playbook.reload()
        self.assertIsNone(self.playbook.n8n_workflow_id)

        # Verify reprovisioning creation job was enqueued
        mock_enqueue.assert_called_once_with(self.playbook.name)

    @patch("frappe_n8n.n8n.doctype.playbook.playbook.enqueue_create_workflow")
    @patch("requests.get")
    def test_update_a_playbook_handles_404_gracefully(self, mock_get, mock_enqueue):
        response = MagicMock()
        response.status_code = 404
        mock_get.side_effect = requests.exceptions.HTTPError(response=response)

        from frappe_n8n.n8n.doctype.playbook_provider.playbook_provider import update_a_playbook

        # Act (should not throw 404 exception or fail the job)
        update_a_playbook(self.playbook.name)

        # Assert
        self.playbook.reload()
        self.assertIsNone(self.playbook.n8n_workflow_id)
        mock_enqueue.assert_called_once_with(self.playbook.name)
