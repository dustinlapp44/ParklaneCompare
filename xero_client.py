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
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

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
def get_invoices(access_token, tenant_id, start_date, itype):
    param_str = f'Date >= DateTime({start_date.replace("-", ", ")}) && Status != "DELETED" && Status != "VOIDED"'
    if itype!=None:
        param_str += f' && Type == "{itype}"'
        
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
def pull_xero_data(access_token, tenant_id):
    invoices = get_invoices(access_token, tenant_id)
    payments = get_payments(access_token, tenant_id)

    return invoices, payments

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
