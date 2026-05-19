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


def create_user(sn_instance, sn_username, sn_password, first_name, last_name, user_name, email, password):
    """
    Creates a ServiceNow user via the sys_user table API.

    :param sn_instance: The ServiceNow instance name.
    :param sn_username: The ServiceNow username.
    :param sn_password: The ServiceNow password.
    :param first_name: The first name of the user.
    :param last_name: The last name of the user.
    :param user_name: The username for the new user.
    :param email: The email address of the user.
    :param password: The password for the user.
    :return: The sys_id of the newly created user.
    """
    sn_base_url = f"https://{sn_instance}.service-now.com"
    url = f"{sn_base_url}/api/now/table/sys_user?sysparm_input_display_value=true"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "user_name": user_name,
        "email": email,
        "user_password": password,
    }

    response = requests.post(url, auth=(sn_username, sn_password),
                             headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()
    sys_id = data["result"]["sys_id"]
    print(f"User created with sys_id: {sys_id}")
    return sys_id


def delete_user(sn_instance, sn_username, sn_password, sys_id):
    """
    Deletes a ServiceNow user by sys_id via the sys_user table API.

    :param sn_instance: The ServiceNow instance name.
    :param sn_username: The ServiceNow username.
    :param sn_password: The ServiceNow password.
    :param sys_id: The sys_id of the user to be deleted.
    :return: None
    """
    sn_base_url = f"https://{sn_instance}.service-now.com"
    url = f"{sn_base_url}/api/now/table/sys_user/{sys_id}"
    response = requests.delete(url, auth=(sn_username, sn_password))
    response.raise_for_status()
    print(f"User with sys_id {sys_id} deleted.")


def add_user_to_group(sn_instance, sn_username, sn_password, user_sys_id, group_name="Workshop Users"):
    """
    Adds a user to a group via the sys_user_grmember table API.

    :param sn_instance: The ServiceNow instance name.
    :param sn_username: The ServiceNow username.
    :param sn_password: The ServiceNow password.
    :param user_sys_id: The sys_id of the user to add to the group.
    :param group_name: The name of the group (default is "Workshop Users").
    :return: The sys_id of the membership record created.
    """
    sn_base_url = f"https://{sn_instance}.service-now.com"
    group_url = f"{sn_base_url}/api/now/table/sys_user_group?sysparm_query=name={group_name}"
    group_response = requests.get(group_url, auth=(sn_username, sn_password))
    group_response.raise_for_status()

    group_data = group_response.json().get("result", [])
    if not group_data:
        raise ValueError(f"Group '{group_name}' not found!")
    group_sys_id = group_data[0]["sys_id"]

    membership_url = f"{sn_base_url}/api/now/table/sys_user_grmember"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "group": group_sys_id,
        "user": user_sys_id
    }
    membership_response = requests.post(membership_url, auth=(sn_username, sn_password),
                                        headers=headers, json=payload)
    membership_response.raise_for_status()

    membership_sys_id = membership_response.json()["result"]["sys_id"]
    print(f"User {user_sys_id} added to group '{group_name}' with membership sys_id: {membership_sys_id}")
    return membership_sys_id
