#!/usr/bin/env python3
"""
Debug script to test AI reasoning with REAL payment data
"""

import os
import sys
import logging
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def get_real_tenant_with_invoices():
    """Get a real tenant that has invoices in the database"""
    try:
        import sqlite3
        
        db_path = '/tmp/payments.db'
        if not os.path.exists(db_path):
            print("❌ Database not found at /tmp/payments.db")
            return None
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find a tenant with unpaid invoices
        cursor.execute('''
            SELECT contact_name, COUNT(*) as invoice_count, 
                   SUM(amount_due) as total_due,
                   MIN(amount_due) as min_due,
                   MAX(amount_due) as max_due
            FROM invoices 
            WHERE amount_due > 0 
            GROUP BY contact_name 
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
            LIMIT 5
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        if results:
            print("🔍 Found tenants with multiple unpaid invoices:")
            for i, (name, count, total, min_due, max_due) in enumerate(results):
                print(f"  {i+1}. {name}: {count} invoices, ${total:.2f} total (${min_due:.2f} - ${max_due:.2f})")
            
            # Return the first tenant
            return results[0][0]
        else:
            print("❌ No tenants found with multiple unpaid invoices")
            return None
            
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return None

def test_real_payment_matching():
    """Test payment matching with real data"""
    print("🔍 Testing Payment Matching with REAL Data")
    print("=" * 60)
    
    # Get a real tenant
    tenant_name = get_real_tenant_with_invoices()
    if not tenant_name:
        print("❌ Cannot test without real tenant data")
        return None
    
    print(f"\n🎯 Testing with tenant: {tenant_name}")
    
    # Create a test payment for this tenant with an amount that should trigger AI reasoning
    test_payment = {
        'amount': 1604.0,  # Use the amount from the user's example
        'person': tenant_name,
        'property': 'Test Property', 
        'ref': '999999',  # Use a reference that won't be a duplicate
        'date': '2025-01-14'
    }
    
    print(f"📧 Test Payment: {test_payment}")
    
    try:
        from ai_agent.agent.tools.payment_matching_tools import PaymentMatchingTool
        
        print("\n🔧 Initializing PaymentMatchingTool...")
        payment_matcher = PaymentMatchingTool()
        
        print("🎯 Running payment matching...")
        start_time = time.time()
        
        result = payment_matcher._run(
            payment=test_payment,
            tenant_name=test_payment['person'],
            amount=test_payment['amount'],
            payment_date=test_payment['date'],
            reference=test_payment['ref'],
            property_name=test_payment['property']
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print()
        
        # Detailed analysis
        print("📊 DETAILED RESULTS:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Confidence: {result.get('confidence_score', 0.0):.3f}")
        print(f"  Match Type: {result.get('match_type', 'none')}")
        print(f"  Matched Invoice: {result.get('matched_invoice_id', 'None')}")
        print(f"  Reasoning Length: {len(result.get('reasoning', ''))}")
        print(f"  Recommendations: {len(result.get('recommendations', []))}")
        print()
        
        # Check for AI reasoning
        reasoning_text = result.get('reasoning', '')
        ai_enhanced = 'AI Analysis:' in reasoning_text
        
        print("🤖 AI REASONING ANALYSIS:")
        print(f"  AI reasoning detected: {'✅ YES' if ai_enhanced else '❌ NO'}")
        print(f"  Full reasoning: {reasoning_text}")
        print()
        
        # Check confidence thresholds that should trigger AI
        confidence = result.get('confidence_score', 0.0)
        print("🎯 CONFIDENCE THRESHOLD ANALYSIS:")
        print(f"  Confidence: {confidence:.3f}")
        print(f"  >= 0.9 (no AI needed): {confidence >= 0.9}")
        print(f"  >= 0.7 (medium - should use AI): {confidence >= 0.7}")
        print(f"  < 0.7 (low - should use AI): {confidence < 0.7}")
        print()
        
        # Show the actual path taken
        if result.get('success', False):
            print("✅ Payment matching succeeded - job should be created")
        else:
            print("❌ Payment matching failed - checking why...")
            match_type = result.get('match_type', 'none')
            if match_type == 'duplicate':
                print("  → Duplicate payment detected")
            elif match_type == 'none':
                print("  → No invoices found for tenant")
            else:
                print(f"  → Other failure: {match_type}")
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_database_invoices_for_tenant(tenant_name):
    """Check what invoices exist for the tenant"""
    print(f"\n📋 Checking Database Invoices for: {tenant_name}")
    print("=" * 60)
    
    try:
        import sqlite3
        
        conn = sqlite3.connect('/tmp/payments.db')
        cursor = conn.cursor()
        
        # Get invoices for this tenant
        cursor.execute('''
            SELECT invoice_id, contact_name, amount_due, status, issue_date
            FROM invoices 
            WHERE contact_name LIKE ?
            ORDER BY issue_date DESC
            LIMIT 10
        ''', (f'%{tenant_name}%',))
        
        invoices = cursor.fetchall()
        conn.close()
        
        if invoices:
            print(f"📄 Found {len(invoices)} invoices for {tenant_name}:")
            for inv_id, contact, amount, status, date in invoices:
                print(f"  • {inv_id}: ${amount:.2f} ({status}) - {date} - {contact}")
        else:
            print(f"❌ No invoices found for {tenant_name}")
        
        return invoices
        
    except Exception as e:
        print(f"❌ Error checking invoices: {e}")
        return []

if __name__ == "__main__":
    print("🔬 Real Payment AI Reasoning Debug")
    print("=" * 60)
    
    # Step 1: Test with real data
    result = test_real_payment_matching()
    
    if result:
        tenant_name = result.get('tenant_name') or 'Unknown'
        
        # Step 2: Check what invoices exist for this tenant
        invoices = check_database_invoices_for_tenant(tenant_name)
        
        # Step 3: Summary
        print("\n📋 SUMMARY")
        print("=" * 60)
        print(f"Payment matching result: {'✅ Success' if result.get('success') else '❌ Failed'}")
        print(f"Confidence: {result.get('confidence_score', 0.0):.3f}")
        print(f"AI reasoning used: {'✅ YES' if 'AI Analysis:' in result.get('reasoning', '') else '❌ NO'}")
        print(f"Invoices found: {len(invoices)}")
        
        # Explain why AI reasoning wasn't used
        if 'AI Analysis:' not in result.get('reasoning', ''):
            confidence = result.get('confidence_score', 0.0)
            if not result.get('success', False):
                print("🔍 AI reasoning not used because: Payment matching failed early")
            elif confidence >= 0.9:
                print("🔍 AI reasoning not used because: High confidence (≥0.9)")
            else:
                print("🔍 AI reasoning should have been used - this is the bug!")

