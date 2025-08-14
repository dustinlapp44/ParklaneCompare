# main.py
import sys
import os
from bs4 import BeautifulSoup


# Add parent directory to path for xero_client import
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


from XeroClient.xero_client import pull_tenant_invoices
from Google.GmailClient.gmail_watcher import fetch_aptexx_emails
from Google.GmailClient.gmail_sender import send_email
from parser import parse_html_payments
from apply_payments import match_and_apply_payments
from Payments.payments_db import get_invoices_by_contact
from Payments.refresh_invoices import refresh_invoice_cache

def build_html_email(payments):
    rows = []
    for p in payments:
        row = f"""
        <tr>
            <td>{p['person']}</td>
            <td>{p['property']}</td>
            <td>{p['unit']}</td>
            <td>${p['amount']:.2f}</td>
            <td>{p['ref']}</td>
            <td>{p['date']}</td>
        </tr>"""
        rows.append(row)

    html = f"""
    <html>
      <body>
        <p>Here are today's failed payments, sorry aboot that:</p>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
          <thead>
            <tr>
              <th>Tenant</th>
              <th>Property</th>
              <th>Unit</th>
              <th>Amount</th>
              <th>Aptexx Reference</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </body>
    </html>
    """
    return html

def process_payments(start_date=None, end_date=None):
    # Step 1. Fetch AptExx emails
    emails = fetch_aptexx_emails(start_date=start_date, end_date=end_date)
    
    for email in emails:
        if email['html']:
            parsed_payments = parse_html_payments(email['html'])
        else:
            print("No usable email content found.")

        total_amount = sum(payment['amount'] for payment in parsed_payments)
        missed_payments=[]
        for payment in parsed_payments:
            print(f"Processing AptExx payment: {payment['ref']} on {payment['date']} for amount {payment['amount']}")
            payment_type = payment['property'].split(' - ')[1].strip().replace('(Non-Integrated)', '').strip()
            payment['property'] = payment['property'].split(' - ')[0].strip()
            if payment_type != 'Rent':
                missed_payments.append(payment)
                print(f"Payment type {payment_type} is not Rent. SEND EMAIL")
                continue

            # Step 2. Get tenant invoices from Xero
            contact = " ".join(x for x in payment['person'].split() if x !='')
            tenant_invoices = get_invoices_by_contact(contact)
            if not tenant_invoices:
                print(f"No invoices found for tenant: {payment['person']}. SEND EMAIL")
                print()
                missed_payments.append(payment)
                continue
            
            # Step 3. Match and apply payments
            ret = match_and_apply_payments(payment, tenant_invoices)
            if not ret:
                missed_payments.append(payment)

            print()

        ## Send email for missed payments
        if missed_payments:
            html = build_html_email(missed_payments)
            print("Sending email for missed payments...")
            send_email(subject="Missed Payments", message_text=html)
        print(f"Total amount for all payments: ${total_amount:.2f}")

if __name__ == "__main__":

    invoice_start_date = "2025-05-01"
    invoice_end_date = "2025-08-14"
    refresh_invoice_cache(invoice_start_date, invoice_end_date)

    email_start_date = "2025-08-14"
    email_end_date = "2025-08-14"
    process_payments(email_start_date, email_end_date)

    
        