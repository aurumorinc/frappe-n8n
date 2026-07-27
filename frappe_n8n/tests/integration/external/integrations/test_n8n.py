# Copyright (c) 2026, Aurumor and Contributors
# See license.txt

import os
import vcr
import vcr.patch
import frappe
from frappe.tests import IntegrationTestCase
from frappe_n8n.integrations.n8n import N8nClient, N8nNotFoundError


def empty_generator(*args, **kwargs):
	yield from []


vcr.patch.CassettePatcherBuilder._aiohttp = empty_generator

CASSETTES_DIR = os.path.join(os.path.dirname(__file__), "cassettes")

my_vcr = vcr.VCR(
	cassette_library_dir=CASSETTES_DIR,
	record_mode="once",
	match_on=["method", "scheme", "host", "port", "path", "query"],
)


class TestN8nExternalIntegration(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def setUp(self):
		super().setUp()
		self.client = N8nClient(base_url="https://n8n.example.com", api_key="dummy_api_key")

	@my_vcr.use_cassette("test_get_personal_project.yaml")
	def test_n8n_client_get_personal_project(self):
		project_id = self.client.get_personal_project_id()
		self.assertEqual(project_id, "proj_personal_123")

	@my_vcr.use_cassette("test_create_and_move_workflow.yaml")
	def test_n8n_client_create_and_move_workflow(self):
		wf = self.client.create_workflow(name="VCR Test Workflow")
		self.assertEqual(wf.get("id"), "wf_vcr_001")

		self.client.move_workflow("wf_vcr_001", "proj_dest_456")

	@my_vcr.use_cassette("test_404_workflow_move.yaml")
	def test_n8n_client_404_workflow_move(self):
		with self.assertRaises(N8nNotFoundError):
			self.client.move_workflow("wf_stale_999", "proj_dest_456")
