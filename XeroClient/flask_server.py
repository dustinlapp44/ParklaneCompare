from flask import Flask, redirect, request
import requests
import json
from xero_client import save_tokens

app = Flask(__name__)

CLIENT_ID = '6D3387F5F6F0463DA9BEB98BEDFBD793'
CLIENT_SECRET = 'MQCjTrRNWs0Pn5D1OUR1GUDts6v9H4F5O4tGJmdPpgo4I4tx'
REDIRECT_URI = 'http://localhost:10000/callback'
SCOPES = "offline_access accounting.transactions accounting.settings.read"

@app.route("/")
def home():
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
    save_tokens(tokens)

    return "Authorization complete. Tokens saved. You can now call your data pull script."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
