#!/usr/bin/env python3
"""
Debug script to trace AI reasoning in payment matching
"""

import os
import sys
import logging
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_single_payment_reasoning():
    """Test a single payment to see where AI reasoning fails"""
    print("🔍 Testing Payment Matching with AI Reasoning")
    print("=" * 60)
    
    try:
        # Import the payment matching tool
        from ai_agent.agent.tools.payment_matching_tools import PaymentMatchingTool
        
        # Create a test payment that should trigger AI reasoning
        test_payment = {
            'amount': 1500.0,
            'person': 'John Smith',
            'property': 'Test Property', 
            'ref': '123456',
            'date': '2025-01-14'
        }
        
        print(f"📧 Test Payment: {test_payment}")
        print()
        
        # Initialize the payment matching tool
        print("🔧 Initializing PaymentMatchingTool...")
        payment_matcher = PaymentMatchingTool()
        print("✅ PaymentMatchingTool initialized")
        print()
        
        # Test the matching process
        print("🎯 Running payment matching...")
        print("⏱️  Starting timer...")
        
        import time
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
        
        # Analyze the result
        print("📊 RESULTS:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Confidence: {result.get('confidence_score', 0.0):.2f}")
        print(f"  Match Type: {result.get('match_type', 'none')}")
        print(f"  Reasoning: {result.get('reasoning', 'No reasoning')}")
        print()
        
        # Check if AI reasoning was used
        reasoning_text = result.get('reasoning', '')
        ai_enhanced = 'AI Analysis:' in reasoning_text
        
        print("🤖 AI REASONING CHECK:")
        print(f"  AI reasoning detected: {'✅ YES' if ai_enhanced else '❌ NO'}")
        print(f"  Full reasoning: {reasoning_text}")
        print()
        
        # Check confidence thresholds
        confidence = result.get('confidence_score', 0.0)
        print("🎯 CONFIDENCE ANALYSIS:")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Should trigger AI reasoning: {'✅ YES' if confidence < 0.9 else '❌ NO'}")
        print(f"  Threshold check: confidence ({confidence:.2f}) < 0.9 = {confidence < 0.9}")
        print()
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_ai_reasoning_tool_directly():
    """Test the AI reasoning tool directly"""
    print("\n🧪 Testing AI Reasoning Tool Directly")
    print("=" * 60)
    
    try:
        from ai_agent.agent.tools.ai_reasoning_tools import AIReasoningTool
        
        print("🔧 Initializing AIReasoningTool...")
        ai_tool = AIReasoningTool()
        print("✅ AIReasoningTool initialized")
        
        # Test with a simple scenario
        test_data = {
            'amount': 1500.0,
            'person': 'John Smith',
            'property': 'Test Property',
            'ref': '123456',
            'date': '2025-01-14'
        }
        
        test_invoices = [
            {'InvoiceID': 'INV001', 'AmountDue': 1200.0, 'ContactName': 'John Smith', 'Date': '2025-01-01'},
            {'InvoiceID': 'INV002', 'AmountDue': 800.0, 'ContactName': 'John Smith', 'Date': '2025-01-05'}
        ]
        
        test_matches = [{'name': 'John Smith', 'confidence': 1.0}]
        
        context = {
            'payment_amount': 1500.0,
            'algorithmic_confidence': 0.6,
            'algorithmic_reasoning': 'Multiple matches found',
            'match_type': 'multiple'
        }
        
        print("🎯 Running AI reasoning...")
        start_time = time.time()
        
        ai_result = ai_tool._run(
            scenario_type='multiple_invoices',
            payment_data=test_data,
            available_invoices=test_invoices,
            tenant_matches=test_matches,
            context=context
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📊 AI Result: {ai_result}")
        
        return ai_result
        
    except Exception as e:
        print(f"❌ ERROR testing AI tool: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_llm_availability():
    """Check if LLM is available for AI reasoning"""
    print("\n🤖 Checking LLM Availability")
    print("=" * 60)
    
    try:
        from ai_agent.agent.llm_setup import setup_llm_for_agent
        
        print("📡 Testing LLM connection...")
        llm = setup_llm_for_agent()
        
        if llm:
            print("✅ LLM is available")
            
            # Test a simple query
            print("🧪 Testing simple LLM query...")
            start_time = time.time()
            response = llm.invoke("Hello, this is a test. Please respond with 'LLM working correctly'.")
            end_time = time.time()
            
            print(f"⏱️  LLM response time: {end_time - start_time:.2f} seconds")
            print(f"📝 LLM response: {response}")
            return True
        else:
            print("❌ LLM is NOT available")
            return False
            
    except Exception as e:
        print(f"❌ ERROR testing LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 AI Reasoning Debug Analysis")
    print("=" * 60)
    
    # Step 1: Check LLM availability
    llm_available = check_llm_availability()
    
    # Step 2: Test payment matching
    payment_result = test_single_payment_reasoning()
    
    # Step 3: Test AI reasoning tool directly
    ai_result = test_ai_reasoning_tool_directly()
    
    # Summary
    print("\n📋 SUMMARY")
    print("=" * 60)
    print(f"LLM Available: {'✅' if llm_available else '❌'}")
    print(f"Payment Matching: {'✅' if payment_result else '❌'}")
    print(f"AI Reasoning Tool: {'✅' if ai_result else '❌'}")
    
    if payment_result:
        ai_used = 'AI Analysis:' in payment_result.get('reasoning', '')
        print(f"AI Reasoning Used in Payment Matching: {'✅' if ai_used else '❌'}")
