#!/usr/bin/env python3
"""
Quick Performance Test for AI Agent
Simple test to verify performance improvements
"""

import os
import sys
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def test_agent_startup():
    """Test agent startup performance"""
    print("🤖 Testing Agent Startup Performance...")
    start_time = time.time()
    
    try:
        from agent.core_agent import PropertyManagementAgent
        from agent.llm_setup import setup_llm_for_agent
        
        # Setup LLM
        print("  Setting up LLM...")
        llm = setup_llm_for_agent(
            base_url="http://192.168.86.53:11434",
            model_name="llama3",
            temperature=0.1
        )
        
        if llm:
            # Initialize agent with reduced verbosity
            print("  Initializing agent...")
            agent = PropertyManagementAgent(verbose=False)
            agent.set_llm(llm)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Agent startup completed in {duration:.2f} seconds")
            return agent
            
        else:
            print("❌ Failed to initialize LLM")
            return None
            
    except Exception as e:
        print(f"❌ Agent startup failed: {e}")
        return None

def test_basic_tools(agent):
    """Test basic tool functionality"""
    print("\n🔧 Testing Basic Tools...")
    
    try:
        # Test payment matching tool
        payment_matching_tool = next((tool for tool in agent.tools if tool.name == "match_payment"), None)
        
        if payment_matching_tool:
            print("✅ Payment matching tool found")
            
            # Test with a simple payment
            test_payment = {
                'person': 'Anna Camacho',
                'property': '123 Main St',
                'amount': 1500.00,
                'ref': 'TEST-001',
                'date': '2024-01-15'
            }
            
            start_time = time.time()
            result = payment_matching_tool._run(
                payment=test_payment,
                tenant_name='Anna Camacho',
                amount=1500.00,
                payment_date='2024-01-15',
                reference='TEST-001',
                property_name='123 Main St'
            )
            end_time = time.time()
            
            print(f"✅ Payment matching test completed in {end_time - start_time:.3f} seconds")
            print(f"   Result: {result.get('success', False)}")
            
        else:
            print("❌ Payment matching tool not found")
            
    except Exception as e:
        print(f"❌ Tool test failed: {e}")

def main():
    """Main test"""
    print("=" * 50)
    print("🚀 QUICK PERFORMANCE TEST")
    print("=" * 50)
    
    # Test agent startup
    agent = test_agent_startup()
    if not agent:
        print("❌ Cannot proceed without agent")
        return
    
    # Test basic tools
    test_basic_tools(agent)
    
    print("\n" + "=" * 50)
    print("✅ Quick test completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()

