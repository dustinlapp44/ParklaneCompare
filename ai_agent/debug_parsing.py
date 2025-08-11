"""
Debug script to test parsing logic
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from Payments.parser import parse_aptexx_email, parse_html_payments

def test_parsing():
    """Test the parsing functions directly"""
    
    # Read the sample email
    sample_email_path = os.path.join(project_root, "Payments", "sample_email.txt")
    
    with open(sample_email_path, 'r', encoding='utf-8') as f:
        email_content = f.read()
    
    print("Testing parse_aptexx_email function...")
    lines = email_content.split('\n')
    result = parse_aptexx_email(lines)
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    
    if result:
        print("First property result:")
        print(result[0])
        
        # Count total payments
        total_payments = 0
        for property_data in result:
            total_payments += len(property_data['payments'])
        
        print(f"Total payments found: {total_payments}")
        
        # Show first few payments
        for i, property_data in enumerate(result[:3]):
            print(f"\nProperty {i+1}: {property_data['property']}")
            for j, payment in enumerate(property_data['payments'][:2]):
                print(f"  Payment {j+1}: {payment}")

if __name__ == "__main__":
    test_parsing()
