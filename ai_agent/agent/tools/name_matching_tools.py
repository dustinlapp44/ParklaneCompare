"""
Name Matching Tools for AI Agent
Combines fuzzy matching with AI reasoning for tenant name matching
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from difflib import SequenceMatcher

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class NameMatchInput(BaseModel):
    """Input schema for name matching"""
    payment_name: str = Field(description="Name from payment data")
    available_tenants: List[str] = Field(description="List of tenant names from database")
    property_name: str = Field(description="Property name for context")
    payment_amount: float = Field(description="Payment amount for context")

class NameMatchResult(BaseModel):
    """Result of name matching"""
    success: bool
    matched_tenant: Optional[str] = None
    confidence_score: float = 0.0
    match_type: str = "none"  # exact, fuzzy_high, fuzzy_low, ai_reasoned
    reasoning: str = ""
    alternatives: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []

class NameMatchingTool(BaseTool):
    """Tool for matching tenant names using hybrid approach"""
    
    name: str = "match_tenant_name"
    description: str = """
    Match a tenant name from payment data to available tenants using fuzzy matching and AI reasoning.
    
    This tool:
    1. Performs exact name matching first
    2. Uses fuzzy matching for similar names
    3. Requires AI review for low-confidence matches
    4. Handles nicknames, typos, and variations
    5. Returns detailed reasoning and confidence scores
    
    Use this tool when you need to match a payment name to a tenant in the database.
    """
    args_schema: type[NameMatchInput] = NameMatchInput
    
    def __init__(self):
        super().__init__()
        # Confidence thresholds
        self._EXACT_THRESHOLD = 1.0
        self._FUZZY_HIGH_THRESHOLD = 0.85
        self._FUZZY_LOW_THRESHOLD = 0.70
    
    @property
    def EXACT_THRESHOLD(self):
        return self._EXACT_THRESHOLD
    
    @property
    def FUZZY_HIGH_THRESHOLD(self):
        return self._FUZZY_HIGH_THRESHOLD
    
    @property
    def FUZZY_LOW_THRESHOLD(self):
        return self._FUZZY_LOW_THRESHOLD
    
    def _run(self, payment_name: str, available_tenants: List[str], 
             property_name: str, payment_amount: float) -> Dict[str, Any]:
        """
        Match tenant name using hybrid approach
        
        Args:
            payment_name: Name from payment data
            available_tenants: List of tenant names from database
            property_name: Property name for context
            payment_amount: Payment amount for context
            
        Returns:
            Dictionary with matching results and reasoning
        """
        logger.info(f"Matching payment name '{payment_name}' to {len(available_tenants)} available tenants")
        
        try:
            # Step 1: Exact matching
            exact_match = self._exact_match(payment_name, available_tenants)
            if exact_match:
                return self._create_match_result(
                    exact_match,
                    confidence_score=1.0,
                    match_type="exact",
                    reasoning=f"Exact name match: '{payment_name}' = '{exact_match}'"
                )
            
            # Step 2: Fuzzy matching
            fuzzy_results = self._fuzzy_match(payment_name, available_tenants)
            
            if not fuzzy_results:
                return self._create_no_match_result(
                    f"No fuzzy matches found for '{payment_name}'",
                    recommendations=["Verify tenant name", "Check for typos", "Use AI reasoning"]
                )
            
            # Step 3: Analyze fuzzy results
            best_match = fuzzy_results[0]
            confidence = best_match['score']
            
            if confidence >= self.FUZZY_HIGH_THRESHOLD:
                return self._create_match_result(
                    best_match['name'],
                    confidence_score=confidence,
                    match_type="fuzzy_high",
                    reasoning=f"High-confidence fuzzy match: '{payment_name}' ≈ '{best_match['name']}' (score: {confidence:.2f})",
                    alternatives=[r['name'] for r in fuzzy_results[1:3]],  # Top 3 alternatives
                    warnings=["Fuzzy match - verify tenant identity"]
                )
            elif confidence >= self.FUZZY_LOW_THRESHOLD:
                return self._create_match_result(
                    best_match['name'],
                    confidence_score=confidence,
                    match_type="fuzzy_low",
                    reasoning=f"Low-confidence fuzzy match: '{payment_name}' ≈ '{best_match['name']}' (score: {confidence:.2f})",
                    alternatives=[r['name'] for r in fuzzy_results[1:3]],
                    warnings=["Low confidence match - AI review recommended"],
                    recommendations=["Use AI reasoning to validate match", "Flag for human review"]
                )
            else:
                return self._create_no_match_result(
                    f"Low confidence fuzzy match: '{payment_name}' ≈ '{best_match['name']}' (score: {confidence:.2f})",
                    alternatives=[r['name'] for r in fuzzy_results[:3]],
                    recommendations=["Use AI reasoning", "Flag for human review"]
                )
                
        except Exception as e:
            logger.error(f"Error in name matching: {str(e)}")
            return self._create_no_match_result(
                f"Error during name matching: {str(e)}",
                recommendations=["Check system logs", "Flag for human review"]
            )
    
    def _exact_match(self, payment_name: str, available_tenants: List[str]) -> Optional[str]:
        """Find exact name match"""
        payment_clean = self._normalize_name(payment_name)
        
        for tenant in available_tenants:
            tenant_clean = self._normalize_name(tenant)
            if payment_clean == tenant_clean:
                return tenant
        
        return None
    
    def _fuzzy_match(self, payment_name: str, available_tenants: List[str]) -> List[Dict[str, Any]]:
        """Find fuzzy name matches"""
        payment_clean = self._normalize_name(payment_name)
        results = []
        
        for tenant in available_tenants:
            tenant_clean = self._normalize_name(tenant)
            
            # Calculate similarity score
            score = SequenceMatcher(None, payment_clean, tenant_clean).ratio()
            
            # Additional checks for common variations
            score = self._enhance_score(payment_clean, tenant_clean, score)
            
            if score > 0.5:  # Only include reasonable matches
                results.append({
                    'name': tenant,
                    'score': score,
                    'original': payment_name
                })
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Remove common suffixes
        suffixes = [' jr', ' sr', ' ii', ' iii', ' iv']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _enhance_score(self, payment_name: str, tenant_name: str, base_score: float) -> float:
        """Enhance similarity score with additional checks"""
        enhanced_score = base_score
        
        # Check for nickname patterns
        nicknames = {
            'william': 'bill', 'bill': 'william',
            'robert': 'bob', 'bob': 'robert',
            'richard': 'rick', 'rick': 'richard',
            'michael': 'mike', 'mike': 'michael',
            'james': 'jim', 'jim': 'james',
            'john': 'johnny', 'johnny': 'john',
            'elizabeth': 'liz', 'liz': 'elizabeth',
            'katherine': 'kate', 'kate': 'katherine',
            'margaret': 'maggie', 'maggie': 'margaret'
        }
        
        # Check if names are nicknames of each other
        if payment_name in nicknames and nicknames[payment_name] == tenant_name:
            enhanced_score = min(enhanced_score + 0.2, 1.0)
        elif tenant_name in nicknames and nicknames[tenant_name] == payment_name:
            enhanced_score = min(enhanced_score + 0.2, 1.0)
        
        # Check for initials vs full names
        payment_parts = payment_name.split()
        tenant_parts = tenant_name.split()
        
        if len(payment_parts) == len(tenant_parts):
            # Check if one uses initials and the other uses full names
            for i in range(len(payment_parts)):
                if (len(payment_parts[i]) == 1 and len(tenant_parts[i]) > 1 and 
                    tenant_parts[i].startswith(payment_parts[i])):
                    enhanced_score = min(enhanced_score + 0.1, 1.0)
                elif (len(tenant_parts[i]) == 1 and len(payment_parts[i]) > 1 and 
                      payment_parts[i].startswith(tenant_parts[i])):
                    enhanced_score = min(enhanced_score + 0.1, 1.0)
        
        return enhanced_score
    
    def _create_match_result(self, matched_tenant: str, confidence_score: float, 
                           match_type: str, reasoning: str, alternatives: List[str] = None,
                           warnings: List[str] = None, recommendations: List[str] = None) -> Dict[str, Any]:
        """Create a match result"""
        return {
            "success": True,
            "matched_tenant": matched_tenant,
            "confidence_score": confidence_score,
            "match_type": match_type,
            "reasoning": reasoning,
            "alternatives": alternatives or [],
            "warnings": warnings or [],
            "recommendations": recommendations or [],
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_no_match_result(self, reasoning: str, alternatives: List[str] = None,
                               recommendations: List[str] = None) -> Dict[str, Any]:
        """Create a no-match result"""
        return {
            "success": False,
            "matched_tenant": None,
            "confidence_score": 0.0,
            "match_type": "none",
            "reasoning": reasoning,
            "alternatives": alternatives or [],
            "warnings": [],
            "recommendations": recommendations or [],
            "timestamp": datetime.now().isoformat()
        }
