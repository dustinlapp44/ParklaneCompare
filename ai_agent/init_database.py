#!/usr/bin/env python3
"""
Database Initialization Script
Creates all required tables for the AI agent
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def init_database():
    """Initialize the database with all required tables"""
    
    db_path = '/tmp/payments.db'
    
    print("🗄️  Initializing Database...")
    print(f"   Database path: {db_path}")
    
    try:
        # Import the original payments_db module
        from Payments.payments_db import init_db, reset_db
        
        # Initialize the original tables (invoices and payments)
        print("   Creating invoices and payments tables...")
        init_db()
        
        # Create the payment_tracking table for duplicate prevention
        print("   Creating payment_tracking table...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_tracking (
                payment_id TEXT PRIMARY KEY,
                xero_payment_id TEXT,
                amount REAL,
                date TEXT,
                reference TEXT,
                status TEXT,
                applied_to_invoice TEXT,
                sync_timestamp TEXT
            )
        ''')
        
        # Create a sync_log table for tracking database syncs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT,
                start_date TEXT,
                end_date TEXT,
                records_processed INTEGER,
                success BOOLEAN,
                error_message TEXT,
                sync_timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Database initialized successfully!")
        
        # Verify tables exist
        verify_tables(db_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def verify_tables(db_path):
    """Verify that all required tables exist"""
    print("\n🔍 Verifying Database Tables...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['invoices', 'payments', 'payment_tracking', 'sync_log']
        
        for table in required_tables:
            if table in tables:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   ✅ {table}: {count} rows")
            else:
                print(f"   ❌ {table}: Missing!")
        
        conn.close()
        
        # Check if all required tables exist
        missing_tables = [table for table in required_tables if table not in tables]
        if missing_tables:
            print(f"\n❌ Missing tables: {missing_tables}")
            return False
        else:
            print("\n✅ All required tables exist!")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    print("\n📝 Creating Sample Data...")
    
    try:
        from Payments.payments_db import upsert_invoices
        
        # Sample invoice data
        sample_invoices = [
            {
                'InvoiceID': 'INV-001',
                'Contact': {'Name': 'John Smith'},
                'Reference': 'Unit 101',
                'AmountDue': 1500.00,
                'Status': 'AUTHORISED',
                'DateString': '2024-01-01T00:00:00Z',
                'DueDateString': '2024-01-31T00:00:00Z',
                'Payments': []
            },
            {
                'InvoiceID': 'INV-002',
                'Contact': {'Name': 'Jane Doe'},
                'Reference': 'Unit 102',
                'AmountDue': 1200.00,
                'Status': 'AUTHORISED',
                'DateString': '2024-01-01T00:00:00Z',
                'DueDateString': '2024-01-31T00:00:00Z',
                'Payments': []
            },
            {
                'InvoiceID': 'INV-003',
                'Contact': {'Name': 'Bob Johnson'},
                'Reference': 'Unit 103',
                'AmountDue': 1800.00,
                'Status': 'AUTHORISED',
                'DateString': '2024-01-01T00:00:00Z',
                'DueDateString': '2024-01-31T00:00:00Z',
                'Payments': []
            }
        ]
        
        # Insert sample invoices
        upsert_invoices(sample_invoices)
        print(f"   ✅ Created {len(sample_invoices)} sample invoices")
        
        # Create sample payment tracking entries
        db_path = '/tmp/payments.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        sample_payments = [
            ('PAY-001', 'PAY-001', 1500.00, '2024-01-15', 'PAY123456', 'AUTHORISED', 'INV-001', datetime.now().isoformat()),
            ('PAY-002', 'PAY-002', 1200.00, '2024-01-16', 'PAY789012', 'AUTHORISED', 'INV-002', datetime.now().isoformat()),
        ]
        
        for payment in sample_payments:
            cursor.execute('''
                INSERT OR REPLACE INTO payment_tracking
                (payment_id, xero_payment_id, amount, date, reference, status, applied_to_invoice, sync_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', payment)
        
        conn.commit()
        conn.close()
        print(f"   ✅ Created {len(sample_payments)} sample payment tracking entries")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

def main():
    """Main initialization function"""
    print("=" * 60)
    print("🗄️  DATABASE INITIALIZATION")
    print("=" * 60)
    
    # Initialize database
    if not init_database():
        print("❌ Database initialization failed")
        return
    
    # Create sample data (optional)
    create_sample = input("\nCreate sample data for testing? (y/n): ").lower().strip()
    if create_sample == 'y':
        create_sample_data()
    
    print("\n" + "=" * 60)
    print("✅ Database initialization completed!")
    print("=" * 60)
    print("\n🎯 Next Steps:")
    print("   1. Run database sync to populate with real data")
    print("   2. Test payment matching with the new tables")
    print("   3. Verify duplicate payment prevention works")

if __name__ == "__main__":
    main()

