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
import os
import subprocess
import time

# Third-party imports
import requests
from kubernetes import client, utils

# Library-specific imports
from .misc import run_command


def add_k8s_service_to_hosts(service_name, namespace, hostname):
    """
    Adds a Kubernetes service IP to the /etc/hosts file.

    :param service_name: The name of the Kubernetes service.
    :param namespace: The namespace of the Kubernetes service.
    :param hostname: The hostname to map to the service IP.
    """
    retries = 0
    max_retries = 5
    retry_delay = 10  # seconds

    print(f"Adding '{service_name}' to the hosts file.")
    while retries < max_retries:
        ip_address = subprocess.getoutput(f"kubectl get service {service_name} -n {namespace} -o=jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")
        if ip_address and ip_address.lower() not in ["<none>", "none"]:
            print(f"Successfully retrieved IP address: {ip_address}")
            break
        retries += 1
        if retries == max_retries:
            print(f"Failed to retrieve IP for service {service_name} in namespace {namespace} after {max_retries} attempts.")
            return 1
        print(f"Retrying in {retry_delay} seconds... ({retries}/{max_retries})")
        time.sleep(retry_delay)

    # Update /etc/hosts
    with open("/etc/hosts", "r") as file:
        hosts_content = file.readlines()
    with open("/etc/hosts", "w") as file:
        for line in hosts_content:
            if hostname not in line:
                file.write(line)
        file.write(f"{ip_address} {hostname}\n")

    print(f"Added {hostname} with IP {ip_address} to /etc/hosts")


def get_k8s_loadbalancer_ip(service_name, namespace="default", max_attempts=15):
    """
    Retrieves the external IP of a Kubernetes LoadBalancer service.

    :param service_name: The name of the Kubernetes service.
    :param namespace: The namespace of the Kubernetes service. Default is 'default'.
    :param max_attempts: The maximum number of attempts to get the IP. Default is 15.
    :return: The external IP address of the LoadBalancer service.
    :raises SystemExit: If the IP address could not be retrieved within the maximum attempts.
    """
    print(f"Waiting for LoadBalancer IP for service {service_name}...")
    sleep_time = 5
    v1 = client.CoreV1Api()
    for attempt in range(1, max_attempts + 1):
        try:
            service = v1.read_namespaced_service(service_name, namespace)
            if service.status.load_balancer.ingress:
                external_ip = service.status.load_balancer.ingress[0].ip
                print(f"Attempt {attempt}/{max_attempts}:: Found IP {external_ip} for service {service_name}")
                return external_ip
            else:
                print(f"Attempt {attempt}/{max_attempts}:: No ingress IP found for service {service_name}. Retrying in {sleep_time} seconds...")
        except client.ApiException as e:
            print(f"Attempt {attempt}/{max_attempts}:: Failed to get service {service_name}. Error: {e}")
        time.sleep(sleep_time)
    print(f"Failed to get LoadBalancer IP for service {service_name} after {max_attempts} attempts.")
    raise SystemExit(1)


def render_manifest_from_template(template_file, output_path, apps_string):
    """
    Renders a Kubernetes manifest from a template by replacing placeholders with actual values.

    :param template_file: The path to the template file.
    :param output_path: The path where the rendered manifest will be saved.
    :param apps_string: A comma-separated string of app details in the format 'app_name:app_port:ip_address'.
    """
    def replace_values(template_file, output_file, app_name, app_port, ip_address):
        """
        Replaces placeholders in the template file with actual values and writes to the output file.

        :param template_file: The path to the template file.
        :param output_file: The path to the output file.
        :param app_name: The application name to replace in the template.
        :param app_port: The application port to replace in the template.
        :param ip_address: The IP address to replace in the template.
        """
        with open(template_file, "r") as file:
            content = file.read()
        content = content.replace("{{ APP_NAME }}", app_name)
        content = content.replace("{{ APP_PORT }}", app_port)
        content = content.replace("{{ HOSTNAME }}", os.getenv("HOST_NAME", ""))
        content = content.replace("{{ PARTICIPANT_ID }}", os.getenv("INSTRUQT_PARTICIPANT_ID", ""))
        content = content.replace("{{ IP_ADDRESS }}", ip_address)
        with open(output_file, "w") as file:
            file.write(content)

    apps = apps_string.split(",")
    for app in apps:
        print(f"Rendering template for {app}")
        app_name, app_port, ip_address = app.split(":")
        output_file = os.path.join(output_path, f"nginx-{app_name}.yaml")
        replace_values(template_file, output_file, app_name, app_port, ip_address)


def apply_k8s_manifests(manifests, namespace="default"):
    """
    Apply Kubernetes manifests.

    :param manifests: The path to the manifests file(s).
    :param namespace: The namespace for the Kubernetes secret. Default is 'default'.
    """
    k8s_client = client.ApiClient()
    for manifest in manifests:
        utils.create_from_yaml(k8s_client, manifest, namespace=namespace)


def wait_for_kubernetes_api(k8s_api):
    """
    Enables bash completion for kubectl.
    Waits for the Kubernetes API server to become available.

    :param k8s_api: The URL of the Kubernetes API server. (e.g., 'http://localhost:8001/api')
    """
    run_command('echo "source /usr/share/bash-completion/bash_completion" >> /root/.bashrc')
    run_command('echo "complete -F __start_kubectl k" >> /root/.bashrc')

    while True:
        try:
            response = requests.get(k8s_api)
            if response.status_code == 200:
                print("Kubernetes API server is available.")
                break
        except requests.RequestException:
            print("Waiting for the Kubernetes API server to become available...")
            time.sleep(2)


def create_k8s_secret(secret_name, secret_data, namespace="default"):
    """
    Create Kubernetes secret.

    :param secret_name: The name of the Kubernetes secret to create.
    :param secret_data: The secret value (stored under the ``password`` key in stringData).
    :param namespace: The namespace for the Kubernetes secret. Default is 'default'.
    :raises SystemExit: If the secret could not be created.
    """
    print(f"Creating secret '{secret_name}'")

    v1 = client.CoreV1Api()
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name=secret_name),
        string_data={"password": secret_data}
    )
    try:
        v1.create_namespaced_secret(namespace=namespace, body=secret)
    except client.ApiException as e:
        if e.status != 409:
            print(f"Exception when creating secret: {e}")
            raise SystemExit(1)
