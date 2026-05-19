# Copyright 2026 Wiz Technical Experiences.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Standard imports
#   None

# Third-party imports
import requests

# Library-specific imports
#   None


def generate_keycloak_token(keycloak_endpoint, keycloak_admin_user, keycloak_admin_pwd, cleanup=False):
    """
    Generates a Keycloak bearer token.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_admin_user: The Keycloak admin username.
    :param keycloak_admin_pwd: The Keycloak admin password.
    :param cleanup: When True, return None on failure instead of exiting — lets a
        cleanup script keep trying other teardown steps even if Keycloak is unreachable.
    :return: The Keycloak token if successful, otherwise None when cleanup=True.
    """
    url = f"{keycloak_endpoint}/realms/master/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "username": keycloak_admin_user,
        "password": keycloak_admin_pwd,
        "grant_type": "password",
        "client_id": "admin-cli",
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code != 200:
        print(f"Keycloak token API call failed (HTTP {response.status_code}): {response.text}")
        if cleanup:
            return None
        raise SystemExit(1)

    keycloak_token = response.json().get("access_token")
    if not keycloak_token:
        print(f"Keycloak token response missing access_token: {response.json()}")
        if cleanup:
            return None
        raise SystemExit(1)

    print("Token generation complete")
    return keycloak_token
