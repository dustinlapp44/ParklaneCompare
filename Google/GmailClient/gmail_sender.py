import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

# Get absolute path to the directory where this script resides
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')

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

# If modifying these SCOPES, delete token.json to refresh
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send']

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_message(service, message):
    sent = service.users().messages().send(userId='me', body=message).execute()
    print(f"Message ID: {sent['id']}")
    return sent

def send_email(subject, message_text, sender='jill@Parklaneco.com', to='jill@Parklaneco.com'):
    """
    Sends an email using the Gmail API.
    """
    service = get_gmail_service()
    message = create_message(sender, to, subject, message_text)
    return send_message(service, message)

if __name__ == "__main__":
    service = get_gmail_service()

    message = create_message(
        sender="jill@Parklaneco.com",
        to="dustinlapp44@gmail.com",
        subject="Test from Gmail API",
        message_text="This was sent from the command line via the Gmail API!"
    )

    send_message(service, message)