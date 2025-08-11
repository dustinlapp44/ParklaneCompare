"""
AI Reasoning Tools for Complex Payment Scenarios
Handles edge cases that require human-like analysis
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class AIReasoningInput(BaseModel):
    """Input schema for AI reasoning"""
    scenario_type: str = Field(description="Type of scenario (multiple_invoices, name_ambiguity, overpayment, etc.)")
    payment_data: Dict[str, Any] = Field(description="Payment data from parsed email")
    available_invoices: List[Dict[str, Any]] = Field(description="Available invoices for matching")
    tenant_matches: List[Dict[str, Any]] = Field(description="Possible tenant matches")
    context: Dict[str, Any] = Field(description="Additional context for reasoning")

class AIReasoningTool(BaseTool):
    """Tool for AI reasoning on complex payment scenarios"""
    
    name: str = "ai_reasoning"
    description: str = """
    Use AI reasoning to analyze complex payment matching scenarios.
    
    This tool handles:
    1. Multiple invoice scenarios (which invoice to apply payment to)
    2. Name ambiguity (fuzzy name matches)
    3. Overpayment analysis (intent and handling)
    4. Roommate payment scenarios
    5. Unusual payment patterns
    
    Use this tool when algorithmic matching produces low confidence or multiple options.
    """
    args_schema: type[AIReasoningInput] = AIReasoningInput
    
    def _run(self, scenario_type: str, payment_data: Dict[str, Any], 
             available_invoices: List[Dict[str, Any]], tenant_matches: List[Dict[str, Any]],
             context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform AI reasoning on complex payment scenario
        
        Args:
            scenario_type: Type of scenario to analyze
            payment_data: Payment data from parsed email
            available_invoices: Available invoices for matching
            tenant_matches: Possible tenant matches
            context: Additional context
            
        Returns:
            Dictionary with AI reasoning results
        """
        logger.info(f"Performing AI reasoning for scenario: {scenario_type}")
        
        try:
            if scenario_type == "multiple_invoices":
                return self._reason_multiple_invoices(payment_data, available_invoices, context)
            elif scenario_type == "name_ambiguity":
                return self._reason_name_ambiguity(payment_data, tenant_matches, context)
            elif scenario_type == "overpayment":
                return self._reason_overpayment(payment_data, available_invoices, context)
            elif scenario_type == "roommate_payment":
                return self._reason_roommate_payment(payment_data, available_invoices, context)
            else:
                return self._reason_general_scenario(scenario_type, payment_data, available_invoices, tenant_matches, context)
                
        except Exception as e:
            logger.error(f"Error in AI reasoning: {str(e)}")
            return self._create_error_result(f"Error during AI reasoning: {str(e)}")
    
    def _reason_multiple_invoices(self, payment_data: Dict[str, Any], 
                                available_invoices: List[Dict[str, Any]], 
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """AI reasoning for multiple invoice scenarios"""
        
        payment_amount = payment_data.get('amount', 0)
        payment_date = payment_data.get('date', '')
        payment_ref = payment_data.get('ref', '')
        
        # Analyze payment reference for month specificity
        month_hints = self._extract_month_hints(payment_ref)
        
        # Sort invoices by date (oldest first)
        sorted_invoices = sorted(available_invoices, key=lambda x: x.get('Date', ''))
        
        reasoning = f"Analyzing payment of ${payment_amount} with reference '{payment_ref}'. "
        
        # Check for exact amount matches first
        exact_matches = [inv for inv in sorted_invoices if abs(inv.get('AmountDue', 0) - payment_amount) < 0.01]
        
        if len(exact_matches) == 1:
            selected_invoice = exact_matches[0]
            reasoning += f"Found single exact amount match: {selected_invoice.get('InvoiceNumber')}. "
            confidence = 0.95
        elif len(exact_matches) > 1:
            # Multiple exact matches - use date logic
            if month_hints:
                # Try to match by month
                month_matches = [inv for inv in exact_matches if month_hints in inv.get('Date', '')]
                if len(month_matches) == 1:
                    selected_invoice = month_matches[0]
                    reasoning += f"Used month hint '{month_hints}' to select {selected_invoice.get('InvoiceNumber')}. "
                    confidence = 0.90
                else:
                    selected_invoice = exact_matches[0]  # Take oldest
                    reasoning += f"Multiple exact matches found, using oldest invoice {selected_invoice.get('InvoiceNumber')}. "
                    confidence = 0.80
            else:
                selected_invoice = exact_matches[0]  # Take oldest
                reasoning += f"Multiple exact matches found, using oldest invoice {selected_invoice.get('InvoiceNumber')}. "
                confidence = 0.80
        else:
            # No exact matches - use partial matching with business logic
            partial_matches = [inv for inv in sorted_invoices if inv.get('AmountDue', 0) >= payment_amount]
            
            if len(partial_matches) == 1:
                selected_invoice = partial_matches[0]
                reasoning += f"Single partial match found: {selected_invoice.get('InvoiceNumber')}. "
                confidence = 0.85
            elif len(partial_matches) > 1:
                # Multiple partial matches - use oldest first logic
                selected_invoice = partial_matches[0]
                reasoning += f"Multiple partial matches found, applying to oldest invoice {selected_invoice.get('InvoiceNumber')}. "
                confidence = 0.75
            else:
                # No matches found
                return self._create_no_match_result(
                    "No suitable invoice found for payment amount",
                    recommendations=["Verify payment amount", "Check for data entry errors", "Flag for human review"]
                )
        
        return {
            "success": True,
            "selected_invoice": selected_invoice,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "recommendations": ["Verify invoice selection", "Monitor for similar patterns"],
            "warnings": ["Multiple options considered - verify selection"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _reason_name_ambiguity(self, payment_data: Dict[str, Any], 
                             tenant_matches: List[Dict[str, Any]], 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """AI reasoning for name ambiguity scenarios"""
        
        payment_name = payment_data.get('person', '')
        payment_amount = payment_data.get('amount', 0)
        
        reasoning = f"Analyzing name ambiguity for '{payment_name}' with payment ${payment_amount}. "
        
        if not tenant_matches:
            return self._create_no_match_result(
                f"No tenant matches found for '{payment_name}'",
                recommendations=["Verify tenant name", "Check for new tenants", "Flag for human review"]
            )
        
        # Sort by confidence score
        sorted_matches = sorted(tenant_matches, key=lambda x: x.get('confidence_score', 0), reverse=True)
        best_match = sorted_matches[0]
        
        reasoning += f"Best match: '{best_match.get('matched_tenant')}' (confidence: {best_match.get('confidence_score', 0):.2f}). "
        
        # Additional context analysis
        if payment_amount > 0:
            # Check if payment amount matches any invoices for the best match
            reasoning += "Payment amount analysis could provide additional validation. "
        
        confidence = best_match.get('confidence_score', 0) * 0.9  # Slightly reduce confidence for AI reasoning
        
        return {
            "success": True,
            "selected_tenant": best_match.get('matched_tenant'),
            "confidence_score": confidence,
            "reasoning": reasoning,
            "alternatives": [m.get('matched_tenant') for m in sorted_matches[1:3]],
            "recommendations": ["Verify tenant identity", "Check payment history"],
            "warnings": ["Name ambiguity detected - verify selection"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _reason_overpayment(self, payment_data: Dict[str, Any], 
                          available_invoices: List[Dict[str, Any]], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """AI reasoning for overpayment scenarios"""
        
        payment_amount = payment_data.get('amount', 0)
        total_balance = sum(inv.get('AmountDue', 0) for inv in available_invoices)
        overpayment_amount = payment_amount - total_balance
        
        reasoning = f"Analyzing overpayment of ${overpayment_amount} (payment: ${payment_amount}, total balance: ${total_balance}). "
        
        # Analyze overpayment intent
        if overpayment_amount in [500, 1000, 1500, 2000]:
            reasoning += f"Overpayment amount (${overpayment_amount}) suggests security deposit. "
            recommendation = "Create separate security deposit credit"
            confidence = 0.85
        elif overpayment_amount < 100:
            reasoning += f"Small overpayment (${overpayment_amount}) likely unintentional. "
            recommendation = "Apply to oldest invoice, create small credit"
            confidence = 0.80
        else:
            reasoning += f"Significant overpayment (${overpayment_amount}) requires verification. "
            recommendation = "Verify payment intent with tenant"
            confidence = 0.70
        
        return {
            "success": True,
            "overpayment_amount": overpayment_amount,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "recommendations": [recommendation, "Create overpayment credit in Xero"],
            "warnings": ["Overpayment detected - verify intent"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _reason_roommate_payment(self, payment_data: Dict[str, Any], 
                               available_invoices: List[Dict[str, Any]], 
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """AI reasoning for roommate payment scenarios"""
        
        reasoning = "Analyzing potential roommate payment scenario. "
        
        # This would require more sophisticated analysis
        # For now, provide general guidance
        
        reasoning += "Roommate payments require careful handling to ensure proper allocation. "
        
        return {
            "success": True,
            "confidence_score": 0.60,
            "reasoning": reasoning,
            "recommendations": ["Verify roommate arrangement", "Check lease agreements", "Flag for human review"],
            "warnings": ["Complex roommate scenario - manual review recommended"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _reason_general_scenario(self, scenario_type: str, payment_data: Dict[str, Any],
                               available_invoices: List[Dict[str, Any]], 
                               tenant_matches: List[Dict[str, Any]],
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """General AI reasoning for unknown scenarios"""
        
        reasoning = f"Performing general AI reasoning for scenario type: {scenario_type}. "
        
        return {
            "success": True,
            "confidence_score": 0.50,
            "reasoning": reasoning,
            "recommendations": ["Manual review recommended", "Document scenario for future analysis"],
            "warnings": ["Unknown scenario type - human review required"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_month_hints(self, payment_ref: str) -> Optional[str]:
        """Extract month hints from payment reference"""
        if not payment_ref:
            return None
        
        ref_lower = payment_ref.lower()
        month_mapping = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        
        for month_name, month_num in month_mapping.items():
            if month_name in ref_lower:
                return month_num
        
        return None
    
    def _create_no_match_result(self, reasoning: str, recommendations: List[str] = None) -> Dict[str, Any]:
        """Create a no-match result"""
        return {
            "success": False,
            "confidence_score": 0.0,
            "reasoning": reasoning,
            "recommendations": recommendations or [],
            "warnings": ["No match found"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result"""
        return {
            "success": False,
            "confidence_score": 0.0,
            "reasoning": error_message,
            "recommendations": ["Check system logs", "Flag for human review"],
            "warnings": ["Error during AI reasoning"],
            "timestamp": datetime.now().isoformat()
        }
