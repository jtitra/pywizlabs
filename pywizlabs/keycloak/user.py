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


def create_keycloak_user(keycloak_endpoint, keycloak_realm, keycloak_token, user_email, user_name, user_pwd):
    """
    Creates a user in Keycloak.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak token.
    :param user_email: The email of the user to create.
    :param user_name: The name of the user to create.
    :param user_pwd: The password of the user to create.
    """
    url = f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {keycloak_token}"
    }
    payload = {
        "email": user_email,
        "username": user_email,
        "firstName": user_name,
        "lastName": "Student",
        "emailVerified": True,
        "enabled": True,
        "requiredActions": [],
        "groups": [],
        "credentials": [
            {
                "type": "password",
                "value": user_pwd,
                "temporary": False
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    response_code = response.status_code

    print(f"[KEYCLOAK] HTTP status code: {response_code}")

    if response_code != 201:
        print(f"[KEYCLOAK] The user creation API is not returning 201... this was the response: {response_code}")
        raise SystemExit(1)


def get_keycloak_user_id(keycloak_endpoint, keycloak_realm, keycloak_token, search_term):
    """
    Gets the Keycloak user ID based on the search term.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak token.
    :param search_term: The term to search for the user.
    :return: The user ID if found, otherwise None.
    """
    url = f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users?briefRepresentation=true&first=0&max=11&search={search_term}"
    headers = {
        "Authorization": f"Bearer {keycloak_token}"
    }

    response = requests.get(url, headers=headers)
    response_data = response.json()
    user_id = response_data[0].get("id") if response_data else None

    print(f"[KEYCLOAK] Keycloak User ID: {user_id}")
    return user_id


def add_keycloak_user_to_group(keycloak_endpoint, keycloak_realm, keycloak_token, user_email, group_name):
    """
    Adds an existing Keycloak user to a group by name. Resolves both the user
    (by email) and the group (by exact name) before issuing the PUT join.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak admin token.
    :param user_email: The email of the user to add (used as the search term).
    :param group_name: The exact name of the Keycloak group the user should join.
    :raises SystemExit: If the user or group cannot be found, or the join fails.
    """
    user_id = get_keycloak_user_id(keycloak_endpoint, keycloak_realm, keycloak_token, user_email)
    if not user_id:
        raise SystemExit(f"Could not find Keycloak user '{user_email}'")

    headers = {"Authorization": f"Bearer {keycloak_token}"}

    group_response = requests.get(
        f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/groups",
        headers=headers,
        params={"search": group_name, "exact": "true"},
        timeout=10,
    )
    group_response.raise_for_status()
    groups = group_response.json()
    if not groups:
        raise SystemExit(
            f"Keycloak group '{group_name}' not found in realm '{keycloak_realm}'. "
            "Create it in the admin console first."
        )
    group_id = groups[0]["id"]

    join_response = requests.put(
        f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users/{user_id}/groups/{group_id}",
        headers=headers,
        timeout=10,
    )
    join_response.raise_for_status()
    print(f"[KEYCLOAK] Added '{user_email}' to Keycloak group '{group_name}'")


def delete_keycloak_user(keycloak_endpoint, keycloak_realm, keycloak_token, user_email, cleanup=False):
    """
    Deletes a user from Keycloak based on their email.

    :param keycloak_endpoint: The Keycloak endpoint.
    :param keycloak_realm: The Keycloak realm.
    :param keycloak_token: The Keycloak token.
    :param user_email: The email of the user to delete.
    :param cleanup: Flag to continue the cleanup process on failure.
    """
    user_id = get_keycloak_user_id(keycloak_endpoint, keycloak_realm, keycloak_token, user_email)
    if not user_id:
        print("[KEYCLOAK] Failed to determine the User ID.")
    else:
        print(f"[KEYCLOAK] Deleting Keycloak User ID: {user_id}")
        url = f"{keycloak_endpoint}/admin/realms/{keycloak_realm}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {keycloak_token}"
        }

        response = requests.delete(url, headers=headers)
        response_code = response.status_code

        print(f"[KEYCLOAK] HTTP status code: {response_code}")

        if response_code != 204:
            print(f"[KEYCLOAK] The user deletion API is not returning 204... this was the response: {response_code}")
            if cleanup:
                print("[KEYCLOAK] Attempting to continue the cleanup process...")
            else:
                raise SystemExit(1)
