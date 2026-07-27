# Copyright (c) 2026, Aquiveal and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from frappe_controller.utils import controller


def get_n8n_config() -> dict:
	settings = frappe.get_single("n8n Settings")
	try:
		settings.reload()
	except Exception:
		pass

	base_url = frappe.conf.get("n8n_base_url") or getattr(settings, "base_url", None) or ""
	api_key = frappe.conf.get("n8n_api_key") or settings.get_password("api_key", raise_exception=False) or getattr(settings, "api_key", None) or ""
	webhook_security = frappe.conf.get("n8n_webhook_security") or settings.get_password("webhook_security", raise_exception=False) or getattr(settings, "webhook_security", None) or ""
	project_id = frappe.conf.get("n8n_project_id") or getattr(settings, "project_id", None) or ""

	conf_enabled = frappe.conf.get("n8n_enabled")
	enabled = bool(conf_enabled) if conf_enabled is not None else bool(getattr(settings, "enabled", 0))

	raw_status = getattr(settings, "status", None)
	if raw_status == "Unauthorized":
		status = "Unauthorized"
	elif enabled:
		status = "Authorized"
	else:
		status = "Disabled"

	return {
		"base_url": base_url,
		"api_key": api_key,
		"webhook_security": webhook_security,
		"project_id": project_id,
		"enabled": enabled,
		"status": status,
	}


class N8nError(requests.exceptions.HTTPError):
	def __init__(self, message: str, status_code: int | None = None, response: requests.Response | None = None):
		super().__init__(message, response=response)
		self.status_code = status_code


class N8nNotFoundError(N8nError):
	pass


class N8nClient:
	def __init__(self, base_url: str, api_key: str):
		self.base_url = base_url.rstrip("/") if base_url else ""
		self.api_key = api_key
		self.headers = {
			"X-N8N-API-KEY": self.api_key,
			"Accept": "application/json",
			"Content-Type": "application/json",
		}

	@classmethod
	def from_settings(cls, wait_if_unauthorized: bool = True) -> "N8nClient | None":
		config = get_n8n_config()
		if not config["enabled"] or config["status"] != "Authorized":
			if wait_if_unauthorized and getattr(frappe.flags, "current_job_id", None):
				controller.wait_for_event("doc:n8n Settings:authorized")
				config = get_n8n_config()
			if not config["enabled"] or config["status"] != "Authorized":
				return None

		if not config["base_url"] or not config["api_key"]:
			return None

		return cls(config["base_url"], config["api_key"])

	def _request(self, method: str, path: str, **kwargs) -> requests.Response:
		url = f"{self.base_url}{path}"
		headers = kwargs.pop("headers", self.headers)
		try:
			method_lower = method.lower()
			if hasattr(requests, method_lower):
				func = getattr(requests, method_lower)
				res = func(url, headers=headers, timeout=10, **kwargs)
			else:
				res = requests.request(method, url, headers=headers, timeout=10, **kwargs)
			if res.status_code == 404:
				raise N8nNotFoundError("Resource not found", status_code=404, response=res)
			if res.status_code >= 400:
				raise N8nError(f"n8n API error: {res.status_code} - {res.text}", status_code=res.status_code, response=res)
			return res
		except N8nError:
			raise
		except requests.exceptions.RequestException as e:
			if getattr(e, "response", None) is not None and e.response.status_code == 404:
				raise N8nNotFoundError("Resource not found", status_code=404, response=e.response) from e
			raise N8nError(f"n8n HTTP request failed: {str(e)}", response=getattr(e, "response", None)) from e

	def get_personal_project_id(self) -> str | None:
		res = self._request("GET", "/api/v1/projects")
		data = res.json()
		items = data.get("data", data) if isinstance(data, dict) else data
		if isinstance(items, list):
			for item in items:
				if isinstance(item, dict) and item.get("type") == "personal":
					return item.get("id")
		return None

	def update_credential(self, credential_id: str, webhook_security: str) -> dict:
		payload = {
			"name": "crm_n8n_api_key",
			"type": "httpHeaderAuth",
			"data": {
				"name": "Authorization",
				"value": f"Bearer {webhook_security}"
			}
		}
		res = self._request("PATCH", f"/api/v1/credentials/{credential_id}", json=payload)
		return res.json()

	def get_credentials(self) -> list[dict]:
		res = self._request("GET", "/api/v1/credentials")
		data = res.json()
		return data.get("data", data) if isinstance(data, dict) else data

	def create_credential(self, name: str, webhook_security: str) -> str:
		payload = {
			"name": name,
			"type": "httpHeaderAuth",
			"data": {
				"name": "Authorization",
				"value": f"Bearer {webhook_security}"
			}
		}
		res = self._request("POST", "/api/v1/credentials", json=payload)
		data = res.json()
		return data.get("id")

	def move_credential(self, credential_id: str, destination_project_id: str) -> None:
		payload = {"destinationProjectId": destination_project_id}
		self._request("PUT", f"/api/v1/credentials/{credential_id}/transfer", json=payload)

	def create_workflow(self, name: str, nodes: list | None = None, connections: dict | None = None, settings: dict | None = None) -> dict:
		payload = {
			"name": name,
			"nodes": nodes or [],
			"connections": connections or {},
			"settings": settings or {}
		}
		res = self._request("POST", "/api/v1/workflows", json=payload)
		return res.json()

	def move_workflow(self, workflow_id: str, destination_project_id: str) -> None:
		payload = {"destinationProjectId": destination_project_id}
		self._request("PUT", f"/api/v1/workflows/{workflow_id}/transfer", json=payload)

	def activate_workflow(self, workflow_id: str) -> None:
		self._request("POST", f"/api/v1/workflows/{workflow_id}/activate")

	def deactivate_workflow(self, workflow_id: str) -> None:
		self._request("POST", f"/api/v1/workflows/{workflow_id}/deactivate")

	def delete_workflow(self, workflow_id: str) -> None:
		try:
			self._request("DELETE", f"/api/v1/workflows/{workflow_id}")
		except N8nNotFoundError:
			frappe.log_error("Workflow already deleted in n8n (404).", "n8n Integration Error")


def update_credential():
	config = get_n8n_config()
	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return

	webhook_security = config["webhook_security"]
	settings = frappe.get_single("n8n Settings")
	if not webhook_security:
		webhook_security = frappe.generate_hash(length=32)
		settings.db_set("webhook_security", webhook_security)
		settings.webhook_security = webhook_security

	credential_exists = False
	if settings.webhook_credential_id:
		try:
			client.update_credential(settings.webhook_credential_id, webhook_security)
			credential_exists = True
		except N8nNotFoundError:
			settings.db_set("webhook_credential_id", None)
			settings.webhook_credential_id = None
			credential_exists = False
		except Exception as e:
			frappe.log_error(f"Failed to update credential: {str(e)}", "n8n Integration Error")
			raise

	if not credential_exists:
		try:
			credentials = client.get_credentials()
			for cred in credentials:
				if cred.get("name") == "crm_n8n_api_key":
					try:
						client.update_credential(cred["id"], webhook_security)
						settings.db_set("webhook_credential_id", cred["id"])
						settings.webhook_credential_id = cred["id"]
						credential_exists = True
						break
					except N8nNotFoundError:
						pass
		except Exception:
			pass

	if not credential_exists:
		try:
			new_id = client.create_credential("crm_n8n_api_key", webhook_security)
			settings.db_set("webhook_credential_id", new_id)
			settings.webhook_credential_id = new_id
			settings.db_set("webhook_secret_updated", frappe.utils.now_datetime())
			credential_exists = True
		except Exception as e:
			frappe.log_error(f"Failed to create credential: {str(e)}", "n8n Integration Error")
			raise

	destination_project_id = config["project_id"] or client.get_personal_project_id()
	if destination_project_id and settings.webhook_credential_id:
		try:
			client.move_credential(settings.webhook_credential_id, destination_project_id)
		except N8nNotFoundError:
			settings.db_set("webhook_credential_id", None)
			settings.webhook_credential_id = None
			new_id = client.create_credential("crm_n8n_api_key", webhook_security)
			settings.db_set("webhook_credential_id", new_id)
			settings.webhook_credential_id = new_id
			client.move_credential(new_id, destination_project_id)

	controller.emit_event(key="n8n_credential_ready", argument={"status": "success"})


def rotate_credentials():
	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return

	settings = frappe.get_single("n8n Settings")
	new_webhook_security = frappe.generate_hash(length=32)
	if settings.webhook_credential_id:
		try:
			client.update_credential(settings.webhook_credential_id, new_webhook_security)
		except N8nNotFoundError:
			update_credential()
			return
	else:
		update_credential()
		return

	settings.db_set("webhook_security", new_webhook_security)
	settings.db_set("webhook_secret_updated", frappe.utils.now_datetime())
	controller.emit_event(key="n8n_credential_ready", argument={"status": "success"})


def create_workflow(playbook_name: str):
	playbook_doc = frappe.get_doc("Playbook", playbook_name)
	if playbook_doc.n8n_workflow_id:
		return playbook_doc.n8n_workflow_id

	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return None

	config = get_n8n_config()
	nodes = []
	connections = {}
	settings_cfg = {}

	try:
		wf = client.create_workflow(
			name=getattr(playbook_doc, "playbook_name", None) or playbook_doc.name,
			nodes=nodes,
			connections=connections,
			settings=settings_cfg
		)
		workflow_id = wf.get("id")

		if config["project_id"]:
			try:
				client.move_workflow(workflow_id, config["project_id"])
			except N8nNotFoundError:
				pass

		vue_flow_data = {
			"nodes": wf.get("nodes", []),
			"connections": wf.get("connections", {})
		}
		playbook_doc.db_set("playbook_data", json.dumps(vue_flow_data))

		playbook_doc.set("nodes", [])
		for node in wf.get("nodes", []):
			playbook_doc.append("nodes", {
				"node_name": node.get("name"),
				"node_type": node.get("type"),
				"disabled": node.get("disabled", False),
				"retry_on_fail": node.get("retryOnFail", False),
				"on_error": node.get("onError", ""),
				"n8n_node_id": node.get("id"),
				"n8n_webhook_id": node.get("webhookId", "")
			})

		for child in playbook_doc.get("nodes"):
			child.db_insert()

		playbook_doc.db_set("n8n_workflow_id", workflow_id)
		controller.emit_event(key="n8n_workflow_created", argument={"playbook_name": playbook_doc.name})

		if playbook_doc.enabled:
			enable_workflow(playbook_name)

		return workflow_id
	except Exception as e:
		frappe.log_error(f"Failed to create n8n workflow: {str(e)}", "n8n Integration Error")
		raise


def move_workflow(playbook_name: str, project_id: str):
	playbook_doc = frappe.get_doc("Playbook", playbook_name)
	if not playbook_doc.n8n_workflow_id:
		return create_workflow(playbook_name)

	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return None

	try:
		client.move_workflow(playbook_doc.n8n_workflow_id, project_id)
	except N8nNotFoundError:
		playbook_doc.db_set("n8n_workflow_id", None)
		playbook_doc.n8n_workflow_id = None
		return create_workflow(playbook_name)


def enable_workflow(playbook_name: str):
	playbook_doc = frappe.get_doc("Playbook", playbook_name)
	if not playbook_doc.n8n_workflow_id:
		return None

	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return None

	try:
		client.activate_workflow(playbook_doc.n8n_workflow_id)
	except N8nNotFoundError:
		playbook_doc.db_set("n8n_workflow_id", None)
		playbook_doc.n8n_workflow_id = None
		return create_workflow(playbook_name)


def disable_workflow(playbook_name: str):
	playbook_doc = frappe.get_doc("Playbook", playbook_name)
	if not playbook_doc.n8n_workflow_id:
		return None

	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return None

	try:
		client.deactivate_workflow(playbook_doc.n8n_workflow_id)
	except N8nNotFoundError:
		playbook_doc.db_set("n8n_workflow_id", None)
		playbook_doc.n8n_workflow_id = None


def delete_workflow(workflow_id: str):
	client = N8nClient.from_settings(wait_if_unauthorized=True)
	if not client:
		return
	client.delete_workflow(workflow_id)
