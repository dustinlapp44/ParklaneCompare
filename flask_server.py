from flask import Flask, redirect, request
from xero_python.accounting import AccountingApi
from xero_python.api_client import ApiClient
from xero_python.api_client.configuration import Configuration
from xero_python.api_client.oauth2 import OAuth2Token
import json

import os
import requests

app = Flask(__name__)

# Your Xero app credentials
CLIENT_ID = '6D3387F5F6F0463DA9BEB98BEDFBD793'
CLIENT_SECRET = 'MQCjTrRNWs0Pn5D1OUR1GUDts6v9H4F5O4tGJmdPpgo4I4tx'
REDIRECT_URI = 'http://localhost:10000/callback'

# Scopes required for your program
SCOPES = "offline_access accounting.transactions.read"

@app.route("/")
def home():
    # Redirect user to Xero authorization URL
    auth_url = (
        f"https://login.xero.com/identity/connect/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code in callback URL."
    if os.path.exists("xero_tokens.json"):
        with open("xero_tokens.json", "r") as f:
            tokens = json.load(f)
        access_token = tokens["access_token"]

        # Optional: check expiry time and refresh token if needed here
        # Then call APIs directly without redirecting to authorize

        # Call your invoice/payment retrieval here

        return "Used stored tokens and pulled data successfully."
    else:
        # Start normal OAuth redirect flow as before
        # Exchange authorization code for tokens
        token_url = "https://identity.xero.com/connect/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        auth = (CLIENT_ID, CLIENT_SECRET)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(token_url, data=data, auth=auth, headers=headers)
    
        if response.status_code != 200:
            return f"Token exchange failed: {response.text}"
    
        tokens = response.json()
        access_token = tokens["access_token"]
    
        # After token exchange and obtaining tokens dict
        with open("xero_tokens.json", "w") as f:
            json.dump(tokens, f)

    # Get tenant ID
    connections_response = requests.get(
        "https://api.xero.com/connections",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    connections = connections_response.json()
    tenant_id = connections[0]["tenantId"]

    # ... after getting tokens and tenant_id

    print("Access token:", access_token)
    print("Tenant ID:", tenant_id)

    invoices_response = requests.get(
        "https://api.xero.com/api.xro/2.0/Invoices",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        }
    )
    print("Invoices status:", invoices_response.status_code)
    print("Invoices response:", invoices_response.text)

    #payments_response = requests.get(
    #    "https://api.xero.com/api.xro/2.0/Payments",
    #    headers={
    #        "Authorization": f"Bearer {access_token}",
    #        "Accept": "application/json",
    #        "Xero-tenant-id": tenant_id,
    #    }
    #)
    params = {
    'where': 'Date >= DateTime(2025, 07, 01)'
    }

    payments_response = requests.get(
        "https://api.xero.com/api.xro/2.0/Payments",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        },
        params=params
    )

    print("Payments status:", payments_response.status_code)
    print("Payments response:", payments_response.text)

    # Proceed only if status codes are 200
    if invoices_response.status_code == 200:
        invoices = invoices_response.json()
    else:
        return f"Failed to get invoices: {invoices_response.status_code} {invoices_response.text}"

    if payments_response.status_code == 200:
        payments = payments_response.json()
    else:
        return f"Failed to get payments: {payments_response.status_code} {payments_response.text}"

    return f"Found {len(invoices['Invoices'])} invoices and {len(payments['Payments'])} payments."


    # Get invoices directly
    invoices_response = requests.get(
        "https://api.xero.com/api.xro/2.0/Invoices",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        }
    )
    invoices = invoices_response.json()

    # Get payments directly
    payments_response = requests.get(
        "https://api.xero.com/api.xro/2.0/Payments",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Xero-tenant-id": tenant_id,
        }
    )
    payments = payments_response.json()

    return f"Found {len(invoices['Invoices'])} invoices and {len(payments['Payments'])} payments."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
