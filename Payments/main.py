# main.py
import sys
import os

# Add parent directory to path for xero_client import
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


from xero_client import pull_tenant_invoices
from gmail_watcher import fetch_aptexx_emails
from parser import parse_aptexx_email, print_data
from apply_payments import match_and_apply_payments
from invoice_db import get_invoices_by_contact

def process_payments():
    # Step 1. Fetch AptExx emails
    emails = fetch_aptexx_emails(start_date="2025/07/22", end_date="2025/07/23")
    
    for email in emails:
        if email['plain']:
            parsed_payments = parse_aptexx_email(email['plain'].splitlines())
        elif email['html']:
            # Optionally parse HTML version with BeautifulSoup
            parsed_payments = parse_aptexx_email(email['html'].splitlines())
        else:
            print("No usable email content found.")
        
        ## Prinf info about email
        #print(f"Email from: {email['from']} | Subject: {email['subject']}")
        #print_data(parsed_payments)

        for property in parsed_payments:
            # Step 3. Apply payment to Xero
            property_name = property['property']
            print(f"Processing property: {property_name}")
            for payment in property['payments']:
                print(f"  Payment: {payment['ref']} -->  Person: {payment['person']}")
                invoices = get_invoices_by_contact(payment['person'])
                #print(invoices)
                if len(invoices) == 0:
                    print(f"    No invoices found for property: {property_name} and person: {payment['person']}")
                    #sys.exit(0)
                for invoice in invoices:
                    issue_date = invoice['issue_date']
                    due_date = invoice['due_date']
                    print(f"    Found invoice: {invoice['invoice_id']} for amount ${invoice['amount_due']} issued {issue_date} due {due_date}") 
                    #print(f"    Reference: {invoice.get('Reference', 'N/A')}") 
                    #break
                #break
            #break
        #break
            #print()
            
            #
            #if not invoices:
            #    print(f"No invoices found for property: {property_name}")
            #    continue
            #match_and_apply_payments(property['payments'], invoices)


        #    for payment in property['payments']:
        #        print(f"Processing payment: {payment}")
        #        try:
        #            result = apply_payment_to_xero(payment)
        #            print(f"✅ Payment applied successfully. Result: {result}")
        #        except Exception as e:
        #            print(f"❌ Error applying payment: {e}")

        # Optionally: mark email as processed in Gmail (requires modify scope)
        # We can implement this later

if __name__ == "__main__":
    process_payments()

    
        