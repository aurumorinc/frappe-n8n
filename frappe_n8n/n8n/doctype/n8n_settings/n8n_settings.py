# Copyright (c) 2026, Aurumor and contributors
# For license information, please see license.txt

import requests
import frappe
from frappe.model.document import Document
from frappe_controller.utils.controller import emit_event
from frappe_n8n.integrations.n8n import (
	N8nClient,
	N8nError,
	update_credential as integration_update_credential,
	rotate_credentials as integration_rotate_credentials,
)


class n8nSettings(Document):
	def validate(self):
		if not self.webhook_secret and not self.get_password("webhook_secret", raise_exception=False):
			self.webhook_secret = frappe.generate_hash(length=32)

		conf_enabled = frappe.conf.get("n8n_enabled")
		is_enabled = bool(conf_enabled) if conf_enabled is not None else bool(self.enabled)

		if is_enabled:
			base_url = frappe.conf.get("n8n_base_url") or self.base_url
			api_key = frappe.conf.get("n8n_api_key") or self.get_password("api_key", raise_exception=False) or self.api_key

			if not base_url or not api_key:
				self.enabled = 0
				self.status = "Disabled"
				frappe.msgprint("Base URL and API Key are required to enable n8n integration. Integration has been disabled.", indicator="orange", alert=True)
				return

			client = N8nClient(base_url, api_key)
			try:
				client.get_personal_project_id()
				self.status = "Authorized"
			except (N8nError, requests.exceptions.RequestException) as e:
				self.status = "Unauthorized"
				self.enabled = 0
				frappe.msgprint(f"Failed to connect to n8n. Integration disabled. Error: {str(e)}", indicator="orange", alert=True)
		else:
			self.status = "Disabled"

	def on_update(self):
		if frappe.db.exists("Playbook Provider", "n8n"):
			provider = frappe.get_doc("Playbook Provider", "n8n")
			target_enabled = 1 if (self.enabled and self.status == "Authorized") else 0
			if provider.enabled != target_enabled:
				provider.enabled = target_enabled
				provider.save(ignore_permissions=True)

		if self.enabled and self.status == "Authorized":
			emit_event(key="doc:n8n Settings:n8n Settings:authorized", argument={"status": "success"})
			frappe.enqueue("frappe_n8n.integrations.n8n.update_credential")

			if self.has_value_changed("project_id") or self.has_value_changed("base_url"):
				playbooks = frappe.get_all("Playbook", filters={"provider": "n8n"}, fields=["name"])
				for pb in playbooks:
					frappe.enqueue(
						"frappe_n8n.integrations.n8n.move_workflow",
						playbook_name=pb.name,
						project_id=self.project_id
					)


def update_webhook_credential():
	integration_update_credential()


def update_credential():
	integration_update_credential()


def rotate_credentials():
	integration_rotate_credentials()


def enqueue_rotate_credentials():
	settings = frappe.get_single("n8n Settings")
	if settings.enabled:
		from frappe_controller.utils.background_jobs import enqueue
		enqueue("frappe_n8n.n8n.doctype.n8n_settings.n8n_settings.rotate_credentials")
