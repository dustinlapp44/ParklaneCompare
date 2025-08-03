from XeroClient.xero_client import apply_payment
from Payments.payments_db import get_payments_by_invoice

def create_payment(payment,invoice):
    pass

def match_and_apply_payments(aptexx_payments, tenant_invoices):
    """
    For each parsed payment, find matching open invoice and apply payment.
    """
    needs_payment = []
    for invoice in tenant_invoices:
        issue_date = invoice['issue_date']
        due_date = invoice['due_date']
        #print(f"    Found invoice: {invoice['invoice_id']} for amount ${invoice['amount_due']} issued {issue_date} due {due_date}")
        # Check if invoice is open
        if invoice['status'] == 'AUTHORISED':
            needs_payment.append(invoice)
    
    for invoice in needs_payment:
        print(f"  Found open invoice: {invoice['invoice_id']} for amount ${invoice['amount_due']} issued {invoice['issue_date']} due {invoice['due_date']}")


        #payments = get_payments_by_invoice(invoice['invoice_id']) 
        #for payment in payments:
        #    print(f"      Payment: {payment['amount']} on {payment['date']}  APTEXX info: {payment['reference']}") 

    #for payment in payments:
    #    unit = payment['unit']
    #    amount = payment['amount'].replace('$','').replace(',','')
    #    amount = float(amount)
    #    
    #    # 2. Find invoice matching unit and amount
    #    matched = None
    #    for invoice in invoices:
    #        if unit in invoice.get('Reference', '') and invoice['AmountDue'] == amount:
    #            matched = invoice
    #            break
#
    #    if matched:
    #        print(f"Applying payment to invoice {matched['InvoiceNumber']} for unit {unit} amount ${amount}")
    #        #apply_payment(access_token, tenant_id, matched['InvoiceID'], amount)
    #    else:
    #        print(f"No matching invoice found for unit {unit} amount ${amount}")
#
