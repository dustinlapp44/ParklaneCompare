#!/usr/bin/env python3
"""
Test Runner for AI Agent
Runs unit tests, integration tests, and performance tests.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_file(test_file: str, test_type: str = "Test") -> bool:
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {test_type}: {test_file}")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=300)
        end_time = time.time()
        
        print(f"Duration: {end_time - start_time:.2f} seconds")
        
        if result.stdout:
            print("Output:")
            print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {test_type} PASSED: {test_file}")
            return True
        else:
            print(f"❌ {test_type} FAILED: {test_file}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_type} TIMEOUT: {test_file}")
        return False
    except Exception as e:
        print(f"💥 {test_type} ERROR: {test_file} - {e}")
        return False

def run_unit_tests():
    """Run all unit tests."""
    print("\n🧪 Running Unit Tests")
    print("="*60)
    
    unit_tests = [
        "tests/unit/test_email_parsing.py",
        "tests/unit/test_payment_matching.py", 
        "tests/unit/test_xero_tools.py",
        "tests/unit/test_hybrid_matching.py"
    ]
    
    passed = 0
    total = 0
    
    for test_file in unit_tests:
        if os.path.exists(test_file):
            total += 1
            if run_test_file(test_file, "Unit Test"):
                passed += 1
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    print(f"\n📊 Unit Tests Summary: {passed}/{total} passed")
    return passed, total

def run_integration_tests():
    """Run all integration tests."""
    print("\n🔗 Running Integration Tests")
    print("="*60)
    
    integration_tests = [
        "tests/integration/test_llm_performance.py",
        "tests/integration/test_sync_manager.py",
        "tests/integration/test_with_real_emails.py",
        "tests/integration/test_full_integration.py",
        "tests/integration/test_performance.py"
    ]
    
    passed = 0
    total = 0
    
    for test_file in integration_tests:
        if os.path.exists(test_file):
            total += 1
            if run_test_file(test_file, "Integration Test"):
                passed += 1
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    print(f"\n📊 Integration Tests Summary: {passed}/{total} passed")
    return passed, total

def run_scripts():
    """Run utility scripts."""
    print("\n🛠️  Running Utility Scripts")
    print("="*60)
    
    scripts = [
        "scripts/init_database.py",
        "scripts/create_test_data.py",
        "scripts/create_sample_jobs.py"
    ]
    
    passed = 0
    total = 0
    
    for script in scripts:
        if os.path.exists(script):
            total += 1
            if run_test_file(script, "Script"):
                passed += 1
        else:
            print(f"⚠️  Script not found: {script}")
    
    print(f"\n📊 Scripts Summary: {passed}/{total} passed")
    return passed, total

def run_performance_tests():
    """Run performance tests."""
    print("\n⚡ Running Performance Tests")
    print("="*60)
    
    perf_tests = [
        "scripts/simple_performance_test.py",
        "scripts/quick_performance_test.py"
    ]
    
    passed = 0
    total = 0
    
    for test_file in perf_tests:
        if os.path.exists(test_file):
            total += 1
            if run_test_file(test_file, "Performance Test"):
                passed += 1
        else:
            print(f"⚠️  Performance test not found: {test_file}")
    
    print(f"\n📊 Performance Tests Summary: {passed}/{total} passed")
    return passed, total

def main():
    """Main test runner."""
    print("🚀 AI Agent Test Suite")
    print("="*60)
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track overall results
    total_passed = 0
    total_tests = 0
    
    # Run different test categories
    unit_passed, unit_total = run_unit_tests()
    total_passed += unit_passed
    total_tests += unit_total
    
    integration_passed, integration_total = run_integration_tests()
    total_passed += integration_passed
    total_tests += integration_total
    
    script_passed, script_total = run_scripts()
    total_passed += script_passed
    total_tests += script_total
    
    perf_passed, perf_total = run_performance_tests()
    total_passed += perf_passed
    total_tests += perf_total
    
    # Final summary
    print("\n" + "="*60)
    print("🎯 FINAL TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
    
    if total_passed == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

