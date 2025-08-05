from XeroClient.xero_client import apply_payment
from Payments.payments_db import get_payments_by_invoice



def match_payment_to_invoice(aptexx_payment, invoices):
    """
    Match the parsed payment to an open invoice and apply the payment.
    """
    ret_invoice = {}
    ## First check if memo is present in the payment
    #memo = aptexx_payment.get('memo', None)
    #if memo:
    #    print(f"  Payment memo found: {memo}. SEND EMAIL")
    #    return None  # No need to match

    if len(invoices) == 1 and invoices[0]['amount_due'] == aptexx_payment['amount']:
        print(f"  Found exact match for payment {aptexx_payment['ref']} with invoice {invoices[0]['invoice_id']}")
        ret_invoice['PAYMENT'] = {'payment': aptexx_payment, 'invoice': invoices[0]}
        return ret_invoice
    
    elif len(invoices) > 1:
        print(f"  Found multiple open invoices for payment {aptexx_payment['ref']}. SEND EMAIL")
        return None
    elif len(invoices) == 1 and invoices[0]['amount_due'] != aptexx_payment['amount']:
        print(f"  Found open invoice {invoices[0]['invoice_id']} for payment {aptexx_payment['ref']} but amount due ${invoices[0]['amount_due']} does not match payment amount ${aptexx_payment['amount']}. SEND EMAIL")
        return None
    else:
        print(f"  No matching open invoice found for payment {aptexx_payment['ref']}. SEND EMAIL")
        return None

def match_and_apply_payments(aptexx_payment, tenant_invoices):
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

    if needs_payment:
        #for invoice in needs_payment:
        #    print(f"  Found open invoice for {invoice['contact_name']} with amount due ${invoice['amount_due']} issued {invoice['issue_date']} due {invoice['due_date']}")
        invoices_to_pay = match_payment_to_invoice(aptexx_payment, needs_payment)
        if invoices_to_pay:
            payment_status = apply_payment(invoices_to_pay)
            if payment_status is None:
                print(f"  Failed to apply payment {aptexx_payment['ref']} to invoice {invoices_to_pay['PAYMENT']['invoice']['invoice_id']}. SEND EMAIL")
                return None
            if payment_status['Status'] != 'OK':
                print(f"  Failed to apply payment {aptexx_payment['ref']} to invoice {invoices_to_pay['PAYMENT']['invoice']['invoice_id']}. SEND EMAIL")
                return None
            return payment_status  # Return the payment for further processing or email notification
        
        else:
            return None  # No matching invoice found, return None for further processing or email notification

    else:
        ## Check to see if payment is already applied to an invoice
        already_paid= False
        for invoice in tenant_invoices:
            payments = get_payments_by_invoice(invoice['invoice_id'])
            for payment in payments:
                if payment['reference'].count(aptexx_payment['ref']) > 0:
                    already_paid = True
        if already_paid:
            print(f"  Payment {aptexx_payment['ref']} already applied to an invoice.")
            print()
            return aptexx_payment
        else:
            print(f"  No open invoices found for payment {aptexx_payment['ref']}. SEND EMAIL")
            return None
                
        