import sqlite3

DB_NAME = '/tmp/payments.db'

def reset_db():
    """
    Reset the local SQLite database by dropping the invoices table if it exists.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS invoices')
    c.execute('DROP TABLE IF EXISTS payments')
    conn.commit()
    conn.close()
    init_db()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            contact_name TEXT,
            reference TEXT,
            amount_due REAL,
            status TEXT,
            issue_date TEXT,
            due_date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            invoice_id TEXT,
            amount REAL,
            date TEXT,
            reference TEXT,
            bank_transaction_id TEXT,
            status TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
        )
    ''')
    conn.commit()
    conn.close()

def upsert_invoices(invoices):
    """
    Insert or update multiple invoices into the local SQLite db.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for inv in invoices:
        # Check if Payments key exists before accessing it
        payments = inv.get('Payments', [])
       
        # Handle different contact name formats
        contact_name = inv.get('ContactName') or inv.get('Contact', {}).get('Name', 'Unknown')
        
        # Handle different date formats
        issue_date = inv.get('DateString') or inv.get('Date') or inv.get('UpdatedDateUTC', '')
        due_date = inv.get('DueDateString') or inv.get('DueDate') or inv.get('UpdatedDateUTC', '')
        
        c.execute('''
            INSERT OR REPLACE INTO invoices
            (invoice_id, contact_name, reference, amount_due, status, issue_date, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            inv['InvoiceID'],
            contact_name,
            inv.get('Reference', ''),
            inv['AmountDue'],
            inv['Status'],
            issue_date,
            due_date
        ))
        # Handle payments
        for payment in payments:
            c.execute('''
                INSERT OR REPLACE INTO payments (
                    payment_id,
                    invoice_id,
                    amount,
                    date,
                    reference,
                    bank_transaction_id,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment['PaymentID'],
                inv['InvoiceID'],
                payment['Amount'],
                payment['Date'],
                payment.get('Reference'),
                payment.get('BankTransactionID'),
                payment.get('Status'),
            ))
    conn.commit()
    conn.close()

def get_invoices_by_contact(contact_substring):
    """
    Query invoices by a substring of the contact name (case-insensitive).
    Returns a list of dictionaries using column names as keys.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    c = conn.cursor()
    c.execute('''
        SELECT * FROM invoices
        WHERE lower(contact_name) LIKE ?
    ''', ('%' + contact_substring.lower() + '%',))
    rows = c.fetchall()
    conn.close()

    # Convert sqlite3.Row objects to dictionaries
    results = [dict(row) for row in rows]
    return results


def get_invoices_by_unit(unit_substring):
    """
    Query invoices by a substring of the unit reference (case-insensitive).
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM invoices
        WHERE lower(reference) LIKE ?
    ''', ('%' + unit_substring.lower() + '%',))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_invoices():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM invoices')
    rows = c.fetchall()
    conn.close()
    return rows

def get_payments_by_invoice(invoice_id):
    """
    Get all payments associated with a specific invoice ID.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    c = conn.cursor()
    c.execute('SELECT * FROM payments WHERE invoice_id = ?', (invoice_id,))
    rows = c.fetchall()
    payments = [dict(row) for row in rows]  # Convert to list of dicts
    conn.close()
    return payments

def get_all_payments():
    """
    Get all payments from the database.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM payments')
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    
    reset_db()
    #init_db()
    print("Database initialized.")
    
    # Example usage
    invoices = get_all_invoices()
    if invoices:
        print(f"Found {len(invoices)} invoices in the database.")
    else:
        print("No invoices found in the database.")

    payments = get_all_payments()
    if payments:
        print(f"Found {len(payments)} payments in the database.")
    else:
        print("No payments found in the database.")
    
    if False:
        # Example insert/update
        upsert_invoices([{
            'InvoiceID': 'INV-123',
            'Contact': {'Name': 'John Doe'},
            'Reference': 'Unit 101',
            'AmountDue': 1500.00,
            'Status': 'AUTHORISED',
            'DateString': '2025-07-22T12:00:00Z',
            'DueDateString': '2025-07-22T12:00:00Z'
        }])
        print("Sample invoice inserted/updated.")

        invoices = get_invoices_by_contact('John')
        print(f"Found {len(invoices)} invoices for contact 'John':")
        for inv in invoices:
            print(inv)  