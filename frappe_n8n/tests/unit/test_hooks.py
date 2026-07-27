# Copyright (c) 2026, Aurumor and contributors
# For license information, please see license.txt

import unittest
from frappe_n8n import hooks


class TestHooks(unittest.TestCase):
	def test_hooks_controller_events_contains_required_integrations(self):
		required_events = [
			"frappe_n8n.integrations.n8n.update_credential",
			"frappe_n8n.integrations.n8n.rotate_credentials",
			"frappe_n8n.integrations.n8n.create_workflow",
			"frappe_n8n.integrations.n8n.move_workflow",
			"frappe_n8n.integrations.n8n.enable_workflow",
			"frappe_n8n.integrations.n8n.disable_workflow",
			"frappe_n8n.integrations.n8n.delete_workflow",
			"frappe_n8n.integrations.n8n.trigger_execution",
			"frappe_n8n.integrations.n8n.stop_execution",
			"frappe_n8n.integrations.n8n.resume_execution",
			"frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.update_a_playbook",
			"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_execution",
			"frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.resume_execution",
		]
		controller_events = getattr(hooks, "controller_events", {})
		for event in required_events:
			self.assertIn(event, controller_events, f"Missing {event} in controller_events")
