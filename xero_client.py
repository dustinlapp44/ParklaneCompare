import requests
import json
import os
from datetime import datetime, timedelta

CLIENT_ID = '6D3387F5F6F0463DA9BEB98BEDFBD793'
CLIENT_SECRET = 'MQCjTrRNWs0Pn5D1OUR1GUDts6v9H4F5O4tGJmdPpgo4I4tx'
TOKEN_FILE = 'xero_tokens.json'

# ------------------------------------------
# Load saved tokens if available
# ------------------------------------------
def load_tokens():
    try:
        with open("xero_tokens.json", "r") as f:
            content = f.read()
            if not content.strip():
                print("Token file is empty.")
                return None
            return json.loads(content)
    except json.JSONDecodeError as e:
        print("Token file contains invalid JSON:", e)
        return None
    except FileNotFoundError:
        print("Token file not found.")
        return None
    
def get_invoices_for_db(access_token, tenant_id, start_date, end_date, page=1):
    url = 'https://api.xero.com/api.xro/2.0/Invoices'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': tenant_id,
        'Accept': 'application/json'
    }
    params = {
        'where': f'Date >= DateTime({start_date}) && Date <= DateTime({end_date})',
        'page': page
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get('Invoices', [])

# ------------------------------------------
# Save tokens
# ------------------------------------------
def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

# ------------------------------------------
# Refresh access token if expired
# ------------------------------------------
def refresh_access_token(tokens):
    refresh_token = tokens['refresh_token']
    token_url = "https://identity.xero.com/connect/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    auth = (CLIENT_ID, CLIENT_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(token_url, data=data, auth=auth, headers=headers)
    if response.status_code == 200:
        new_tokens = response.json()
        save_tokens(new_tokens)
        return new_tokens
    else:
        print("Token refresh failed:", response.text)
        return None

# ------------------------------------------
# Get tenant ID
# ------------------------------------------
def get_tenant_id(access_token):
    response = requests.get(
        "https://api.xero.com/connections",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if response.status_code == 200:
        connections = response.json()
        return connections[0]["tenantId"]
    else:
        print("Failed to get tenant ID:", response.text)
        return None

# ------------------------------------------
# Get invoices
# ------------------------------------------
def get_invoices(access_token, tenant_id, start_date, end_date, itype, contact=None):
    param_str = f'Date >= DateTime({start_date.replace("-", ", ")}) && Date <= DateTime({end_date.replace("-", ", ")}) && Status != "DELETED" && Status != "VOIDED"'
    if itype!=None:
        param_str += f' && Type == "{itype}"'
    if contact:
        param_str += f' && Contact.Name == "{contact}"'
    params = {
        'where': param_str,
    }
    response = requests.get(
        "https://api.xero.com/api.xro/2.0/Invoices",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        },
        params=params
    )
    if response.status_code == 200:
        return response.json()["Invoices"]
    else:
        print("Failed to get invoices:", response.text)
        return []

# ------------------------------------------
# Get payments (with filter example)
# ------------------------------------------
def get_payments(access_token, tenant_id, start_date):
    params = {
        'where': f'Date >= DateTime({start_date.replace("-", ", ")})'
    }
    response = requests.get(
        "https://api.xero.com/api.xro/2.0/Payments",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        },
        params=params
    )
    if response.status_code == 200:
        return response.json()["Payments"]
    else:
        print("Failed to get payments:", response.text)
        return []
    
import requests

def get_creditnotes(access_token, tenant_id, start_date, end_date, contact=None):
    # Build filter string
    param_str = (
        f'Date >= DateTime({start_date.replace("-", ", ")}) '
        f'&& Date <= DateTime({end_date.replace("-", ", ")}) '
        f'&& Status != "DELETED" && Status != "VOIDED"'
    )

    if contact:
        param_str += f' && Contact.Name == "{contact}"'

    params = {
        'where': param_str,
    }

    response = requests.get(
        "https://api.xero.com/api.xro/2.0/CreditNotes",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        },
        params=params
    )

    if response.status_code == 200:
        return response.json().get("CreditNotes", [])
    else:
        print("Failed to get credit notes:", response.status_code, response.text)
        return []
    
## Will definitely need to be gone over, do not trust yet
def pull_tenant_invoices(start_date=None, end_date=None, itype=None, contact=None):
    """
    Pulls tenant invoices from Xero API for a given person.
    Optionally filters by date range, invoice type, and contact name.
    """
    access_token = authorize_xero(org_name="Parklane Properties")
    tokens = load_tokens()
    if not tokens:
        print("No tokens saved. Run the Flask server to authorize first.")
        return []

    access_token = tokens["access_token"]
    tenant_id = get_tenant_id(access_token)
    
    if not tenant_id:
        print("Failed to get tenant ID.")
        return []

    # Default date range to last 30 days if not provided
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    invoices = get_invoices(access_token, tenant_id, start_date, end_date, itype, contact=contact)
    
    return invoices

def apply_payment(access_token, tenant_id, invoice_id, amount, date, code):
    """
    Applies a payment to a given invoice via Xero API.
    """
    url = f'https://api.xero.com/api.xro/2.0/Payments'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': tenant_id,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    data = {
        "Payments": [
            {
                "Invoice": {
                    "InvoiceID": invoice_id
                },
                "Account": {
                    "Code": code  # replace with your bank or payment account code in Xero
                },
                "Date": date,
                "Amount": amount
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def authorize_xero(org_name="Test"):
    tokens = load_tokens()
    if not tokens:
        print("No tokens saved. Run the Flask server to authorize first.")
        return None

    access_token = tokens["access_token"]

    # Optional: implement expiry check if you store expiry timestamps
    tokens = refresh_access_token(tokens)
    if tokens:
        access_token = tokens["access_token"]
    else:
        print("Could not refresh token. Re-authorize via Flask server.")
        return None

    tenant_id = get_tenant_id_by_name(access_token,org_name)
    if not tenant_id:
        return None
    
    print("Authorization successful. Access token and tenant ID obtained.")
    return access_token, tenant_id
# ------------------------------------------
# Main function to get both invoices and payments
# ------------------------------------------

def get_tenant_id_by_name(access_token, target_name):
    response = requests.get(
        "https://api.xero.com/connections",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if response.status_code == 200:
        connections = response.json()
        for c in connections:
            if c["tenantName"] == target_name:
                return c["tenantId"]
        print(f"No organization found with name: {target_name}")
        return None
    else:
        print("Failed to get connections:", response.text)
        return None
