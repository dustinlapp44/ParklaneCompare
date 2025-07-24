from xero_client import apply_payment,authorize_xero

def match_and_apply_payments(payments, invoices):
    """
    For each parsed payment, find matching open invoice and apply payment.
    """
    access_token, tenant_id = authorize_xero(org_name="Parklane Properties")

    for payment in payments:
        unit = payment['unit']
        amount = payment['amount'].replace('$','').replace(',','')
        amount = float(amount)
        
        # 2. Find invoice matching unit and amount
        matched = None
        for invoice in invoices:
            if unit in invoice.get('Reference', '') and invoice['AmountDue'] == amount:
                matched = invoice
                break

        if matched:
            print(f"Applying payment to invoice {matched['InvoiceNumber']} for unit {unit} amount ${amount}")
            apply_payment(access_token, tenant_id, matched['InvoiceID'], amount)
        else:
            print(f"No matching invoice found for unit {unit} amount ${amount}")

