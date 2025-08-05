# gmail_watcher.py

import os
import base64
import email
from email.header import decode_header
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Get absolute path to the directory where this script resides
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')

# If modifying these SCOPES, delete token.json to refresh
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def get_email_body(service, msg_id):
    """
    Fetches and decodes the full raw email using Gmail API and Python's email library.
    Returns a dict with 'plain' and 'html' keys if available.
    """
    message = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
    raw_msg = message['raw']
    msg_bytes = base64.urlsafe_b64decode(raw_msg.encode('ASCII'))
    mime_msg = email.message_from_bytes(msg_bytes)

    # Extract headers
    subject = decode_subject(mime_msg['Subject'])
    sender = mime_msg['From']

    body = {"plain": None, "html": None, "subject": subject, "from": sender}

    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))

            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                charset = part.get_content_charset() or 'utf-8'
                body['plain'] = part.get_payload(decode=True).decode(charset, errors='replace')
            elif content_type == 'text/html' and 'attachment' not in content_disposition:
                charset = part.get_content_charset() or 'utf-8'
                body['html'] = part.get_payload(decode=True).decode(charset, errors='replace')
    else:
        # Single part message
        content_type = mime_msg.get_content_type()
        charset = mime_msg.get_content_charset() or 'utf-8'
        if content_type == 'text/plain':
            body['plain'] = mime_msg.get_payload(decode=True).decode(charset, errors='replace')
        elif content_type == 'text/html':
            body['html'] = mime_msg.get_payload(decode=True).decode(charset, errors='replace')

    return body

def decode_subject(encoded_subject):
    """
    Decodes RFC 2047 encoded email subject headers.
    Returns a clean Unicode string.
    """
    decoded_parts = decode_header(encoded_subject)
    subject = ''
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            subject += part.decode(encoding or 'utf-8', errors='replace')
        else:
            subject += part
    return subject

def fetch_aptexx_emails(start_date=None, end_date=None):
    service = get_gmail_service()
    
    query_parts = ["from:customerservice@aptx.cm", "subject:'Payment Summary'"]
    if start_date:
        query_parts.append(f"after:{start_date}")  # YYYY/MM/DD
    if end_date:
        query_parts.append(f"before:{end_date}")
        
    query = " ".join(query_parts)
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        email_body = get_email_body(service, msg['id'])
        emails.append(email_body)
    
    return emails

    return emails

if __name__ == '__main__':
    emails = fetch_aptexx_emails()
    for email in emails:
        print(f"Email snippet: {email['snippet']}\n")
        print(f"Full body preview:\n{email['body'][:200]}...\n")
