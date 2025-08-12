"""
Create sample jobs for testing the web dashboard
"""

import os
import sys
import json
from datetime import datetime, timedelta
import random

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def create_sample_jobs():
    """Create sample jobs for dashboard testing"""
    
    sample_jobs = [
        {
            "job_id": "job_1734567890_1",
            "job_type": "payment_matching",
            "data": {
                "payment": {
                    "person": "Anna Camacho",
                    "amount": 1705.00,
                    "ref": "132510794",
                    "property": "Barcelona - Rent (Non-Integrated)"
                },
                "available_invoices": [
                    {"InvoiceID": "INV-001", "AmountDue": 1705.00, "ContactName": "Anna Camacho"},
                    {"InvoiceID": "INV-002", "AmountDue": 1200.00, "ContactName": "Anna Camacho"}
                ]
            },
            "confidence": 0.75,
            "reasoning": "Multiple invoices found for Anna Camacho. Payment amount ($1705) matches Invoice INV-001 exactly, but there's also a partial match with INV-002. Need human decision on which invoice to apply payment to.",
            "recommendations": [
                "Apply to INV-001 (exact amount match)",
                "Split payment between invoices",
                "Check tenant's payment history"
            ],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "chat_messages": [
                {
                    "id": 1,
                    "sender": "AI Agent",
                    "message": "I found multiple invoices for Anna Camacho. The payment amount exactly matches INV-001, but there's also a partial match with INV-002. Which invoice should I apply this payment to?",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        },
        {
            "job_id": "job_1734567890_2",
            "job_type": "name_matching",
            "data": {
                "payment_name": "Bill Smith",
                "available_tenants": ["William Smith", "Robert Johnson", "Michael Brown"],
                "property_name": "Camels Back",
                "payment_amount": 1385.00
            },
            "confidence": 0.65,
            "reasoning": "Payment name 'Bill Smith' could be a nickname for 'William Smith'. Confidence is moderate due to nickname matching. Need human verification.",
            "recommendations": [
                "Confirm if Bill Smith is William Smith",
                "Check tenant records for nickname information",
                "Contact tenant for verification"
            ],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "chat_messages": [
                {
                    "id": 1,
                    "sender": "AI Agent",
                    "message": "I found a potential nickname match: 'Bill Smith' could be 'William Smith'. Should I proceed with this match?",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        },
        {
            "job_id": "job_1734567890_3",
            "job_type": "overpayment",
            "data": {
                "payment": {
                    "person": "Erica Chown 2",
                    "amount": 2500.00,
                    "ref": "132487740",
                    "property": "Camels Back - Rent (Non-Integrated)"
                },
                "total_invoice_balance": 1510.00
            },
            "confidence": 0.80,
            "reasoning": "Payment amount ($2500) exceeds total invoice balance ($1510) by $990. This could be a security deposit or advance payment. Need human decision on how to handle overpayment.",
            "recommendations": [
                "Apply $1510 to current invoice, create $990 credit",
                "Create separate security deposit invoice",
                "Contact tenant to clarify payment intent"
            ],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "chat_messages": [
                {
                    "id": 1,
                    "sender": "AI Agent",
                    "message": "Payment amount exceeds invoice balance by $990. Should I create a credit for the overpayment amount?",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        },
        {
            "job_id": "job_1734567890_4",
            "job_type": "no_match",
            "data": {
                "payment": {
                    "person": "John Doe",
                    "amount": 1000.00,
                    "ref": "999999999",
                    "property": "Test Property - Rent (Non-Integrated)"
                },
                "search_results": []
            },
            "confidence": 0.10,
            "reasoning": "No invoices found for tenant 'John Doe'. This could be a new tenant, incorrect name, or missing invoice data.",
            "recommendations": [
                "Verify tenant name spelling",
                "Check if this is a new tenant",
                "Create new invoice for this tenant",
                "Flag for manual investigation"
            ],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "chat_messages": [
                {
                    "id": 1,
                    "sender": "AI Agent",
                    "message": "No invoices found for John Doe. Should I create a new invoice or investigate further?",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        },
        {
            "job_id": "job_1734567890_5",
            "job_type": "duplicate_payment",
            "data": {
                "payment": {
                    "person": "Thais Holladay",
                    "amount": 1385.00,
                    "ref": "132487744",
                    "property": "Camels Back - Rent (Non-Integrated)"
                },
                "existing_payment": {
                    "payment_id": "PAY-001",
                    "date": "2025-07-20",
                    "amount": 1385.00,
                    "reference": "132487744"
                }
            },
            "confidence": 0.95,
            "reasoning": "Payment reference 132487744 already exists in the system with the same amount. This appears to be a duplicate payment.",
            "recommendations": [
                "Skip this payment (duplicate)",
                "Verify if this is a legitimate duplicate",
                "Check payment processing status"
            ],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "chat_messages": [
                {
                    "id": 1,
                    "sender": "AI Agent",
                    "message": "This payment appears to be a duplicate. Should I skip it or investigate further?",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
    ]
    
    return sample_jobs

def save_sample_jobs():
    """Save sample jobs to a file for testing"""
    
    jobs = create_sample_jobs()
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(project_root, "ai_agent", "data", "sample_data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Save jobs to file
    jobs_file = os.path.join(data_dir, "sample_jobs.json")
    with open(jobs_file, 'w') as f:
        json.dump(jobs, f, indent=2, default=str)
    
    print(f"✅ Sample jobs created and saved to: {jobs_file}")
    print(f"📊 Created {len(jobs)} sample jobs:")
    
    for i, job in enumerate(jobs, 1):
        print(f"  {i}. {job['job_type']} - {job['data'].get('payment', {}).get('person', 'Unknown')} - {job['confidence']:.0%} confidence")
    
    return jobs_file

if __name__ == "__main__":
    save_sample_jobs()

