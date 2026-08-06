## Features

* **Asynchronous Playbook Execution for n8n Provider**
  * Enqueued playbook execution asynchronously using background job queueing and the `after_insert` hook for the n8n provider, improving performance and preventing blocking operations during record insertion.
  * Commits: [`3d5d396`](https://github.com/aurumorinc/frappe-n8n/commit/3d5d396d), [`fe68c46`](https://github.com/aurumorinc/frappe-n8n/commit/fe68c461), [`a1b03c0`](https://github.com/aurumorinc/frappe-n8n/commit/a1b03c04)
