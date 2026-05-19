# pywizlabs

Reusable Python helpers for Wiz Instruqt labs — authenticating to the Wiz API, managing ephemeral Keycloak IdP users, driving the Instruqt agent CLI, and the assorted glue (Kubernetes, ServiceNow, password generation, credential-tab HTML, etc.) that lab lifecycle scripts need.

## Installation

```
pip install git+https://github.com/jtitra/pywizlabs.git#egg=pywizlabs
```

## Usage

```python
from pywizlabs import wiz, keycloak, utils

token = wiz.get_wiz_api_token(client_id, client_secret)
if wiz.verify_wiz_login("us100", token, "user@example.com"):
    print("User has signed in.")
```

## Modules

- **`pywizlabs.wiz`** — Wiz GraphQL API helpers: `get_wiz_api_token`, `verify_wiz_login`, `delete_wiz_user`, `get_user_creations`, `process_deletions`, `build_wiz_api_url`.
- **`pywizlabs.keycloak`** — Keycloak admin helpers used to provision/teardown ephemeral lab IdP users.
- **`pywizlabs.utils.instruqt`** — Thin wrappers over the Instruqt `agent` CLI: `get_agent_variable`, `set_agent_variable`, `raise_lab_failure_message`.
- **`pywizlabs.utils.k8s`** — Helpers for waiting on the Kubernetes API, applying manifests, and creating secrets inside the lab sandbox.
- **`pywizlabs.utils.misc`** — Lab-side utilities: password generation, credential-tab HTML rendering, Jinja2 templating from URLs, YAML/pipeline validators, and GCS persistence of manual-cleanup artifacts (`persist_to_gcs`).
- **`pywizlabs.utils.servicenow`** — Optional ServiceNow user/group helpers for labs that target SNOW.

## Documentation

https://jtitra.github.io/pywizlabs/

## License

Apache License 2.0 — see [LICENSE](LICENSE).
