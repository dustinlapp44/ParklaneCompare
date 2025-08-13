#!/usr/bin/env python3
"""
Debug script to check sync and database issues
"""

import os
import sys
import time
import sqlite3

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def check_database():
    """Check if database exists and is accessible"""
    print("🔍 Checking database...")
    
    db_path = '/tmp/payments.db'
    
    # Check if file exists
    if os.path.exists(db_path):
        print(f"✅ Database file exists: {db_path}")
        print(f"   Size: {os.path.getsize(db_path)} bytes")
    else:
        print(f"❌ Database file not found: {db_path}")
        return False
    
    # Try to connect
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Database connected successfully")
        print(f"   Tables: {[t[0] for t in tables]}")
        
        # Try a simple count query
        try:
            cursor.execute("SELECT COUNT(*) FROM invoices")
            count = cursor.fetchone()[0]
            print(f"   Invoices count: {count}")
        except Exception as e:
            print(f"   ❌ Error counting invoices: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_mock_data():
    """Check mock data availability"""
    print("\n🔍 Checking mock data...")
    
    test_data_path = os.path.join(project_root, "ai_agent", "data", "test_data", "mock_xero_data.json")
    
    if os.path.exists(test_data_path):
        print(f"✅ Mock data file exists: {test_data_path}")
        print(f"   Size: {os.path.getsize(test_data_path)} bytes")
        
        # Try to load it
        try:
            import json
            with open(test_data_path, 'r') as f:
                data = json.load(f)
            print(f"   Invoices in mock data: {len(data.get('invoices', []))}")
            return True
        except Exception as e:
            print(f"   ❌ Error loading mock data: {e}")
            return False
    else:
        print(f"❌ Mock data file not found: {test_data_path}")
        return False

def test_sync_step_by_step():
    """Test sync process step by step"""
    print("\n🔍 Testing sync step by step...")
    
    try:
        # Test 1: Import sync manager
        print("1. Importing sync manager...")
        from sync_manager import SyncManager
        print("   ✅ SyncManager imported")
        
        # Test 2: Create sync manager
        print("2. Creating sync manager...")
        sync_manager = SyncManager(sync_interval_hours=6)
        print("   ✅ SyncManager created")
        
        # Test 3: Test Xero tool
        print("3. Testing Xero tool...")
        from agent.tools.xero_tools import XeroInvoiceTool
        xero_tool = XeroInvoiceTool()
        print("   ✅ XeroInvoiceTool created")
        
        # Test 4: Test mock data retrieval
        print("4. Testing mock data retrieval...")
        start_time = time.time()
        mock_result = xero_tool._get_mock_invoices("", "2025-05-01", "2025-08-12")
        end_time = time.time()
        print(f"   ✅ Mock data retrieved in {end_time - start_time:.2f}s")
        print(f"   Invoices found: {len(mock_result.get('invoices', []))}")
        
        # Test 5: Test database upsert
        print("5. Testing database upsert...")
        try:
            import Payments.payments_db as payments_db
            start_time = time.time()
            payments_db.upsert_invoices(mock_result.get('invoices', []))
            end_time = time.time()
            print(f"   ✅ Database upsert completed in {end_time - start_time:.2f}s")
        except Exception as e:
            print(f"   ❌ Database upsert failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Sync test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main diagnostic function"""
    print("🔧 Sync and Database Diagnostic")
    print("=" * 40)
    
    # Check database
    db_ok = check_database()
    
    # Check mock data
    mock_ok = check_mock_data()
    
    # Test sync process
    sync_ok = test_sync_step_by_step()
    
    # Summary
    print("\n📋 Diagnostic Summary")
    print("=" * 20)
    print(f"Database: {'✅ OK' if db_ok else '❌ FAILED'}")
    print(f"Mock Data: {'✅ OK' if mock_ok else '❌ FAILED'}")
    print(f"Sync Process: {'✅ OK' if sync_ok else '❌ FAILED'}")
    
    if not db_ok:
        print("\n💡 Database issues detected. This might explain the hanging queries.")
    if not sync_ok:
        print("\n💡 Sync process issues detected. This might explain the 3-second syncs.")

if __name__ == "__main__":
    main()
