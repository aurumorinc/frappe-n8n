# Copyright (c) 2026, Aurumor and contributors
# For license information, please see license.txt

import json
import unittest
from unittest.mock import MagicMock
from frappe.tests import UnitTestCase
from frappe_n8n.playbook_execution import _apply_payload_to_execution_doc, DISALLOWED_FIELDS


class TestCallbackPayload(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		try:
			super().setUpClass()
		except Exception:
			pass

	def setUp(self):
		self.mock_doc = MagicMock()
		self.mock_doc.meta.has_field.side_effect = lambda field: field in {"status", "execution_data", "n8n_execution_id", "custom_field"}
		self.mock_doc._values = {}

		def mock_set(key, val):
			self.mock_doc._values[key] = val

		self.mock_doc.set.side_effect = mock_set

	def test_apply_payload_filters_disallowed_fields(self):
		payload = {
			"name": "malicious-name",
			"owner": "hacker@example.com",
			"status": "success",
			"doctype": "Playbook Execution",
			"custom_field": "valid_value"
		}
		_apply_payload_to_execution_doc(self.mock_doc, payload)

		for field in DISALLOWED_FIELDS:
			self.assertNotIn(field, self.mock_doc._values)

		self.assertEqual(self.mock_doc._values.get("status"), "success")
		self.assertEqual(self.mock_doc._values.get("custom_field"), "valid_value")

	def test_apply_payload_serializes_dict_execution_data(self):
		payload = {
			"status": "completed",
			"execution_data": {"result": "ok", "count": 42}
		}
		_apply_payload_to_execution_doc(self.mock_doc, payload)

		self.assertEqual(
			self.mock_doc._values.get("execution_data"),
			json.dumps({"result": "ok", "count": 42})
		)

	def test_apply_payload_extracts_nested_n8n_execution_id(self):
		payload = {
			"status": "completed",
			"execution": {"id": "n8n-exec-999"}
		}
		_apply_payload_to_execution_doc(self.mock_doc, payload)

		self.assertEqual(self.mock_doc.n8n_execution_id, "n8n-exec-999")
