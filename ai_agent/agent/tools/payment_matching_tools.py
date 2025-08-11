"""
Payment Matching Tools for AI Agent
Combines algorithmic matching with AI reasoning for edge cases
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from difflib import SequenceMatcher

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class PaymentMatchInput(BaseModel):
    """Input schema for payment matching"""
    payment: Dict[str, Any] = Field(description="Payment data from parsed email")
    tenant_name: str = Field(description="Name of the tenant making the payment")
    amount: float = Field(description="Payment amount")
    payment_date: str = Field(description="Payment date")
    reference: str = Field(description="Payment reference number")
    property_name: str = Field(description="Property name")

class PaymentMatchResult(BaseModel):
    """Result of payment matching"""
    success: bool
    matched_invoice_id: Optional[str] = None
    confidence_score: float = 0.0
    match_type: str = "none"  # exact, fuzzy, ai_reasoned, multiple, overpayment
    reasoning: str = ""
    warnings: List[str] = []
    recommendations: List[str] = []

class PaymentMatchingTool(BaseTool):
    """Tool for matching payments to invoices using hybrid approach"""
    
    name: str = "match_payment_to_invoice"
    description: str = """
    Match a payment to the appropriate invoice using algorithmic and AI reasoning.
    
    This tool:
    1. Searches local database for matching invoices
    2. Uses algorithmic matching for straightforward cases
    3. Uses AI reasoning for complex edge cases
    4. Handles multiple invoices, roommates, overpayments
    5. Returns detailed reasoning and confidence scores
    
    Use this tool when you need to determine which invoice a payment should be applied to.
    """
    args_schema: type[PaymentMatchInput] = PaymentMatchInput
    
    def __init__(self):
        super().__init__()
        # Set paths after initialization
        self._db_path = os.path.join(project_root, "Payments", "payments.db")
        self._test_data_path = os.path.join(project_root, "ai_agent", "data", "test_data", "mock_xero_data.json")
    
    @property
    def db_path(self):
        return self._db_path
    
    @property
    def test_data_path(self):
        return self._test_data_path
    
    def _run(self, payment: Dict[str, Any], tenant_name: str, amount: float, 
             payment_date: str, reference: str, property_name: str) -> Dict[str, Any]:
        """
        Match payment to invoice using hybrid approach
        
        Args:
            payment: Payment data from parsed email
            tenant_name: Name of the tenant
            amount: Payment amount
            payment_date: Payment date
            reference: Payment reference
            property_name: Property name
            
        Returns:
            Dictionary with matching results and reasoning
        """
        logger.info(f"Matching payment ${amount} for {tenant_name} at {property_name}")
        
        try:
            # Step 1: Get available invoices from database
            invoices = self._get_tenant_invoices(tenant_name)
            
            if not invoices:
                return self._create_no_match_result(
                    f"No invoices found for tenant: {tenant_name}",
                    recommendations=["Verify tenant name", "Check if invoice exists in Xero"]
                )
            
            # Step 2: Algorithmic matching
            algorithmic_result = self._algorithmic_matching(invoices, amount, tenant_name, payment_date)
            
            # Step 3: Handle different match scenarios
            if algorithmic_result["match_type"] == "exact":
                return algorithmic_result
            elif algorithmic_result["match_type"] == "multiple":
                return self._handle_multiple_invoices(algorithmic_result, payment, tenant_name, amount)
            elif algorithmic_result["match_type"] == "overpayment":
                return self._handle_overpayment(algorithmic_result, payment, tenant_name, amount)
            elif algorithmic_result["match_type"] == "fuzzy":
                return self._validate_fuzzy_match(algorithmic_result, payment, tenant_name, amount)
            else:
                return self._create_no_match_result(
                    "No algorithmic match found",
                    recommendations=["Use AI reasoning", "Flag for human review"]
                )
                
        except Exception as e:
            logger.error(f"Error in payment matching: {str(e)}")
            return self._create_no_match_result(
                f"Error during matching: {str(e)}",
                recommendations=["Check system logs", "Flag for human review"]
            )
    
    def _get_tenant_invoices(self, tenant_name: str) -> List[Dict[str, Any]]:
        """Get invoices for tenant from database or mock data"""
        
        # Try to use real database first
        try:
            if os.path.exists(self.db_path):
                return self._query_database(tenant_name)
        except Exception as e:
            logger.warning(f"Database query failed: {e}")
        
        # Fall back to mock data
        return self._get_mock_invoices(tenant_name)
    
    def _query_database(self, tenant_name: str) -> List[Dict[str, Any]]:
        """Query local database for tenant invoices"""
        # TODO: Implement actual database query using your existing Payments.payments_db
        # For now, return empty list to trigger mock data fallback
        return []
    
    def _get_mock_invoices(self, tenant_name: str) -> List[Dict[str, Any]]:
        """Get mock invoices for testing"""
        if os.path.exists(self.test_data_path):
            with open(self.test_data_path, 'r') as f:
                mock_data = json.load(f)
            
            return [
                inv for inv in mock_data['invoices']
                if inv.get('ContactName', '').lower() == tenant_name.lower()
            ]
        return []
    
    def _algorithmic_matching(self, invoices: List[Dict[str, Any]], amount: float, 
                            tenant_name: str, payment_date: str) -> Dict[str, Any]:
        """Perform algorithmic matching"""
        
        # Sort invoices by date (oldest first)
        sorted_invoices = sorted(invoices, key=lambda x: x.get('Date', ''))
        
        # Find exact amount matches
        exact_matches = [
            inv for inv in sorted_invoices
            if abs(inv.get('AmountDue', 0) - amount) < 0.01
        ]
        
        if len(exact_matches) == 1:
            return self._create_match_result(
                exact_matches[0],
                confidence_score=1.0,
                match_type="exact",
                reasoning=f"Exact amount match: ${amount} = ${exact_matches[0].get('AmountDue')}"
            )
        elif len(exact_matches) > 1:
            return self._create_match_result(
                exact_matches[0],  # Take oldest
                confidence_score=0.8,
                match_type="multiple",
                reasoning=f"Multiple exact matches found, using oldest invoice",
                warnings=[f"Found {len(exact_matches)} invoices with exact amount match"]
            )
        
        # Find partial matches (payment less than or equal to invoice balance)
        partial_matches = [
            inv for inv in sorted_invoices
            if inv.get('AmountDue', 0) >= amount
        ]
        
        if len(partial_matches) == 1:
            return self._create_match_result(
                partial_matches[0],
                confidence_score=0.9,
                match_type="partial",
                reasoning=f"Single partial match: payment ${amount} <= invoice balance ${partial_matches[0].get('AmountDue')}"
            )
        elif len(partial_matches) > 1:
            return self._create_match_result(
                partial_matches[0],  # Take oldest
                confidence_score=0.7,
                match_type="multiple",
                reasoning=f"Multiple partial matches, using oldest invoice",
                warnings=[f"Found {len(partial_matches)} invoices that could accept this payment"]
            )
        
        # Check for overpayment (payment exceeds all invoice balances)
        total_balance = sum(inv.get('AmountDue', 0) for inv in sorted_invoices)
        if amount > total_balance:
            return self._create_match_result(
                sorted_invoices[0] if sorted_invoices else None,
                confidence_score=0.6,
                match_type="overpayment",
                reasoning=f"Overpayment detected: payment ${amount} > total balance ${total_balance}",
                warnings=["Payment exceeds total invoice balance", "Overpayment credit may be needed"]
            )
        
        # No algorithmic match found
        return self._create_no_match_result(
            "No algorithmic match found",
            recommendations=["Use AI reasoning", "Check for data inconsistencies"]
        )
    
    def _handle_multiple_invoices(self, result: Dict[str, Any], payment: Dict[str, Any], 
                                 tenant_name: str, amount: float) -> Dict[str, Any]:
        """Handle multiple invoice matches using AI reasoning"""
        
        # This is where AI would analyze the context and make a decision
        # For now, we'll use simple heuristics
        
        reasoning = f"Multiple invoices found for {tenant_name}. "
        
        # Check if payment reference contains date/month info
        if any(month in payment.get('reference', '').lower() for month in 
               ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
            reasoning += "Payment reference suggests specific month, but exact match needed. "
            result["recommendations"].append("Use AI to analyze payment reference for month specificity")
        
        # Check for roommate scenarios
        if len(result.get("warnings", [])) > 1:
            reasoning += "Possible roommate scenario detected. "
            result["recommendations"].append("Use AI to determine if this is a roommate payment")
        
        result["reasoning"] = reasoning
        result["recommendations"].append("Flag for AI reasoning or human review")
        
        return result
    
    def _handle_overpayment(self, result: Dict[str, Any], payment: Dict[str, Any], 
                           tenant_name: str, amount: float) -> Dict[str, Any]:
        """Handle overpayment scenarios"""
        
        reasoning = f"Overpayment detected for {tenant_name}. "
        
        # Check if this is a common overpayment amount (e.g., security deposit)
        if amount in [500, 1000, 1500, 2000]:  # Common deposit amounts
            reasoning += "Payment amount suggests security deposit. "
            result["recommendations"].append("Create separate deposit invoice/credit")
        else:
            reasoning += "Unusual overpayment amount. "
            result["recommendations"].append("Verify payment intent with tenant")
        
        result["reasoning"] = reasoning
        result["recommendations"].append("Create overpayment credit in Xero")
        
        return result
    
    def _validate_fuzzy_match(self, result: Dict[str, Any], payment: Dict[str, Any], 
                             tenant_name: str, amount: float) -> Dict[str, Any]:
        """Validate fuzzy matches with additional checks"""
        
        reasoning = f"Fuzzy match found for {tenant_name}. "
        
        # Add additional validation logic here
        # For now, recommend AI review
        result["recommendations"].append("Use AI to validate fuzzy match")
        result["reasoning"] = reasoning
        
        return result
    
    def _create_match_result(self, invoice: Optional[Dict[str, Any]], confidence_score: float, 
                           match_type: str, reasoning: str, warnings: List[str] = None) -> Dict[str, Any]:
        """Create a match result"""
        return {
            "success": True,
            "matched_invoice_id": invoice.get('InvoiceID') if invoice else None,
            "confidence_score": confidence_score,
            "match_type": match_type,
            "reasoning": reasoning,
            "warnings": warnings or [],
            "recommendations": [],
            "invoice_details": invoice,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_no_match_result(self, reasoning: str, recommendations: List[str] = None) -> Dict[str, Any]:
        """Create a no-match result"""
        return {
            "success": False,
            "matched_invoice_id": None,
            "confidence_score": 0.0,
            "match_type": "none",
            "reasoning": reasoning,
            "warnings": [],
            "recommendations": recommendations or [],
            "timestamp": datetime.now().isoformat()
        }
