app_name = "frappe_n8n"
app_title = "Frappe n8n"
app_publisher = "Aurumor"
app_description = "n8n Provider Plugin for Frappe Playbook"
app_email = "hello@aurumor.com"
app_license = "mit"

required_apps = ["frappe_playbook", "frappe_controller"]

after_install = "frappe_n8n.install.after_install"

scheduler_events = {
    "all": [
        "frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.enqueue_update_playbooks"
    ],
    "cron": {
        "0 0 1 */3 *": [
            "frappe_n8n.n8n.doctype.n8n_settings.n8n_settings.enqueue_rotate_credentials"
        ]
    }
}

controller_events = {
    "frappe_n8n.integrations.n8n.update_credential": {},
    "frappe_n8n.integrations.n8n.rotate_credentials": {},
    "frappe_n8n.integrations.n8n.create_workflow": {},
    "frappe_n8n.integrations.n8n.move_workflow": {},
    "frappe_n8n.integrations.n8n.enable_workflow": {},
    "frappe_n8n.integrations.n8n.disable_workflow": {},
    "frappe_n8n.integrations.n8n.delete_workflow": {},
    "frappe_n8n.integrations.n8n.trigger_execution": {},
    "frappe_n8n.integrations.n8n.stop_execution": {},
    "frappe_n8n.integrations.n8n.resume_execution": {},
    "frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.update_a_playbook": {},
    "frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.trigger_execution": {},
    "frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.resume_execution": {}
}

doc_events = {
    "Playbook Provider": {
        "on_update": "frappe_n8n.n8n.doctype.playbook_provider.playbook_provider.on_update"
    },
    "Playbook": {
        "on_update": "frappe_n8n.n8n.doctype.playbook.playbook.on_update",
        "on_trash": "frappe_n8n.n8n.doctype.playbook.playbook.on_trash"
    },
    "Playbook Execution": {
        "after_insert": "frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.after_insert",
        "on_update": "frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.on_update"
    },
    "ToDo": {
        "on_update": "frappe_n8n.n8n.doctype.todo.todo.on_update"
    }
}

override_whitelisted_methods = {
    "frappe_playbook.playbook.doctype.playbook.playbook.get_builder_url": "frappe_n8n.n8n.doctype.playbook.playbook.get_builder_url",
    "frappe_playbook.playbook.doctype.playbook.playbook.trigger_test_execution": "frappe_n8n.n8n.doctype.playbook.playbook.trigger_test_execution",
    "frappe_playbook.playbook.doctype.playbook_execution.playbook_execution.get_debug_url": "frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.get_debug_url",
    "frappe_playbook.playbook.doctype.playbook_execution.playbook_execution.replay": "frappe_n8n.n8n.doctype.playbook_execution.playbook_execution.replay"
}

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "n8n"]]}
]
