## Improvements

* **Error Message Matching**
  * Description: Replaced hardcoded string checks with a list-based approach for detecting transfer errors, adding support for "already owning" and "already owns" variations.
  * Commits: [64bd9ab](https://github.com/aurumorinc/frappe-n8n/commit/64bd9abe), [8bd73e0](https://github.com/aurumorinc/frappe-n8n/commit/8bd73e01)

* **Idempotent Move Tests**
  * Description: Added test cases to verify that moving credentials and workflows to their already-owning project does not raise an exception, handling 400 responses gracefully.
  * Commits: [ea84fcd](https://github.com/aurumorinc/frappe-n8n/commit/ea84fcd2)
