import sqlite3

DB_NAME = '/tmp/invoices.db'

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
    conn.commit()
    conn.close()

def upsert_invoices(invoices):
    """
    Insert or update multiple invoices into the local SQLite db.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for inv in invoices:
        c.execute('''
            INSERT OR REPLACE INTO invoices
            (invoice_id, contact_name, reference, amount_due, status, issue_date, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            inv['InvoiceID'],
            inv['Contact']['Name'],
            inv.get('Reference', ''),
            inv['AmountDue'],
            inv['Status'],
            inv['DueDateString'] if 'DueDateString' in inv else inv['UpdatedDateUTC'],
            inv['DateString'] if 'DateString' in inv else inv['UpdatedDateUTC']
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

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
    
    # Example usage
    invoices = get_all_invoices()
    if invoices:
        print(f"Found {len(invoices)} invoices in the database.")
    else:
        print("No invoices found in the database.")
    
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