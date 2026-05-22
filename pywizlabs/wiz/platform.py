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
from typing import Optional
from datetime import datetime, timedelta, timezone

# Third-party imports
import requests

# Library-specific imports
# None

WIZ_AUTH_URL = "https://auth.app.wiz.io/oauth/token"

def build_wiz_api_url(dc: str) -> str:
    """
    Builds a Wiz GraphQL API URL for the given datacenter.

    Args:
        dc (str): The Wiz datacenter identifier (e.g., "us100", "us17", "eu1").

    Returns:
        str: The full GraphQL endpoint URL for that datacenter.
    """
    return f"https://api.{dc}.app.wiz.io/graphql"


def get_wiz_api_token(
    client_id: str, 
    client_secret: str, 
    auth_url: str = WIZ_AUTH_URL
) -> Optional[str]:
    """
    Authenticates with the Wiz API using a Service Account Client ID and Secret.
    
    Args:
        client_id (str): The Client ID of your Wiz Service Account.
        client_secret (str): The Client Secret of your Wiz Service Account.
        auth_url (str): The token endpoint. Defaults to the commercial Wiz environment. 
                        For FedRAMP/Gov, use "https://auth.app.wiz.us/oauth/token".
        
    Returns:
        Optional[str]: The OAuth access token (Bearer token) if successful, otherwise None.
    """
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    # Payload required by Wiz to issue an access token
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "wiz-api"
    }
    
    try:
        response = requests.post(auth_url, data=payload, headers=headers)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Extract and return the access token
        return token_data.get("access_token")
        
    except requests.exceptions.RequestException as e:
        print(f"[WIZ] Failed to authenticate with Wiz API: {e}")
        # If the server returned an error response, print it for debugging
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WIZ] Server Response: {e.response.text}")
        return None


def verify_wiz_login(dc: str, access_token: str, user_email: str) -> bool:
    """
    Queries the Wiz GraphQL API to determine if a user has ever logged into the platform.

    Args:
        dc (str): The Wiz datacenter identifier (e.g., "us100", "us17", "eu1").
        access_token (str): A valid Wiz API Bearer token.
        user_email (str): The email address of the user you want to verify.

    Returns:
        bool: True if the user exists and has a populated 'lastLoginAt' timestamp.
              False if the user has never logged in, or if the user is not found.
    """
    api_endpoint_url = build_wiz_api_url(dc)

    # GraphQL query to search for the user and retrieve their last login timestamp
    query = """
    query GetUserLoginStatus($search: String, $first: Int) {
      users(filterBy: { search: $search }, first: $first) {
        nodes {
          email
          lastLoginAt
        }
      }
    }
    """
    
    variables = {
        "search": user_email,
        "first": 50 # Fetch up to 50 results to account for partial matches
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"[WIZ] Validating Wiz login for user '{user_email}'...")
        response = requests.post(
            api_endpoint_url,
            json={"query": query, "variables": variables},
            headers=headers
        )
        response.raise_for_status()

        response_json = response.json()
        if response_json.get("errors"):
            print(f"[WIZ] GraphQL errors from users query: {response_json['errors']}")
            return False

        # Safely extract the list of users from the GraphQL response.
        # Use ``or {}`` because a GraphQL error response has ``data: null``,
        # which would make a chained .get() crash with AttributeError.
        data = response_json.get("data") or {}
        users_block = data.get("users") or {}
        users = users_block.get("nodes", [])
        
        for user in users:
            # Ensure we are checking the exact user, as search might return similar emails
            if user.get("email", "").lower() == user_email.lower():
                # If 'lastLoginAt' is not None, the user has successfully logged in before
                return user.get("lastLoginAt") is not None
                
        # If the loop finishes without returning, the user wasn't found in the results
        print(f"[WIZ] User '{user_email}' not found in the Wiz tenant.")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"[WIZ] Failed to query Wiz API: {e}")
        return False


def delete_wiz_user(dc: str, access_token: str, user_email: str) -> bool:
    """
    Deletes a specific user from the Wiz platform based on their email address.

    Args:
        dc (str): The Wiz datacenter identifier (e.g., "us100", "us17", "eu1").
        access_token (str): A valid Wiz API Bearer token with 'admin:users' or 'delete:users' permission.
        user_email (str): The email address of the lab user you want to delete.

    Returns:
        bool: True if the user was successfully found and deleted, False otherwise.
    """
    api_endpoint_url = build_wiz_api_url(dc)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # STEP 1: Find the user's ID by their email
    query_user = """
    query GetUserForDeletion($search: String, $first: Int) {
      users(filterBy: { search: $search }, first: $first) {
        nodes {
          id
          email
        }
      }
    }
    """
    
    try:
        # Fetch user details
        response = requests.post(
            api_endpoint_url,
            json={"query": query_user, "variables": {"search": user_email, "first": 50}},
            headers=headers
        )
        response.raise_for_status()

        response_json = response.json()
        if response_json.get("errors"):
            print(f"[WIZ] GraphQL errors from users-for-deletion query: {response_json['errors']}")
            return False

        data = response_json.get("data") or {}
        users_block = data.get("users") or {}
        users = users_block.get("nodes", [])
        user_id = None
        
        # Look for the exact email match
        for user in users:
            if user.get("email", "").lower() == user_email.lower():
                user_id = user.get("id")
                break
                
        if not user_id:
            print(f"[WIZ] User '{user_email}' not found. Nothing to delete.")
            return False
            
        print(f"[WIZ] Found user '{user_email}' with ID '{user_id}'. Proceeding with deletion...")
        
        # STEP 2: Delete the user using the ID we just fetched.
        # DeleteUserPayload's only selectable field is `_stub` — the API doesn't
        # echo the deleted user back, so we just select the placeholder.
        mutation_delete = """
        mutation DeleteLabUser($id: ID!) {
          deleteUser(input: { id: $id }) {
            _stub
          }
        }
        """
        
        delete_response = requests.post(
            api_endpoint_url,
            json={"query": mutation_delete, "variables": {"id": user_id}},
            headers=headers
        )
        delete_response.raise_for_status()
        
        delete_data = delete_response.json()
        
        # Check for GraphQL errors in the response
        if "errors" in delete_data:
            print(f"[WIZ] Failed to delete user due to GraphQL errors: {delete_data['errors']}")
            return False
            
        print(f"[WIZ] Successfully deleted user '{user_email}'.")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[WIZ] Failed to communicate with the Wiz API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WIZ] Server Response: {e.response.text}")
        return False


# All `Create*` action names Wiz emits today. Canonical list from the API
# reference (docs.wiz.io > Get Audit Logs > available actions). Used as the
# Python-side match set in `get_user_creations` because the server-side
# `action` filter in `AuditLogEntryFilters` is a single string, not an enum
# or array — we can't pre-filter all 47 in one shot. Update this if Wiz adds
# new create actions; until then, anything not in this set is ignored even
# if it shares the `Create…` prefix.
WIZ_CREATE_ACTIONS = frozenset({
    "CreateActionTemplate",
    "CreateApplicationServiceDiscoveryRule",
    "CreateAutomationRule",
    "CreateCICDScanPolicy",
    "CreateCloudConfigurationFindingNote",
    "CreateCloudConfigurationRule",
    "CreateCloudConfigurationRules",
    "CreateCloudEventRule",
    "CreateComputeGroupTagsSet",
    "CreateConnector",
    "CreateControl",
    "CreateCustomIPRange",
    "CreateDashboard",
    "CreateDashboardWidget",
    "CreateDataClassifier",
    "CreateDigitalTrustCustomDomain",
    "CreateFileIntegrityMonitoringExclusion",
    "CreateHostConfigurationAssessmentNote",
    "CreateHostConfigurationRule",
    "CreateIgnoreRule",
    "CreateImageIntegrityValidator",
    "CreateIntegration",
    "CreateIssueNote",
    "CreateMalwareExclusion",
    "CreateMonitoredMetric",
    "CreateOutpost",
    "CreateOutpostCluster",
    "CreatePolicyPackage",
    "CreatePortalView",
    "CreateProject",
    "CreateRemediationAndResponseDeployment",
    "CreateRemediationPullRequest",
    "CreateReport",
    "CreateRuntimeResponsePolicy",
    "CreateSAMLIdentityProvider",
    "CreateSAMLUser",
    "CreateSavedCloudEventFilter",
    "CreateSavedGraphQuery",
    "CreateScannerAPIRateLimit",
    "CreateSecurityFramework",
    "CreateServiceAccount",
    "CreateSupportTicket",
    "CreateTestNode",
    "CreateUser",
    "CreateUserRole",
    "CreateVulnerabilityFindingNote",
})


def get_user_creations(dc: str, access_token: str, user_email: str, hours_ago: int = 24) -> list:
    """
    Queries the Wiz Audit Logs for successful ``Create*`` actions performed by
    the given user within a timeframe. Wiz's ``AuditLogEntry`` has no structured
    ``resource`` field — the resource identifiers live inside ``actionParameters``
    as a JSON blob whose shape varies per action. This function returns the raw
    audit entries so callers can either persist them for manual review or parse
    ``actionParameters`` per action type.

    Filtering strategy:
      - Server-side via ``AuditLogEntryFilters`` —
        ``timestamp.after`` (lookback bound), ``status: [SUCCESS]``,
        ``actionType: [MUTATION]`` — keeps the Wiz-side result small.
      - Python-side — performer email match (no server filter accepts email
        directly; the ``user`` filter requires UUIDs, which would cost an
        extra lookup) plus exact-match against ``WIZ_CREATE_ACTIONS``.

    Args:
        dc (str): The Wiz datacenter identifier (e.g., "us100", "us17", "eu1").
        access_token (str): A valid Wiz API Bearer token with 'admin:audit' permissions.
        user_email (str): The email address of the lab user (also stored as ``performer.name``).
        hours_ago (int): The lookback period in hours to search for creation events.

    Returns:
        list: A list of audit entry dicts, each containing ``id``, ``action``,
        ``actionType``, ``status``, ``timestamp``, ``performer`` ({id, name}), and
        ``actionParameters`` (JSON).
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    api_endpoint_url = build_wiz_api_url(dc)

    # Calculate the timestamp for the filter
    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()

    # Server-side filters narrow the result set before Python touches it:
    #   - timestamp.after      drops everything outside the lookback window
    #   - status: [SUCCESS]    drops failed / denied attempts
    #   - actionType: [MUTATION] drops the read-side audit volume
    # The `action` field in `AuditLogEntryFilters` is a SINGLE string (not
    # an enum or array), so we can't enumerate all 47 `Create*` action names
    # server-side. WIZ_CREATE_ACTIONS handles that match in Python below.
    # ISO 8601 `Z` form (no microseconds, no offset) is what Wiz's
    # `timestamp.after` expects per the docs: yyyy-MM-dd'T'HH:mm:ss'Z'.
    # `performer` is a SystemPrincipalSnapshot interface — only `id` and
    # `name` are common to all impls; Wiz stores the user's email in `name`.
    time_threshold_iso = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")

    query_audit_logs = """
    query GetUserAuditLogs($first: Int, $filterBy: AuditLogEntryFilters) {
      auditLogEntries(first: $first, filterBy: $filterBy) {
        nodes {
          id
          action
          actionType
          status
          timestamp
          performer {
            id
            name
          }
          actionParameters
        }
      }
    }
    """

    variables = {
        "first": 500,
        "filterBy": {
            "timestamp":  {"after": time_threshold_iso},
            "status":     ["SUCCESS"],
            "actionType": ["MUTATION"],
        },
    }

    created_resources = []

    try:
        response = requests.post(
            api_endpoint_url,
            json={"query": query_audit_logs, "variables": variables},
            headers=headers
        )
        response.raise_for_status()

        response_json = response.json()
        if response_json.get("errors"):
            print(f"[WIZ] GraphQL errors from auditLogEntries query: {response_json['errors']}")
            return []

        data = response_json.get("data") or {}
        entries_block = data.get("auditLogEntries") or {}
        logs = entries_block.get("nodes", [])

        for log in logs:
            # Server-side filters already enforced status=SUCCESS, actionType=MUTATION,
            # and timestamp >= threshold. We only need to narrow by user (no
            # server filter for email-based matching without an extra user-ID
            # lookup) and to the known set of `Create*` action names.
            performer_name = log.get("performer", {}).get("name", "").lower()
            action = log.get("action", "")

            if performer_name == user_email.lower() and action in WIZ_CREATE_ACTIONS:
                timestamp = log.get("timestamp", "")
                print(f"[WIZ] [{timestamp}] {user_email} performed {action} (entry {log.get('id')})")
                created_resources.append(log)

        if not created_resources:
            print(f"[WIZ] No CREATE audit entries found for user '{user_email}' in the last {hours_ago} hours.")

        return created_resources

    except requests.exceptions.RequestException as e:
        print(f"[WIZ] Failed to fetch audit logs from the Wiz API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WIZ] Server Response: {e.response.text}")
        return []


# --- CLEANUP LOGIC ---

def delete_connector(api_endpoint_url: str, access_token: str, resource_id: str) -> bool:
    """
    Deletes a Connector from the Wiz platform by its resource ID.

    Args:
        api_endpoint_url (str): The Wiz GraphQL endpoint URL (built once by the caller
            and reused across multiple deletions in :func:`process_deletions`).
        access_token (str): A valid Wiz API Bearer token with permission to delete connectors.
        resource_id (str): The ID of the Connector to delete.

    Returns:
        bool: True if the connector was deleted successfully, False otherwise.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    mutation_delete = """
    mutation DeleteConnector($id: ID!) {
      deleteConnector(input: { id: $id }) {
        connector {
          id
        }
      }
    }
    """
    try:
        print(f"[WIZ] Executing API call to delete Connector {resource_id}...")
        response = requests.post(
            api_endpoint_url,
            json={"query": mutation_delete, "variables": {"id": resource_id}},
            headers=headers
        )
        response.raise_for_status()
        
        delete_data = response.json()
        if "errors" in delete_data:
            print(f"[WIZ] Failed to delete Connector due to GraphQL errors: {delete_data['errors']}")
            return False
            
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WIZ] API request failed for deleting Connector {resource_id}: {e}")
        return False


########### Map of resource 'type' string from the audit log to its corresponding deletion function.
########### Defined after the handler functions so they exist at module load time.
DELETION_HANDLERS = {
    "Connector": delete_connector,
    # "Integration": delete_integration,
    # Add additional types and their functions
}

def process_deletions(dc: str, access_token: str, resources: list) -> list:
    """
    Iterates over a list of created resources and routes each one to the correct
    deletion function via :data:`DELETION_HANDLERS`. Resources whose type has no
    registered handler, or whose deletion fails, are returned for manual cleanup.

    Args:
        dc (str): The Wiz datacenter identifier (e.g., "us100", "us17", "eu1").
        access_token (str): A valid Wiz API Bearer token.
        resources (list): A list of resource dicts (as returned by
            :func:`get_user_creations`) with at least ``type``, ``id``, and ``name`` keys.

    Returns:
        list: The subset of ``resources`` that could not be deleted automatically
        and require manual cleanup.
    """
    api_endpoint_url = build_wiz_api_url(dc)
    manual_cleanup_required = []

    for resource in resources:
        res_type = resource.get("type")
        res_id = resource.get("id")
        res_name = resource.get("name") or resource.get("action")

        # Audit entries from get_user_creations lack a structured 'type' — the
        # resource identifiers are inside actionParameters as JSON whose shape
        # varies per action. They fall through to manual cleanup below.
        handler = DELETION_HANDLERS.get(res_type) if res_type else None

        if handler:
            try:
                success = handler(api_endpoint_url, access_token, res_id)
                if not success:
                    print(f"[WIZ] Failed to delete {res_type} '{res_name}' ({res_id}). Tagging for manual cleanup.")
                    manual_cleanup_required.append(resource)
            except Exception as e:
                print(f"[WIZ] Error deleting {res_type} '{res_name}' ({res_id}): {e}")
                manual_cleanup_required.append(resource)
        else:
            label = res_type or f"audit-entry/{resource.get('action', 'unknown')}"
            print(f"[WIZ] No handler for '{label}' ('{res_name}'). Tagging for manual cleanup.")
            manual_cleanup_required.append(resource)

    return manual_cleanup_required
