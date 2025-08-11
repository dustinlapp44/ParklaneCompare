"""
Create comprehensive test data for AI agent development
Includes sample emails, parsed payments, and mock Xero data
"""

import os
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def create_test_email_data():
    """Create sample email data for testing"""
    
    # Sample HTML email content (simplified version of real Aptexx emails)
    sample_html_email = """
    <html>
    <body>
        <h2>Jul 20 2025 Payment Summary</h2>
        <table border="1">
            <tr>
                <th>Ref #</th>
                <th>Date</th>
                <th>Method</th>
                <th>Person</th>
                <th>Unit</th>
                <th>Amount</th>
            </tr>
            <tr><td colspan="6"><b>Barcelona - Rent (Non-Integrated)</b></td></tr>
            <tr>
                <td>132510794</td>
                <td>20 Jul 2025 23:41:04 MDT</td>
                <td>VISA DEBIT #5553</td>
                <td>Anna Camacho</td>
                <td>1426-103</td>
                <td>$505.00</td>
            </tr>
            <tr>
                <td>132510789</td>
                <td>20 Jul 2025 23:39:47 MDT</td>
                <td>VISA CREDIT #9784</td>
                <td>Anna Camacho</td>
                <td>1426-103</td>
                <td>$1,200.00</td>
            </tr>
            <tr><td colspan="6"><b>Camels Back - Rent (Non-Integrated)</b></td></tr>
            <tr>
                <td>132487744</td>
                <td>20 Jul 2025 05:05:10 MDT</td>
                <td>ACH #7092</td>
                <td>Thais Holladay</td>
                <td>139</td>
                <td>$1,385.00</td>
            </tr>
            <tr>
                <td>132487740</td>
                <td>20 Jul 2025 05:05:09 MDT</td>
                <td>ACH #2731</td>
                <td>Erica Chown 2</td>
                <td>1414-223</td>
                <td>$1,510.00</td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Sample text email content
    sample_text_email = """
    Jul 20 2025 Payment Summary
    Ref #	Date	Method	Person	Unit	Amount
    Barcelona - Rent (Non-Integrated)
    132510794	20 Jul 2025 23:41:04 MDT	VISA DEBIT #5553	Anna Camacho	1426-103	$505.00
    132510789	20 Jul 2025 23:39:47 MDT	VISA CREDIT #9784	Anna Camacho	1426-103	$1,200.00
    Subtotal	$1,705.00
    Camels Back - Rent (Non-Integrated)
    132487744	20 Jul 2025 05:05:10 MDT	ACH #7092	Thais Holladay	139	$1,385.00
    132487740	20 Jul 2025 05:05:09 MDT	ACH #2731	Erica Chown 2	1414-223	$1,510.00
    Subtotal	$2,895.00
    """
    
    return {
        "html_email": sample_html_email,
        "text_email": sample_text_email
    }

def create_mock_xero_data():
    """Create mock Xero data for testing (read-only)"""
    
    # Mock invoices that would match the test payments
    mock_invoices = [
        {
            "InvoiceID": "INV-001",
            "ContactName": "Anna Camacho",
            "InvoiceNumber": "INV-2025-001",
            "Date": "2025-07-01",
            "DueDate": "2025-07-31",
            "Total": 1705.00,
            "AmountDue": 1705.00,
            "Status": "AUTHORISED",
            "LineItems": [
                {
                    "Description": "Rent - July 2025",
                    "Quantity": 1,
                    "UnitAmount": 1705.00,
                    "LineAmount": 1705.00
                }
            ]
        },
        {
            "InvoiceID": "INV-002", 
            "ContactName": "Thais Holladay",
            "InvoiceNumber": "INV-2025-002",
            "Date": "2025-07-01",
            "DueDate": "2025-07-31",
            "Total": 1385.00,
            "AmountDue": 1385.00,
            "Status": "AUTHORISED",
            "LineItems": [
                {
                    "Description": "Rent - July 2025",
                    "Quantity": 1,
                    "UnitAmount": 1385.00,
                    "LineAmount": 1385.00
                }
            ]
        },
        {
            "InvoiceID": "INV-003",
            "ContactName": "Erica Chown 2",
            "InvoiceNumber": "INV-2025-003", 
            "Date": "2025-07-01",
            "DueDate": "2025-07-31",
            "Total": 1510.00,
            "AmountDue": 1510.00,
            "Status": "AUTHORISED",
            "LineItems": [
                {
                    "Description": "Rent - July 2025",
                    "Quantity": 1,
                    "UnitAmount": 1510.00,
                    "LineAmount": 1510.00
                }
            ]
        }
    ]
    
    # Mock payments (existing payments in Xero)
    mock_payments = [
        {
            "PaymentID": "PAY-001",
            "InvoiceID": "INV-001",
            "Amount": 505.00,
            "Date": "2025-07-20",
            "Reference": "132510794",
            "Status": "AUTHORISED"
        },
        {
            "PaymentID": "PAY-002",
            "InvoiceID": "INV-002", 
            "Amount": 1385.00,
            "Date": "2025-07-20",
            "Reference": "132487744",
            "Status": "AUTHORISED"
        }
    ]
    
    return {
        "invoices": mock_invoices,
        "payments": mock_payments
    }

def create_test_scenarios():
    """Create various test scenarios for different edge cases"""
    
    scenarios = {
        "perfect_match": {
            "description": "Payment amount exactly matches invoice balance",
            "payment": {
                "person": "Anna Camacho",
                "amount": 1705.00,
                "ref": "132510794",
                "property": "Barcelona - Rent (Non-Integrated)"
            },
            "expected_invoice": "INV-001"
        },
        "partial_payment": {
            "description": "Payment is less than invoice balance",
            "payment": {
                "person": "Anna Camacho", 
                "amount": 505.00,
                "ref": "132510794",
                "property": "Barcelona - Rent (Non-Integrated)"
            },
            "expected_invoice": "INV-001"
        },
        "no_matching_invoice": {
            "description": "No invoice found for tenant",
            "payment": {
                "person": "John Doe",
                "amount": 1000.00,
                "ref": "999999999",
                "property": "Test Property - Rent (Non-Integrated)"
            },
            "expected_invoice": None
        },
        "multiple_invoices": {
            "description": "Multiple invoices for same tenant",
            "payment": {
                "person": "Anna Camacho",
                "amount": 500.00,
                "ref": "132510795",
                "property": "Barcelona - Rent (Non-Integrated)"
            },
            "expected_invoice": "INV-001"  # Should match oldest unpaid invoice
        }
    }
    
    return scenarios

def save_test_data():
    """Save all test data to files"""
    
    # Create test data directories
    test_data_dir = os.path.join(project_root, "ai_agent", "data", "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    
    # Create email test data
    email_data = create_test_email_data()
    with open(os.path.join(test_data_dir, "sample_emails.json"), 'w') as f:
        json.dump(email_data, f, indent=2)
    
    # Create Xero test data
    xero_data = create_mock_xero_data()
    with open(os.path.join(test_data_dir, "mock_xero_data.json"), 'w') as f:
        json.dump(xero_data, f, indent=2)
    
    # Create test scenarios
    scenarios = create_test_scenarios()
    with open(os.path.join(test_data_dir, "test_scenarios.json"), 'w') as f:
        json.dump(scenarios, f, indent=2)
    
    # Create a test configuration file
    test_config = {
        "created_date": datetime.now().isoformat(),
        "description": "Test data for AI agent development and debugging",
        "files": {
            "sample_emails": "sample_emails.json",
            "mock_xero_data": "mock_xero_data.json", 
            "test_scenarios": "test_scenarios.json"
        },
        "usage": {
            "sample_emails": "Use for testing email parsing without Gmail access",
            "mock_xero_data": "Use for testing Xero operations without API access",
            "test_scenarios": "Use for testing payment matching logic"
        }
    }
    
    with open(os.path.join(test_data_dir, "test_config.json"), 'w') as f:
        json.dump(test_config, f, indent=2)
    
    print(f"Test data created in: {test_data_dir}")
    print("Files created:")
    print("  - sample_emails.json: Sample email content for parsing tests")
    print("  - mock_xero_data.json: Mock Xero invoices and payments")
    print("  - test_scenarios.json: Various test scenarios for edge cases")
    print("  - test_config.json: Configuration and usage information")

if __name__ == "__main__":
    save_test_data()
