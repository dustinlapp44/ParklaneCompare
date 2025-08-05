import requests, json, os, re
from datetime import datetime, timedelta, timezone

base_dir = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(base_dir, 'xero_tokens.json')

## If xero_secrets is deleted, must recreate with new client_id and client_secret
def load_xero_credentials(filename='xero_secrets.json') -> dict:
    """
    Load Xero API credentials from a local JSON file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Xero secrets file not found: {path}")

    with open(path, 'r') as f:
        creds = json.load(f)

    if 'client_id' not in creds or 'client_secret' not in creds:
        raise ValueError("Missing 'client_id' or 'client_secret' in secrets file.")

    return creds

# ------------------------------------------
# Load saved tokens if available
# ------------------------------------------
def load_tokens():
    try:
        with open(token_path, "r") as f:
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
    with open(token_path, 'w') as f:
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
    creds = load_xero_credentials()
    client_id = creds['client_id']
    client_secret = creds['client_secret']
    auth = (client_id, client_secret)
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

def get_creditnotes(access_token, tenant_id, start_date, end_date, itype, contact=None):
    # Build filter string
    param_str = (
        f'Date >= DateTime({start_date.replace("-", ", ")}) '
        f'&& Date <= DateTime({end_date.replace("-", ", ")}) '
        f'&& Status != "DELETED" && Status != "VOIDED"'
    )
    if itype!=None:
        param_str += f' && Type == "{itype}"'
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
    access_token, tenant_id = authorize_xero(org_name="Parklane Properties")

    # Default date range to last 30 days if not provided
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    invoices = get_invoices(access_token, tenant_id, start_date, end_date, itype, contact=contact)
    
    invoices = format_dates(invoices)

    return invoices

def parse_xero_date(date_str):
    ## Step 1, check if timestamp format
    match = re.search(r'/Date\((\d+)(?:[+-]\d{4})?\)/', date_str)
    if match:
        timestamp = int(match.group(1))
        date_str =  datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%dT%H:%M:%S')
    ## Step 2, check if ISO format and return only date info (not time)
    if 'T' in date_str:
        return date_str.split('T')[0]  # Return only the date part
    else:
        return date_str

def format_dates(invoices):
    """
    Converts date strings in invoices to ISO format.
    """
    for invoice in invoices:
        if 'DateString' in invoice:
            invoice['DateString'] = parse_xero_date(invoice['DateString'])
        if 'DueDateString' in invoice:
            invoice['DueDateString'] = parse_xero_date(invoice['DueDateString'])
        if 'Date' in invoice:
            invoice['Date'] = parse_xero_date(invoice['Date'])
        if 'Payments' in invoice:
            for payment in invoice['Payments']:
                if 'Date' in payment:
                    payment['Date'] = parse_xero_date(payment['Date'])
                if 'UpdatedDateUTC' in payment:
                    payment['UpdatedDateUTC'] = parse_xero_date(payment['UpdatedDateUTC'])
    return invoices

def get_xero_accounts(access_token: str, tenant_id: str):

    params = {
        'where': 'Status=="ACTIVE"',
    }
    
    url = "https://api.xero.com/api.xro/2.0/Accounts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Xero-tenant-id": tenant_id,
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()["Accounts"]

def get_bank_info(access_token, tenant_id, payment_data):
    ret_list = []
    accounts = get_xero_accounts(access_token, tenant_id)
    for account in accounts:
        if account["Name"].count(payment_data['PAYMENT']['payment']['property']):
            ret_list.append(account)
    return ret_list


def build_payment_payload(payment_data: dict, account_id) -> dict:
    """
    Given a combined payment+invoice dict and an account code, return Xero payment payload.
    """
    # Parse and normalize the date
    raw_date = payment_data["payment"]["date"]
    try:
        # Strip timezone and parse
        parsed_date = datetime.strptime(raw_date.split(" MDT")[0], "%d %b %Y %H:%M:%S")
        formatted_date = parsed_date.strftime("%Y-%m-%d")
    except Exception as e:
        raise ValueError(f"Could not parse payment date: {raw_date}") from e

    # Use payment reference (e.g., Aptexx transaction ID) and optionally include method
    payment_ref = f"Aptexx {payment_data['payment']['ref']}"

    payload = {
        "Payments": [
            {
                "Invoice": {
                    "InvoiceID": payment_data["invoice"]["invoice_id"]
                },
                "Account": {
                    "AccountID": account_id
                },
                "Date": formatted_date,
                "Amount": payment_data["payment"]["amount"],
                "Reference": payment_ref
            }
        ]
    }

    return payload

def apply_payment(payment_data):
    """
    Applies a payment to a given invoice via Xero API.
    """
    access_token, tenant_id = authorize_xero(org_name="Parklane Properties")
    account = get_bank_info(access_token, tenant_id, payment_data)
    if len(account) == 0:
        print(f"No matching bank account found for payment: {payment_data['PAYMENT']['payment']['property']}")
        return None
    elif len(account) > 1:
        new_account = []
        for acc in account:
            if acc["Name"].count('Checking'):
                new_account.append(acc)
        if len(new_account) == 1:
            account = new_account
        elif len(new_account) == 0:
            print(f"No matching bank account found for payment: {payment_data['PAYMENT']['payment']['property']}")
            return None
        else:
            print(f"Multiple matching bank accounts found for payment: {payment_data['PAYMENT']['payment']['property']}")
            return None  
    data = build_payment_payload(payment_data['PAYMENT'], account[0]["AccountID"])

    url = f'https://api.xero.com/api.xro/2.0/Payments'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': tenant_id,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
    #return None

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
