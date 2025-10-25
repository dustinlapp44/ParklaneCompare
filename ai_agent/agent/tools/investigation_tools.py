"""
Advanced Investigation Tools for Intelligent Payment Analysis
These tools give the agent the capability to investigate payment scenarios like a human would
"""

import os
import sys
import json
import sqlite3
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

class TenantHistoryInput(BaseModel):
    """Input schema for tenant payment history analysis"""
    tenant_name: str = Field(description="Name of the tenant to investigate")
    months_back: int = Field(default=12, description="Number of months to look back")
    include_patterns: bool = Field(default=True, description="Whether to analyze payment patterns")

class InvoiceRelationshipInput(BaseModel):
    """Input schema for invoice relationship analysis"""
    tenant_name: str = Field(description="Primary tenant name")
    property_name: str = Field(description="Property name")
    amount: float = Field(description="Payment amount to investigate")

class BusinessScenarioInput(BaseModel):
    """Input schema for business scenario validation"""
    payment: Dict[str, Any] = Field(description="Payment data")
    potential_invoices: List[Dict[str, Any]] = Field(description="List of potential matching invoices")
    scenario_type: str = Field(description="Type of scenario to validate (overpayment, prepayment, etc.)")

class PaymentInvestigationInput(BaseModel):
    """Input schema for comprehensive payment investigation"""
    payment_data: str = Field(description="Payment information as text: 'tenant_name=NAME, amount=AMOUNT, property_name=PROPERTY, reference=REF, payment_date=DATE'")

class TenantPaymentHistoryTool(BaseTool):
    """Tool for analyzing tenant payment history and patterns"""
    
    name: str = "analyze_tenant_payment_history"
    description: str = """
    Analyze a tenant's payment history to understand patterns and identify anomalies.
    
    This tool:
    1. Retrieves all payments made by a tenant over specified time period
    2. Analyzes payment patterns (amounts, frequency, timing)
    3. Identifies recurring payment amounts
    4. Checks for payment behavior changes
    5. Provides insights for current payment context
    
    Use this when you need to understand a tenant's payment behavior to make better matching decisions.
    """
    args_schema: type[TenantHistoryInput] = TenantHistoryInput
    
    def _run(self, tenant_name: str, months_back: int = 12, include_patterns: bool = True) -> Dict[str, Any]:
        """Analyze tenant payment history"""
        try:
            db_path = "/tmp/payments.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back * 30)
            
            # Get payment history for tenant (fuzzy name matching via invoices)
            cursor.execute("""
                SELECT p.reference, p.amount, p.date, i.contact_name
                FROM payments p
                LEFT JOIN invoices i ON p.invoice_id = i.invoice_id
                WHERE LOWER(i.contact_name) LIKE LOWER(?)
                ORDER BY p.date DESC
                LIMIT 50
            """, (f"%{tenant_name}%",))
            
            payments = cursor.fetchall()
            
            if not payments:
                return {
                    "success": True,
                    "tenant_name": tenant_name,
                    "payments_found": 0,
                    "analysis": "No payment history found for this tenant",
                    "patterns": {},
                    "recommendations": ["Verify tenant name spelling", "Check if this is a new tenant"]
                }
            
            # Analyze patterns if requested
            analysis = {
                "success": True,
                "tenant_name": tenant_name,
                "payments_found": len(payments),
                "recent_payments": [
                    {
                        "reference": p[0],
                        "amount": p[1],
                        "date": p[2],
                        "contact_name": p[3]
                    } for p in payments[:5]
                ],
                "total_paid": sum(p[1] for p in payments),
                "patterns": {},
                "recommendations": []
            }
            
            if include_patterns and len(payments) >= 3:
                amounts = [p[1] for p in payments]
                
                # Find most common payment amount
                amount_counts = {}
                for amount in amounts:
                    amount_counts[amount] = amount_counts.get(amount, 0) + 1
                
                most_common_amount = max(amount_counts, key=amount_counts.get)
                
                analysis["patterns"] = {
                    "most_common_amount": most_common_amount,
                    "amount_frequency": amount_counts.get(most_common_amount, 0),
                    "unique_amounts": len(set(amounts)),
                    "average_amount": sum(amounts) / len(amounts),
                    "payment_frequency": f"{len(payments)} payments in {months_back} months"
                }
                
                # Generate recommendations based on patterns
                if amount_counts.get(most_common_amount, 0) >= 3:
                    analysis["recommendations"].append(f"Regular payment pattern detected: ${most_common_amount}")
                
                if len(set(amounts)) == 1:
                    analysis["recommendations"].append("Tenant pays consistent amounts")
                else:
                    analysis["recommendations"].append("Tenant payment amounts vary - check for different invoice types")
            
            conn.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing tenant payment history: {e}")
            return {
                "success": False,
                "error": str(e),
                "tenant_name": tenant_name
            }

class InvoiceRelationshipTool(BaseTool):
    """Tool for finding related invoices and tenant relationships"""
    
    name: str = "find_invoice_relationships"
    description: str = """
    Find related invoices and tenant relationships for complex payment scenarios.
    
    This tool:
    1. Finds all invoices for a tenant across different properties
    2. Identifies roommate/co-tenant invoices at the same property
    3. Looks for invoice amount combinations that match payment
    4. Checks for invoice series or recurring billing patterns
    5. Identifies potential overpayment scenarios
    
    Use this when single invoice matching fails and you need to investigate complex scenarios.
    """
    args_schema: type[InvoiceRelationshipInput] = InvoiceRelationshipInput
    
    def _run(self, tenant_name: str, property_name: str, amount: float) -> Dict[str, Any]:
        """Find related invoices for complex matching scenarios"""
        try:
            db_path = "/tmp/payments.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Search for related invoices
            results = {
                "success": True,
                "tenant_name": tenant_name,
                "property_name": property_name,
                "payment_amount": amount,
                "relationships": {},
                "scenarios": [],
                "recommendations": []
            }
            
            # 1. Find all invoices for this tenant (various name formats)
            cursor.execute("""
                SELECT invoice_id, contact_name, amount_due, issue_date, status, reference
                FROM invoices 
                WHERE (LOWER(contact_name) LIKE LOWER(?) OR LOWER(contact_name) LIKE LOWER(?))
                  AND status != 'PAID'
                ORDER BY issue_date DESC
                LIMIT 20
            """, (f"%{tenant_name}%", f"%{tenant_name.split()[0]}%"))
            
            tenant_invoices = cursor.fetchall()
            
            # 2. Find invoices at the same property (potential roommates)
            cursor.execute("""
                SELECT invoice_id, contact_name, amount_due, issue_date, status, reference
                FROM invoices 
                WHERE LOWER(reference) LIKE LOWER(?)
                  AND status != 'PAID'
                  AND LOWER(contact_name) NOT LIKE LOWER(?)
                ORDER BY issue_date DESC
                LIMIT 10
            """, (f"%{property_name}%", f"%{tenant_name}%"))
            
            property_invoices = cursor.fetchall()
            
            # 3. Look for amount combinations
            if tenant_invoices:
                invoice_amounts = [inv[2] for inv in tenant_invoices]
                
                # Check for exact match
                exact_matches = [inv for inv in tenant_invoices if abs(inv[2] - amount) < 0.01]
                
                # Check for combination matches (up to 3 invoices)
                combination_matches = []
                for i, inv1 in enumerate(tenant_invoices):
                    for j, inv2 in enumerate(tenant_invoices[i+1:], i+1):
                        if abs((inv1[2] + inv2[2]) - amount) < 0.01:
                            combination_matches.append([inv1, inv2])
                        
                        # Three invoice combinations
                        for k, inv3 in enumerate(tenant_invoices[j+1:], j+1):
                            if abs((inv1[2] + inv2[2] + inv3[2]) - amount) < 0.01:
                                combination_matches.append([inv1, inv2, inv3])
                
                results["relationships"]["tenant_invoices"] = [
                    {
                        "invoice_id": inv[0],
                        "contact_name": inv[1],
                        "amount_due": inv[2],
                        "issue_date": inv[3],
                        "status": inv[4]
                    } for inv in tenant_invoices
                ]
                
                # Analyze scenarios
                if exact_matches:
                    results["scenarios"].append({
                        "type": "exact_match",
                        "confidence": 95,
                        "description": f"Found {len(exact_matches)} exact amount matches",
                        "invoices": [inv[0] for inv in exact_matches]
                    })
                
                if combination_matches:
                    results["scenarios"].append({
                        "type": "combination_match",
                        "confidence": 85,
                        "description": f"Found {len(combination_matches)} invoice combinations matching payment amount",
                        "combinations": [[inv[0] for inv in combo] for combo in combination_matches]
                    })
                
                # Check for overpayment scenario
                max_single_invoice = max(invoice_amounts) if invoice_amounts else 0
                if amount > max_single_invoice and max_single_invoice > 0:
                    overpay_amount = amount - max_single_invoice
                    results["scenarios"].append({
                        "type": "overpayment",
                        "confidence": 70,
                        "description": f"Potential overpayment of ${overpay_amount:.2f}",
                        "base_invoice": max_single_invoice,
                        "overpayment_amount": overpay_amount
                    })
            
            # 4. Check roommate scenarios
            if property_invoices:
                results["relationships"]["property_invoices"] = [
                    {
                        "invoice_id": inv[0],
                        "contact_name": inv[1],
                        "amount_due": inv[2],
                        "date": inv[3]
                    } for inv in property_invoices
                ]
                
                # Look for roommate payment patterns
                property_amounts = [inv[2] for inv in property_invoices]
                for prop_amount in property_amounts:
                    if abs(prop_amount - amount) < 0.01:
                        results["scenarios"].append({
                            "type": "roommate_payment",
                            "confidence": 60,
                            "description": f"Payment amount matches roommate invoice at same property",
                            "potential_roommate": property_invoices[property_amounts.index(prop_amount)][1]
                        })
            
            # Generate recommendations
            if not results["scenarios"]:
                results["recommendations"].extend([
                    "No clear invoice matches found",
                    "Consider if this is a prepayment for future invoice",
                    "Verify tenant name and property details",
                    "Check if invoice exists in Xero but not synced to database"
                ])
            else:
                for scenario in results["scenarios"]:
                    if scenario["confidence"] >= 85:
                        results["recommendations"].append(f"High confidence {scenario['type']}: {scenario['description']}")
                    elif scenario["confidence"] >= 70:
                        results["recommendations"].append(f"Possible {scenario['type']}: {scenario['description']}")
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error finding invoice relationships: {e}")
            return {
                "success": False,
                "error": str(e),
                "tenant_name": tenant_name
            }

class BusinessScenarioValidatorTool(BaseTool):
    """Tool for validating common business scenarios"""
    
    name: str = "validate_business_scenario"
    description: str = """
    Validate common business scenarios that affect payment matching decisions.
    
    This tool:
    1. Checks for overpayment scenarios and calculates credit amounts
    2. Validates prepayment situations (payment before invoice creation)
    3. Identifies roommate/co-tenant payment mixups
    4. Checks for partial payment situations
    5. Validates recurring payment patterns
    
    Use this to confirm business logic for complex payment scenarios.
    """
    args_schema: type[BusinessScenarioInput] = BusinessScenarioInput
    
    def _run(self, payment: Dict[str, Any], potential_invoices: List[Dict[str, Any]], scenario_type: str) -> Dict[str, Any]:
        """Validate specific business scenarios"""
        try:
            payment_amount = payment.get('amount', 0)
            tenant_name = payment.get('person', '')
            
            result = {
                "success": True,
                "scenario_type": scenario_type,
                "payment_amount": payment_amount,
                "validation_result": {},
                "recommendations": [],
                "confidence": 0
            }
            
            if scenario_type == "overpayment":
                # Find largest unpaid invoice and calculate overpayment
                if potential_invoices:
                    largest_invoice = max(potential_invoices, key=lambda x: x.get('amount_due', 0))
                    largest_amount = largest_invoice.get('amount_due', 0)
                    
                    if payment_amount > largest_amount:
                        overpayment = payment_amount - largest_amount
                        result["validation_result"] = {
                            "is_overpayment": True,
                            "base_invoice_id": largest_invoice.get('invoice_id'),
                            "base_amount": largest_amount,
                            "overpayment_amount": overpayment,
                            "overpayment_percentage": (overpayment / largest_amount) * 100
                        }
                        result["confidence"] = 85 if overpayment < largest_amount * 0.5 else 70
                        result["recommendations"] = [
                            f"Apply ${largest_amount} to invoice {largest_invoice.get('invoice_id')}",
                            f"Create ${overpayment:.2f} credit for {tenant_name}",
                            "Verify if overpayment is intentional (covers future periods)"
                        ]
                    else:
                        result["validation_result"] = {"is_overpayment": False}
                        result["confidence"] = 95
            
            elif scenario_type == "prepayment":
                # Check if payment amount matches common rental amounts but no matching invoice
                if not potential_invoices or all(inv.get('amount_due', 0) != payment_amount for inv in potential_invoices):
                    # Check if amount matches historical payments
                    result["validation_result"] = {
                        "is_prepayment": True,
                        "reasoning": "Payment amount doesn't match existing invoices",
                        "suggested_action": "Create new invoice for this amount"
                    }
                    result["confidence"] = 60
                    result["recommendations"] = [
                        "Check if invoice for this period exists in Xero",
                        "Consider creating new invoice if this is a regular rental payment",
                        "Verify payment is for correct tenant and property"
                    ]
                else:
                    result["validation_result"] = {"is_prepayment": False}
                    result["confidence"] = 80
            
            elif scenario_type == "partial_payment":
                # Check if payment is partial for any invoice
                partial_matches = []
                for invoice in potential_invoices:
                    invoice_amount = invoice.get('amount_due', 0)
                    if 0 < payment_amount < invoice_amount:
                        partial_percentage = (payment_amount / invoice_amount) * 100
                        partial_matches.append({
                            "invoice_id": invoice.get('invoice_id'),
                            "invoice_amount": invoice_amount,
                            "partial_percentage": partial_percentage,
                            "remaining_amount": invoice_amount - payment_amount
                        })
                
                if partial_matches:
                    result["validation_result"] = {
                        "is_partial_payment": True,
                        "partial_matches": partial_matches
                    }
                    result["confidence"] = 75
                    result["recommendations"] = [
                        "Confirm if this is intended as partial payment",
                        "Apply to invoice and mark as partially paid",
                        "Set up tracking for remaining balance"
                    ]
                else:
                    result["validation_result"] = {"is_partial_payment": False}
                    result["confidence"] = 90
            
            elif scenario_type == "roommate_mixup":
                # This would require more complex analysis of property relationships
                # For now, provide basic validation
                result["validation_result"] = {
                    "potential_mixup": len(potential_invoices) == 0,
                    "investigation_needed": True
                }
                result["confidence"] = 50
                result["recommendations"] = [
                    "Check for similar tenant names at same property",
                    "Verify payment source and intended recipient",
                    "Review property tenant roster"
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating business scenario: {e}")
            return {
                "success": False,
                "error": str(e),
                "scenario_type": scenario_type
            }

class ComprehensivePaymentInvestigatorTool(BaseTool):
    """Master tool that coordinates all investigation activities"""
    
    name: str = "investigate_payment_comprehensively"
    description: str = """
    Perform a comprehensive investigation of a payment using all available tools and data sources.
    
    This tool:
    1. Coordinates multiple investigation tools systematically
    2. Analyzes payment context from multiple angles
    3. Provides consolidated findings and recommendations
    4. Assigns overall confidence scores based on all evidence
    5. Identifies the most likely scenarios and next steps
    
    Use this as the primary investigation tool for complex payment analysis.
    """
    args_schema: type[PaymentInvestigationInput] = PaymentInvestigationInput
    
    def __init__(self):
        super().__init__()
    
    def _run(self, payment_data: str) -> Dict[str, Any]:
        """Perform comprehensive payment investigation"""
        try:
            # Parse payment data from text format
            import re
            
            # Extract parameters using regex
            tenant_match = re.search(r'tenant_name[=:][\s]*["\']?([^,"\']+)["\']?', payment_data)
            amount_match = re.search(r'amount[=:][\s]*([0-9.]+)', payment_data)
            property_match = re.search(r'property_name[=:][\s]*["\']?([^,"\']*)["\']?', payment_data)
            reference_match = re.search(r'reference[=:][\s]*["\']?([^,"\']*)["\']?', payment_data)
            date_match = re.search(r'payment_date[=:][\s]*["\']?([^,"\']*)["\']?', payment_data)
            
            tenant_name = tenant_match.group(1).strip() if tenant_match else "Unknown"
            amount = float(amount_match.group(1)) if amount_match else 0.0
            property_name = property_match.group(1).strip() if property_match else ""
            reference = reference_match.group(1).strip() if reference_match else ""
            payment_date = date_match.group(1).strip() if date_match else ""
            
            # Reconstruct payment dict for internal use
            payment = {
                'person': tenant_name,
                'amount': amount,
                'property': property_name,
                'ref': reference,
                'date': payment_date
            }
            
            investigation = {
                "success": True,
                "payment_summary": {
                    "tenant": tenant_name,
                    "amount": amount,
                    "property": property_name,
                    "reference": reference
                },
                "investigations": {},
                "scenarios": [],
                "overall_confidence": 0,
                "primary_recommendation": "",
                "detailed_findings": []
            }
            
            # 1. Analyze tenant payment history
            history_tool = TenantPaymentHistoryTool()
            history_result = history_tool._run(tenant_name, months_back=6)
            investigation["investigations"]["payment_history"] = history_result
            
            # 2. Find invoice relationships
            relationship_tool = InvoiceRelationshipTool()
            relationship_result = relationship_tool._run(tenant_name, property_name, amount)
            investigation["investigations"]["invoice_relationships"] = relationship_result
            
            # 3. Validate business scenarios based on findings
            scenario_tool = BusinessScenarioValidatorTool()
            potential_invoices = relationship_result.get("relationships", {}).get("tenant_invoices", [])
            
            if potential_invoices:
                # Test overpayment scenario
                overpay_result = scenario_tool._run(payment, potential_invoices, "overpayment")
                if overpay_result.get("validation_result", {}).get("is_overpayment"):
                    investigation["scenarios"].append(overpay_result)
                
                # Test partial payment scenario
                partial_result = scenario_tool._run(payment, potential_invoices, "partial_payment")
                if partial_result.get("validation_result", {}).get("is_partial_payment"):
                    investigation["scenarios"].append(partial_result)
            else:
                # Test prepayment scenario
                prepay_result = scenario_tool._run(payment, [], "prepayment")
                investigation["scenarios"].append(prepay_result)
            
            # 4. Calculate overall confidence and primary recommendation
            scenario_confidences = [s.get("confidence", 0) for s in investigation["scenarios"]]
            relationship_scenarios = relationship_result.get("scenarios", [])
            
            if relationship_scenarios:
                max_relationship_confidence = max(s.get("confidence", 0) for s in relationship_scenarios)
                scenario_confidences.append(max_relationship_confidence)
            
            if scenario_confidences:
                investigation["overall_confidence"] = max(scenario_confidences)
                
                # Find primary recommendation
                best_scenario = None
                best_confidence = 0
                
                for scenario in investigation["scenarios"]:
                    if scenario.get("confidence", 0) > best_confidence:
                        best_confidence = scenario.get("confidence", 0)
                        best_scenario = scenario
                
                for scenario in relationship_scenarios:
                    if scenario.get("confidence", 0) > best_confidence:
                        best_confidence = scenario.get("confidence", 0)
                        best_scenario = scenario
                
                if best_scenario:
                    investigation["primary_recommendation"] = best_scenario.get("description", "Review required")
                else:
                    investigation["primary_recommendation"] = "Manual review recommended - no clear matching scenario"
            else:
                investigation["overall_confidence"] = 30
                investigation["primary_recommendation"] = "Insufficient data for automated matching"
            
            # 5. Generate detailed findings summary
            findings = []
            
            if history_result.get("payments_found", 0) > 0:
                findings.append(f"Tenant has {history_result['payments_found']} previous payments")
                if "patterns" in history_result and history_result["patterns"]:
                    findings.append(f"Regular payment pattern: ${history_result['patterns'].get('most_common_amount', 'N/A')}")
            else:
                findings.append("No previous payment history found")
            
            if potential_invoices:
                findings.append(f"Found {len(potential_invoices)} unpaid invoices for tenant")
            else:
                findings.append("No unpaid invoices found for tenant")
            
            if relationship_scenarios:
                findings.append(f"Identified {len(relationship_scenarios)} potential matching scenarios")
            
            investigation["detailed_findings"] = findings
            
            return investigation
            
        except Exception as e:
            logger.error(f"Error in comprehensive payment investigation: {e}")
            return {
                "success": False,
                "error": str(e),
                "payment_summary": payment
            }
