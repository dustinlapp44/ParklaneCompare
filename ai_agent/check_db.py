#!/usr/bin/env python3
"""
Quick database checker to debug payment matching issues.
"""

import sqlite3
import sys

DB_PATH = "/tmp/payments.db"

def check_database():
    """Check database contents and structure"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            print("🔍 Database Check Results")
            print("=" * 50)
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"📋 Tables found: {[table[0] for table in tables]}")
            print()
            
            # Check invoices
            cursor.execute("SELECT COUNT(*) FROM invoices")
            invoice_count = cursor.fetchone()[0]
            print(f"📄 Total invoices: {invoice_count}")
            
            if invoice_count > 0:
                cursor.execute("SELECT contact_name, amount_due, status FROM invoices LIMIT 5")
                sample_invoices = cursor.fetchall()
                print("📄 Sample invoices:")
                for inv in sample_invoices:
                    print(f"   - {inv[0]}: ${inv[1]} ({inv[2]})")
            print()
            
            # Check payments
            cursor.execute("SELECT COUNT(*) FROM payments")
            payment_count = cursor.fetchone()[0]
            print(f"💰 Total payments: {payment_count}")
            
            if payment_count > 0:
                cursor.execute("SELECT reference, amount, date FROM payments LIMIT 5")
                sample_payments = cursor.fetchall()
                print("💰 Sample payments:")
                for pay in sample_payments:
                    print(f"   - {pay[0]}: ${pay[1]} ({pay[2]})")
            print()
            
            # Check for specific tenant (example)
            test_tenant = "JENNIFER HUNTER"
            cursor.execute("SELECT COUNT(*) FROM invoices WHERE contact_name LIKE ?", (f"%{test_tenant}%",))
            tenant_invoices = cursor.fetchone()[0]
            print(f"🔍 Invoices for '{test_tenant}': {tenant_invoices}")
            
            if tenant_invoices > 0:
                cursor.execute("SELECT invoice_id, amount_due, status FROM invoices WHERE contact_name LIKE ?", (f"%{test_tenant}%",))
                tenant_data = cursor.fetchall()
                print("📄 Tenant invoices:")
                for inv in tenant_data:
                    print(f"   - {inv[0]}: ${inv[1]} ({inv[2]})")
            print()
            
            # Check payment references
            cursor.execute("SELECT DISTINCT reference FROM payments WHERE reference IS NOT NULL AND reference != '' LIMIT 10")
            payment_refs = cursor.fetchall()
            print(f"🔗 Payment references found: {len(payment_refs)}")
            if payment_refs:
                print("🔗 Sample payment references:")
                for ref in payment_refs:
                    print(f"   - {ref[0]}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def search_tenant(tenant_name):
    """Search for a specific tenant"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            print(f"🔍 Searching for tenant: {tenant_name}")
            print("=" * 50)
            
            # Search invoices
            cursor.execute("SELECT invoice_id, contact_name, amount_due, status, reference FROM invoices WHERE contact_name LIKE ?", (f"%{tenant_name}%",))
            invoices = cursor.fetchall()
            
            print(f"📄 Invoices found: {len(invoices)}")
            for inv in invoices:
                print(f"   - {inv[0]}: {inv[1]} - ${inv[2]} ({inv[3]}) - Ref: {inv[4]}")
            
            # Search payments
            cursor.execute("SELECT payment_id, reference, amount, date FROM payments WHERE reference LIKE ?", (f"%{tenant_name}%",))
            payments = cursor.fetchall()
            
            print(f"💰 Payments found: {len(payments)}")
            for pay in payments:
                print(f"   - {pay[0]}: {pay[1]} - ${pay[2]} ({pay[3]})")
                
    except Exception as e:
        print(f"❌ Error searching tenant: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        search_tenant(sys.argv[1])
    else:
        check_database()
