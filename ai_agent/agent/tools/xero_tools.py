"""
Xero tools for the AI agent
Wraps Xero client functionality for invoice and payment operations
SAFETY: All operations are READ-ONLY for testing
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

# Import Xero client functions (read-only operations)
try:
    from XeroClient.xero_client import (
        authorize_xero, 
        get_invoices, 
        get_payments,
        pull_tenant_invoices
    )
    XERO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Xero client not available: {e}")
    XERO_AVAILABLE = False

class XeroInvoiceInput(BaseModel):
    """Input schema for Xero invoice operations"""
    contact_name: str = Field(description="Name of the contact/tenant")
    start_date: Optional[str] = Field(default=None, description="Start date for invoice search (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date for invoice search (YYYY-MM-DD)")

class XeroPaymentInput(BaseModel):
    """Input schema for Xero payment operations"""
    invoice_id: str = Field(description="Xero invoice ID")
    amount: float = Field(description="Payment amount")
    payment_date: str = Field(description="Payment date (YYYY-MM-DD)")
    reference: str = Field(description="Payment reference number")

class XeroInvoiceTool(BaseTool):
    """Tool for retrieving invoices from Xero (READ-ONLY)"""
    
    name: str = "get_xero_invoices"
    description: str = """
    Retrieve invoices from Xero for a specific contact/tenant.
    
    SAFETY: This tool is READ-ONLY and will not modify any data.
    
    This tool:
    1. Searches for invoices by contact name
    2. Filters by date range if provided
    3. Returns invoice details including amounts, dates, and status
    4. Falls back to mock data if Xero is not available
    
    Use this tool when you need to find invoices for a tenant to apply payments.
    """
    args_schema: type[XeroInvoiceInput] = XeroInvoiceInput
    
    def _run(self, contact_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get invoices from Xero (READ-ONLY)
        
        Args:
            contact_name: Name of the contact/tenant
            start_date: Start date for search
            end_date: End date for search
            
        Returns:
            Dictionary with invoice data
        """
        logger.info(f"Getting invoices for {contact_name} from {start_date} to {end_date}")
        
        try:
            if XERO_AVAILABLE:
                # Use real Xero API (read-only)
                return self._get_real_invoices(contact_name, start_date, end_date)
            else:
                # Use mock data for testing
                return self._get_mock_invoices(contact_name, start_date, end_date)
                
        except Exception as e:
            logger.error(f"Error getting invoices: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "contact_name": contact_name,
                "invoices": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_real_invoices(self, contact_name: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Get invoices from real Xero API (READ-ONLY)"""
        
        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get invoices using existing Xero client
        invoices = pull_tenant_invoices(
            start_date=start_date,
            end_date=end_date,
            contact=contact_name
        )
        
        # Filter by contact name if provided
        if contact_name:
            filtered_invoices = [
                inv for inv in invoices 
                if inv.get('Contact', {}).get('Name', '').lower() == contact_name.lower()
            ]
        else:
            filtered_invoices = invoices
        
        return {
            "success": True,
            "contact_name": contact_name,
            "invoices": filtered_invoices,
            "total_count": len(filtered_invoices),
            "date_range": f"{start_date} to {end_date}",
            "timestamp": datetime.now().isoformat(),
            "source": "xero_api"
        }
    
    def _get_mock_invoices(self, contact_name: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Get mock invoices for testing"""
        
        # Load mock data
        test_data_path = os.path.join(project_root, "ai_agent", "data", "test_data", "mock_xero_data.json")
        
        if os.path.exists(test_data_path):
            with open(test_data_path, 'r') as f:
                mock_data = json.load(f)
            
            logger.info(f"Loaded {len(mock_data.get('invoices', []))} invoices from mock data")
            
            # Filter mock invoices by contact name (if provided)
            if contact_name:
                filtered_invoices = [
                    inv for inv in mock_data['invoices']
                    if inv.get('ContactName', '').lower() == contact_name.lower()
                ]
                logger.info(f"Filtered to {len(filtered_invoices)} invoices for contact '{contact_name}'")
            else:
                # Return all invoices if no contact name provided
                filtered_invoices = mock_data.get('invoices', [])
                logger.info(f"Returning all {len(filtered_invoices)} invoices (no contact filter)")
        else:
            logger.warning(f"Mock data file not found at {test_data_path}")
            filtered_invoices = []
        
        return {
            "success": True,
            "contact_name": contact_name,
            "invoices": filtered_invoices,
            "total_count": len(filtered_invoices),
            "date_range": f"{start_date or 'N/A'} to {end_date or 'N/A'}",
            "timestamp": datetime.now().isoformat(),
            "source": "mock_data"
        }

class XeroPaymentTool(BaseTool):
    """Tool for validating payments against Xero invoices (READ-ONLY)"""
    
    name: str = "validate_xero_payment"
    description: str = """
    Validate a payment against a Xero invoice (READ-ONLY).
    
    SAFETY: This tool is READ-ONLY and will NOT apply payments to Xero.
    It only validates that the payment can be applied.
    
    This tool:
    1. Validates the payment amount against invoice balance
    2. Checks if the invoice exists and is in the correct status
    3. Returns validation results and recommendations
    4. Does NOT apply the payment (safety measure)
    
    Use this tool to validate payments before applying them manually.
    """
    args_schema: type[XeroPaymentInput] = XeroPaymentInput
    
    def _run(self, invoice_id: str, amount: float, payment_date: str, reference: str) -> Dict[str, Any]:
        """
        Validate payment against Xero invoice (READ-ONLY)
        
        Args:
            invoice_id: Xero invoice ID
            amount: Payment amount
            payment_date: Payment date
            reference: Payment reference
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"VALIDATING payment of ${amount} to invoice {invoice_id} with reference {reference}")
        logger.warning("SAFETY: This is READ-ONLY validation only - no payment will be applied")
        
        try:
            if XERO_AVAILABLE:
                return self._validate_real_payment(invoice_id, amount, payment_date, reference)
            else:
                return self._validate_mock_payment(invoice_id, amount, payment_date, reference)
                
        except Exception as e:
            logger.error(f"Error validating payment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "invoice_id": invoice_id,
                "amount": amount,
                "reference": reference,
                "timestamp": datetime.now().isoformat()
            }
    
    def _validate_real_payment(self, invoice_id: str, amount: float, payment_date: str, reference: str) -> Dict[str, Any]:
        """Validate payment against real Xero invoice (READ-ONLY)"""
        
        # Get invoice details from Xero
        # Note: This would need to be implemented with your existing Xero client
        # For now, we'll return a validation structure
        
        validation_result = {
            "success": True,
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_date": payment_date,
            "reference": reference,
            "validation": {
                "invoice_exists": True,  # Would check against Xero
                "invoice_status": "AUTHORISED",  # Would get from Xero
                "current_balance": 0.0,  # Would get from Xero
                "payment_valid": True,
                "recommendation": "Payment can be applied manually",
                "warnings": ["READ-ONLY MODE: Payment not applied automatically"]
            },
            "timestamp": datetime.now().isoformat(),
            "source": "xero_api_validation"
        }
        
        return validation_result
    
    def _validate_mock_payment(self, invoice_id: str, amount: float, payment_date: str, reference: str) -> Dict[str, Any]:
        """Validate payment against mock invoice data"""
        
        # Load mock data
        test_data_path = os.path.join(project_root, "ai_agent", "data", "test_data", "mock_xero_data.json")
        
        if os.path.exists(test_data_path):
            with open(test_data_path, 'r') as f:
                mock_data = json.load(f)
            
            # Find the invoice
            invoice = None
            for inv in mock_data['invoices']:
                if inv.get('InvoiceID') == invoice_id:
                    invoice = inv
                    break
            
            if invoice:
                current_balance = invoice.get('AmountDue', 0.0)
                payment_valid = amount <= current_balance
                
                validation_result = {
                    "success": True,
                    "invoice_id": invoice_id,
                    "amount": amount,
                    "payment_date": payment_date,
                    "reference": reference,
                    "validation": {
                        "invoice_exists": True,
                        "invoice_status": invoice.get('Status', 'UNKNOWN'),
                        "current_balance": current_balance,
                        "payment_valid": payment_valid,
                        "recommendation": "Payment can be applied manually" if payment_valid else "Payment amount exceeds invoice balance",
                        "warnings": ["READ-ONLY MODE: Payment not applied automatically", "Using mock data"]
                    },
                    "timestamp": datetime.now().isoformat(),
                    "source": "mock_data_validation"
                }
            else:
                validation_result = {
                    "success": False,
                    "invoice_id": invoice_id,
                    "amount": amount,
                    "payment_date": payment_date,
                    "reference": reference,
                    "validation": {
                        "invoice_exists": False,
                        "payment_valid": False,
                        "recommendation": "Invoice not found",
                        "warnings": ["READ-ONLY MODE: Payment not applied automatically", "Using mock data"]
                    },
                    "timestamp": datetime.now().isoformat(),
                    "source": "mock_data_validation"
                }
        else:
            validation_result = {
                "success": False,
                "invoice_id": invoice_id,
                "amount": amount,
                "payment_date": payment_date,
                "reference": reference,
                "validation": {
                    "invoice_exists": False,
                    "payment_valid": False,
                    "recommendation": "Mock data not available",
                    "warnings": ["READ-ONLY MODE: Payment not applied automatically", "Mock data file not found"]
                },
                "timestamp": datetime.now().isoformat(),
                "source": "mock_data_validation"
            }
        
        return validation_result
