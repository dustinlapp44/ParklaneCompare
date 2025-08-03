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
from parser import parse_aptexx_email, print_data
from apply_payments import match_and_apply_payments
from Payments.payments_db import get_invoices_by_contact
from Payments.refresh_invoices import refresh_invoice_cache

def clean_html_to_text(html):
    with open('email.html', 'w', encoding='utf-8') as f:
        f.write(html)
    soup = BeautifulSoup(html, 'html.parser')
    
    for table in soup.find_all('table'):
        print(table)



    #for tag in soup.find_all(['b', 'div', 'td']):
    #    tag.append('\n')

    with open('email_cleaned.txt', 'w', encoding='utf-8') as f:
        f.write(soup.get_text())
    return soup.get_text()

def parse_structured_payments(html):
    soup = BeautifulSoup(html, 'html.parser')

    results = []
    current_property = None
    rows = soup.find_all('tr')
    i = 0

    while i < len(rows):
        row = rows[i]
        bold = row.find('b')
        if bold:
            current_property = bold.get_text(strip=True)
            i += 1
            continue

        cols = row.find_all('td')
        if len(cols) == 6:
            try:
                payment = {
                    'property': current_property,
                    'ref': cols[0].get_text(strip=True),
                    'date': cols[1].get_text(strip=True),
                    'method': cols[2].get_text(strip=True),
                    'person': cols[3].get_text(strip=True),
                    'unit': cols[4].get_text(strip=True),
                    'amount': cols[5].get_text(strip=True),
                }

                # Check next row for Memo
                if i + 1 < len(rows):
                    next_row = rows[i + 1]
                    memo_label = next_row.find('td', string=lambda x: x and 'Memo:' in x)
                    if memo_label:
                        memo_value = next_row.find_all('td')[1].get_text(strip=True)
                        payment['memo'] = memo_value
                        i += 1  # skip memo row

                results.append(payment)
            except Exception as e:
                print(f"Skipping row due to error: {e}")
        i += 1

    return results

def process_payments(start_date=None, end_date=None):
    # Step 1. Fetch AptExx emails
    emails = fetch_aptexx_emails(start_date=start_date, end_date=end_date)
    
    for email in emails:
        if email['plain']:
            parsed_payments = parse_aptexx_email(email['plain'].splitlines())
        elif email['html']:
            parsed_payments = parse_structured_payments(email['html'])
        else:
            print("No usable email content found.")
        
        ## Prinf info about email
        #print(f"Email from: {email['from']} | Subject: {email['subject']}")
        #print_data(parsed_payments)

        for property in parsed_payments:
            # Step 3. Apply payment to Xero
            property_name = property['property']
            print(f"Processing property: {property_name}")
            for aptexx_payment in property['payments']:
                print(f"  Payment: {aptexx_payment['ref']}  Amount: {aptexx_payment['amount']}  Person: {aptexx_payment['person']}")
                tenant_invoices = get_invoices_by_contact(aptexx_payment['person'])

                if len(tenant_invoices) == 0:
                    print(f"    No invoices found for {aptexx_payment['person']}")
               
                # Step 4. Match and apply payments
                match_and_apply_payments(aptexx_payment, tenant_invoices)
                print()
            print()


if __name__ == "__main__":

    invoice_start_date = "2025-06-01"
    invoice_end_date = "2025-08-02"
    refresh_invoice_cache(invoice_start_date, invoice_end_date)

    payment_start_date = "2025-08-02"
    payment_end_date = "2025-08-03"
    process_payments(payment_start_date, payment_end_date)

    
        