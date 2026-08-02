import json
from unittest.mock import patch
import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob, process_telemetry_messages
from frappe_n8n.integrations.n8n import N8nClient, trigger_execution


class TestPlaybookLifecycle(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		cache = frappe.cache()
		cache.delete("fs:events")
		cache.delete("fs:deferred:high")
		cache.delete("fs:queue:high")
		frappe.db.delete("FS Match Condition")
		frappe.db.delete("FS Event")
		frappe.db.delete("FS Job")
		frappe.db.delete("Playbook", {"playbook_name": ["like", "Test Lifecycle PB%"]})

		settings = frappe.get_single("n8n Settings")
		settings.db_set("enabled", 1)
		settings.db_set("status", "Authorized")

		if frappe.db.exists("Playbook Provider", "n8n"):
			provider = frappe.get_doc("Playbook Provider", "n8n")
			provider.db_set("enabled", 1)

		frappe.db.commit()

		# Ensure Controller Job Type exists for trigger_execution
		method_path = "frappe_n8n.integrations.n8n.trigger_execution"
		job_type_name = frappe.db.get_value("Controller Job Type", {"method": method_path})
		if not job_type_name:
			jt = frappe.get_doc({
				"doctype": "Controller Job Type",
				"job_type_name": "Test Trigger Execution Job Type",
				"method": method_path,
				"queue": "high"
			}).insert(ignore_permissions=True)
			self.job_type_name = jt.name
			self.created_job_type = True
		else:
			self.job_type_name = job_type_name
			self.created_job_type = False

	def tearDown(self):
		frappe.flags.current_job_id = None
		frappe.db.delete("FS Match Condition")
		frappe.db.delete("FS Event")
		frappe.db.delete("FS Job")
		frappe.db.delete("Playbook", {"playbook_name": ["like", "Test Lifecycle PB%"]})
		if getattr(self, "created_job_type", False) and getattr(self, "job_type_name", None):
			frappe.db.delete("Controller Job Type", self.job_type_name)
		cache = frappe.cache()
		cache.delete("fs:events")
		cache.delete("fs:deferred:high")
		cache.delete("fs:queue:high")
		frappe.db.commit()
		super().tearDown()

	def test_disabled_playbook_fails_fast_on_execution_trigger(self):
		"""
		Verifies that triggering execution on a disabled Playbook fails fast immediately
		with ValidationError rather than suspending the job.
		"""
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": "Test Lifecycle PB Disabled",
			"document_type": "ToDo",
			"provider": "n8n",
			"enabled": 0,
			"status": "Disabled",
			"n8n_workflow_id": "wf-lifecycle-disabled"
		}).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError) as cm:
			trigger_execution(pb.name, {"data": "test"}, "exec-lifecycle-disabled")

		self.assertIn("Playbook is disabled", str(cm.exception))

	@patch.object(N8nClient, "trigger_execution")
	def test_missing_webhook_id_suspends_and_resumes_on_event(self, mock_trigger_exec):
		"""
		End-to-end integration test for in-flight webhook_id suspension & promotion:
		1. Triggering execution on an enabled Playbook missing webhook_id suspends job.
		2. An FS Match Condition is created for 'doc:Playbook:{name}:webhook_id'.
		3. Emitting the webhook_id event satisfies match condition.
		"""
		pb_name = f"Test Lifecycle PB Webhook {frappe.generate_hash(length=6)}"
		pb = frappe.get_doc({
			"doctype": "Playbook",
			"playbook_name": pb_name,
			"document_type": "ToDo",
			"provider": "n8n",
			"enabled": 1,
			"status": "Enabled",
			"n8n_workflow_id": "wf-lifecycle-wh-123",
			"nodes": []
		}).insert(ignore_permissions=True)

		job = frappe.get_doc({
			"doctype": "FS Job",
			"job_type": self.job_type_name,
			"queue": "high",
			"status": "started"
		}).insert(ignore_permissions=True)

		frappe.flags.current_job_id = job.name
		expected_event_key = f"doc:Playbook:{pb.name}:webhook_id"

		with self.assertRaises(SuspendJob) as cm:
			trigger_execution(pb.name, {"data": "test"}, "exec-lifecycle-wh")

		self.assertEqual(cm.exception.event_key, expected_event_key)

		match_conds = frappe.get_all(
			"FS Match Condition",
			filters={"job": job.name, "event_key": expected_event_key},
			fields=["name", "is_satisfied"]
		)
		self.assertEqual(len(match_conds), 1)
		self.assertEqual(match_conds[0].is_satisfied, 0)

		# Populate webhook node and emit event
		frappe.flags.in_playbook_sync = True
		try:
			pb.reload()
			pb.playbook_data = json.dumps({"nodes": [{"type": "n8n-nodes-base.webhook", "webhookId": "wh-lifecycle-ready"}]})
			pb.append("nodes", {
				"node_name": "Webhook",
				"node_type": "n8n-nodes-base.webhook",
				"n8n_webhook_id": "wh-lifecycle-ready"
			})
			pb.save(ignore_permissions=True)
		finally:
			frappe.flags.in_playbook_sync = False

		from frappe_controller.utils.controller import emit_event
		emit_event(key=expected_event_key, argument={"webhook_id": "wh-lifecycle-ready"})

		cache = frappe.cache()
		stream_data = cache.xrange("fs:events")
		messages = [("fs:events", stream_data)]
		process_telemetry_messages(cache, messages)

		satisfied_cond = frappe.get_doc("FS Match Condition", match_conds[0].name)
		self.assertEqual(satisfied_cond.is_satisfied, 1)
