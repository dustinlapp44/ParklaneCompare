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
        self._db_path = "/tmp/payments.db"  # Use the same path as payments_db.py
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
        Match payment to invoice using hybrid approach with AI reasoning
        
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
            # Step 0: Check detailed payment status
            payment_status = self._check_payment_status(reference, tenant_name)
            
            # If payment already exists, skip it
            if payment_status['payment_exists']:
                return self._create_duplicate_result(
                    f"Payment reference {reference} already applied to an invoice - skipping",
                    recommendations=["Payment already applied", "No action needed"]
                )
            
            # Step 1: Get available invoices from database
            invoices = self._get_tenant_invoices(tenant_name)
            
            # Determine the scenario based on payment status
            if not payment_status['invoice_exists']:
                # No invoices exist for this tenant
                return self._create_no_match_result(
                    f"No invoices found for tenant: {tenant_name}. Payment may be for a future invoice.",
                    recommendations=[
                        "Flag for human review - invoice may need to be created in Xero",
                        "This is normal business flow - payments can arrive before invoices",
                        "Future: Agent could create invoice automatically"
                    ]
                )
            elif payment_status['all_invoices_paid']:
                # All existing invoices are paid, but this payment reference is new
                return self._create_no_match_result(
                    f"All existing invoices for {tenant_name} are paid, but payment reference {reference} is new.",
                    recommendations=[
                        "Payment may be for a future invoice (not yet created)",
                        "Payment may be a prepayment for next month",
                        "Flag for human review - may need to create new invoice",
                        "Future: Agent could create invoice automatically"
                    ]
                )
            
            # Step 2: Algorithmic matching
            algorithmic_result = self._algorithmic_matching(invoices, amount, tenant_name, payment_date)
            
            # Step 3: Apply confidence-based logic with AI reasoning
            confidence = algorithmic_result.get("confidence_score", 0.0)
            
            if confidence >= 0.9:
                # High confidence - create job with high confidence for human approval
                logger.info(f"High confidence match ({confidence:.2f}) - creating job for human approval")
                return algorithmic_result
            elif confidence >= 0.7:
                # Medium confidence - use AI reasoning to improve job quality
                logger.info(f"Medium confidence match ({confidence:.2f}) - using AI reasoning to improve job quality")
                return self._apply_ai_reasoning(algorithmic_result, payment, tenant_name, amount, invoices)
            else:
                # Low confidence - use AI reasoning to provide better insights for human review
                logger.info(f"Low confidence match ({confidence:.2f}) - using AI reasoning for better insights")
                return self._apply_ai_reasoning(algorithmic_result, payment, tenant_name, amount, invoices)
                
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
        try:
            from Payments.payments_db import get_invoices_by_contact
            
            # Normalize tenant name by removing extra spaces
            normalized_tenant_name = " ".join(tenant_name.split())
            
            # Get invoices from local database
            invoices = get_invoices_by_contact(normalized_tenant_name)
            
            # Convert to expected format
            formatted_invoices = []
            for inv in invoices:
                formatted_invoices.append({
                    'InvoiceID': inv['invoice_id'],
                    'ContactName': inv['contact_name'],
                    'AmountDue': inv['amount_due'],
                    'Date': inv['issue_date'],
                    'Status': inv['status'],
                    'Reference': inv['reference']
                })
            
            return formatted_invoices
            
        except Exception as e:
            logger.warning(f"Database query failed: {e}")
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
    
    def _apply_ai_reasoning(self, algorithmic_result: Dict[str, Any], payment: Dict[str, Any], 
                           tenant_name: str, amount: float, invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply AI reasoning to improve job quality and provide better insights for human review.
        Does NOT auto-apply payments - only improves reasoning and confidence.
        """
        try:
            # Import AI reasoning tool
            from .ai_reasoning_tools import AIReasoningTool
            
            ai_tool = AIReasoningTool()
            
            # Determine scenario type based on algorithmic result
            scenario_type = self._determine_scenario_type(algorithmic_result, payment, invoices)
            
            # Prepare context for AI reasoning
            context = {
                'payment_amount': amount,
                'payment_date': payment.get('date', ''),
                'payment_reference': payment.get('ref', ''),
                'property_name': payment.get('property', ''),
                'algorithmic_confidence': algorithmic_result.get('confidence_score', 0.0),
                'algorithmic_reasoning': algorithmic_result.get('reasoning', ''),
                'match_type': algorithmic_result.get('match_type', '')
            }
            
            # Use AI reasoning to improve the result
            ai_result = ai_tool._run(
                scenario_type=scenario_type,
                payment_data=payment,
                available_invoices=invoices,
                tenant_matches=[{'name': tenant_name, 'confidence': 1.0}],
                context=context
            )
            
            if ai_result.get('success', False):
                # AI reasoning succeeded - enhance the result
                enhanced_result = algorithmic_result.copy()
                
                # Improve reasoning with AI insights
                ai_reasoning = ai_result.get('reasoning', '')
                enhanced_result['reasoning'] = f"{algorithmic_result.get('reasoning', '')} AI Analysis: {ai_reasoning}"
                
                # Adjust confidence based on AI analysis
                ai_confidence = ai_result.get('confidence_score', 0.0)
                original_confidence = algorithmic_result.get('confidence_score', 0.0)
                
                # Use AI confidence if it's higher, otherwise keep original
                if ai_confidence > original_confidence:
                    enhanced_result['confidence_score'] = ai_confidence
                    enhanced_result['reasoning'] += f" (AI confidence: {ai_confidence:.2f})"
                
                # Add AI recommendations
                ai_recommendations = ai_result.get('recommendations', [])
                enhanced_result['recommendations'].extend(ai_recommendations)
                
                # Add AI insights to warnings
                ai_insights = ai_result.get('insights', [])
                if ai_insights:
                    enhanced_result['warnings'] = enhanced_result.get('warnings', []) + ai_insights
                
                logger.info(f"AI reasoning applied successfully - confidence: {enhanced_result['confidence_score']:.2f}")
                return enhanced_result
            else:
                # AI reasoning failed - return original result with note
                algorithmic_result['reasoning'] += " (AI reasoning unavailable - using algorithmic result)"
                algorithmic_result['recommendations'].append("AI reasoning failed - human review recommended")
                logger.warning(f"AI reasoning failed: {ai_result.get('error', 'Unknown error')}")
                return algorithmic_result
                
        except Exception as e:
            logger.error(f"Error applying AI reasoning: {e}")
            # Return original result with error note
            algorithmic_result['reasoning'] += " (AI reasoning error - using algorithmic result)"
            algorithmic_result['recommendations'].append("AI reasoning error - human review recommended")
            return algorithmic_result
    
    def _determine_scenario_type(self, algorithmic_result: Dict[str, Any], payment: Dict[str, Any], 
                                invoices: List[Dict[str, Any]]) -> str:
        """Determine the scenario type for AI reasoning"""
        match_type = algorithmic_result.get('match_type', '')
        
        if match_type == 'multiple':
            return 'multiple_invoices'
        elif match_type == 'overpayment':
            return 'overpayment'
        elif match_type == 'fuzzy':
            return 'name_ambiguity'
        elif match_type == 'partial':
            return 'partial_match'
        else:
            return 'general_scenario'
    
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
    
    def _is_duplicate_payment(self, reference: str, amount: float, tenant_name: str) -> bool:
        """Check if payment reference is already linked to an invoice"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for exact match first
            cursor.execute('''
                SELECT COUNT(*) FROM payments 
                WHERE reference = ?
            ''', (reference,))
            
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"Payment reference {reference} already exists in payments table - skipping")
                conn.close()
                return True
            
            # Check for "Aptexx" prefixed version (email parsing vs Xero storage format)
            aptexx_reference = f"Aptexx {reference}"
            cursor.execute('''
                SELECT COUNT(*) FROM payments 
                WHERE reference = ?
            ''', (aptexx_reference,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            if count > 0:
                logger.info(f"Payment reference {aptexx_reference} already exists in payments table - skipping")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking duplicate payment: {e}")
            return False
    
    def _check_payment_status(self, reference: str, tenant_name: str) -> Dict[str, Any]:
        """Check detailed payment status for better decision making"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            result = {
                'payment_exists': False,
                'invoice_exists': False,
                'all_invoices_paid': False,
                'unpaid_invoices': 0,
                'total_invoices': 0
            }
            
            # Check if payment reference already exists (both formats)
            cursor.execute('''
                SELECT COUNT(*) FROM payments 
                WHERE reference = ? OR reference = ?
            ''', (reference, f"Aptexx {reference}"))
            
            result['payment_exists'] = cursor.fetchone()[0] > 0
            
            # Normalize tenant name by removing extra spaces
            normalized_tenant_name = " ".join(tenant_name.split())
            
            # Check tenant invoices
            cursor.execute('''
                SELECT COUNT(*), 
                       SUM(CASE WHEN amount_due > 0 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END)
                FROM invoices 
                WHERE contact_name LIKE ?
            ''', (f'%{normalized_tenant_name}%',))
            
            row = cursor.fetchone()
            result['total_invoices'] = row[0] or 0
            result['unpaid_invoices'] = row[1] or 0
            result['all_invoices_paid'] = (row[2] or 0) == result['total_invoices']
            result['invoice_exists'] = result['total_invoices'] > 0
            
            conn.close()
            return result
            
        except Exception as e:
            logger.warning(f"Error checking payment status: {e}")
            return {
                'payment_exists': False,
                'invoice_exists': False,
                'all_invoices_paid': False,
                'unpaid_invoices': 0,
                'total_invoices': 0
            }
    
    def _create_duplicate_result(self, reasoning: str, recommendations: List[str] = None) -> Dict[str, Any]:
        """Create a duplicate payment result"""
        return {
            "success": False,
            "matched_invoice_id": None,
            "confidence_score": 0.0,
            "match_type": "duplicate",
            "reasoning": reasoning,
            "warnings": ["Duplicate payment detected"],
            "recommendations": recommendations or [],
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
