import os, sys
# Add parent directory to path for xero_client import
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from xero_client import pull_tenant_invoices
from invoice_db import init_db, upsert_invoices



def refresh_invoice_cache(start_date, end_date):
    """
    Fetches all invoices from Xero and refreshes local SQLite db.
    """
    init_db()
    all_invoices = []

    #invoices = get_invoices_for_db(access_token, tenant_id, start_date, end_date, page=page)
    invoices = pull_tenant_invoices(start_date, end_date)
    if not invoices:
        print("No invoices found in the specified date range.")
    all_invoices.extend(invoices)


    upsert_invoices(all_invoices)
    print(f"✅ Refreshed {len(all_invoices)} invoices into local cache.")



if __name__ == "__main__":
    
    # Define the date range for fetching invoices
    start_date = "2025-01-01"
    end_date = "2025-07-23"

    refresh_invoice_cache(start_date, end_date)