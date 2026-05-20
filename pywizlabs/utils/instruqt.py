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
import subprocess

# Third-party imports
#   None

# Library-specific imports
#   None


def get_agent_variable(variable_name):
    """
    Retrieves the value of a specified variable using the 'agent variable get' command.

    :param variable_name: The name of the variable to retrieve.
    :return: The value of the specified variable as a string, or None if an error occurs.
    """
    try:
        result = subprocess.run(["agent", "variable", "get", variable_name], check=True, stdout=subprocess.PIPE, text=True)
        variable_value = result.stdout.strip()
        return variable_value
    except subprocess.CalledProcessError as e:
        print(f"[INSTRUQT] Error retrieving {variable_name}: {e}")
        return None


def set_agent_variable(variable_name, variable_value):
    """
    Sets the value of a specified variable using the 'agent variable set' command.

    :param variable_name: The name of the variable to set.
    :param variable_value: The value of the variable to set.
    """
    try:
        subprocess.run(["agent", "variable", "set", variable_name, variable_value], check=True, stdout=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[INSTRUQT] Error setting {variable_name}: {e}")


def raise_lab_failure_message(message_text):
    """
    Presents the user with a failure message after they've clicked the 'Check' button.

    :param message_text: The error/failure message to display to the workshop user.
    """
    subprocess.run(["fail-message", message_text], check=True)
