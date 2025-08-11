"""
Email parsing tools for the AI agent
Wraps existing parser functionality with data saving and validation
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
from bs4 import BeautifulSoup

# Import existing parser
from Payments.parser import parse_html_payments, parse_aptexx_email

logger = logging.getLogger(__name__)

class EmailParsingInput(BaseModel):
    """Input schema for email parsing"""
    email_content: str = Field(description="Raw email content (HTML or text)")
    email_source: str = Field(description="Source of the email (e.g., 'gmail', 'file')")
    save_raw_data: bool = Field(default=True, description="Whether to save raw email data")
    validate_parsing: bool = Field(default=True, description="Whether to validate parsed data")

class EmailParsingTool(BaseTool):
    """Tool for parsing Aptexx payment emails"""
    
    name: str = "parse_aptexx_email"
    description: str = """
    Parse Aptexx payment emails to extract payment details.
    
    This tool:
    1. Parses HTML or text email content from Aptexx
    2. Extracts payment details (tenant, property, amount, date, reference)
    3. Saves raw email data for audit trails
    4. Validates parsed data for completeness
    
    Use this tool when you need to process Aptexx payment emails.
    """
    args_schema: type[EmailParsingInput] = EmailParsingInput
    
    def _run(self, email_content: str, email_source: str, save_raw_data: bool = True, validate_parsing: bool = True) -> Dict[str, Any]:
        """
        Parse Aptexx payment email
        
        Args:
            email_content: Raw email content
            email_source: Source of the email
            save_raw_data: Whether to save raw email data
            validate_parsing: Whether to validate parsed data
            
        Returns:
            Dictionary with parsed payments and metadata
        """
        try:
            logger.info(f"Starting email parsing from {email_source}")
            
            # Save raw email data if requested
            raw_data_path = None
            if save_raw_data:
                raw_data_path = self._save_raw_email(email_content, email_source)
            
            # Parse the email
            parsed_payments = self._parse_email_content(email_content)
            
            # Validate parsed data if requested
            validation_results = None
            if validate_parsing:
                validation_results = self._validate_parsed_data(parsed_payments)
            
            # Save parsed data
            parsed_data_path = self._save_parsed_data(parsed_payments, email_source)
            
            # Calculate summary statistics
            summary = self._calculate_summary(parsed_payments)
            
            result = {
                "success": True,
                "parsed_payments": parsed_payments,
                "summary": summary,
                "raw_data_path": raw_data_path,
                "parsed_data_path": parsed_data_path,
                "validation_results": validation_results,
                "timestamp": datetime.now().isoformat(),
                "source": email_source
            }
            
            logger.info(f"Email parsing completed. Found {len(parsed_payments)} payments")
            return result
            
        except Exception as e:
            logger.error(f"Email parsing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "source": email_source
            }
    
    def _save_raw_email(self, email_content: str, email_source: str) -> str:
        """Save raw email content to file"""
        data_dir = os.path.join(project_root, "ai_agent", "data", "test_emails")
        os.makedirs(data_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_email_{email_source}_{timestamp}.html"
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(email_content)
        
        logger.info(f"Saved raw email to: {filepath}")
        return filepath
    
    def _parse_email_content(self, email_content: str) -> List[Dict[str, Any]]:
        """Parse email content using existing parser"""
        # Try HTML parsing first
        try:
            soup = BeautifulSoup(email_content, 'html.parser')
            if soup.find('html') or soup.find('body'):
                # It's HTML content
                parsed_payments = parse_html_payments(email_content)
            else:
                # It's text content
                lines = email_content.split('\n')
                parsed_payments = parse_aptexx_email(lines)
                # Flatten the results from parse_aptexx_email
                flattened_payments = []
                for property_data in parsed_payments:
                    for payment in property_data['payments']:
                        payment['property'] = property_data['property']
                        flattened_payments.append(payment)
                parsed_payments = flattened_payments
        except Exception as e:
            logger.error(f"HTML parsing failed, trying text parsing: {str(e)}")
            # Fallback to text parsing
            lines = email_content.split('\n')
            parsed_payments = parse_aptexx_email(lines)
            # Flatten the results
            flattened_payments = []
            for property_data in parsed_payments:
                for payment in property_data['payments']:
                    payment['property'] = property_data['property']
                    flattened_payments.append(payment)
            parsed_payments = flattened_payments
        
        return parsed_payments
    
    def _validate_parsed_data(self, parsed_payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate parsed payment data"""
        validation_results = {
            "total_payments": len(parsed_payments),
            "valid_payments": 0,
            "invalid_payments": 0,
            "missing_fields": {},
            "errors": []
        }
        
        required_fields = ['property', 'person', 'amount', 'date', 'ref']
        
        for i, payment in enumerate(parsed_payments):
            payment_valid = True
            missing_fields = []
            
            # Check required fields
            for field in required_fields:
                if field not in payment or not payment[field]:
                    missing_fields.append(field)
                    payment_valid = False
            
            # Check amount format
            if 'amount' in payment:
                try:
                    if isinstance(payment['amount'], str):
                        # Remove $ and commas, convert to float
                        amount_str = payment['amount'].replace('$', '').replace(',', '')
                        float(amount_str)
                    elif isinstance(payment['amount'], (int, float)):
                        pass  # Already numeric
                    else:
                        payment_valid = False
                        validation_results["errors"].append(f"Payment {i}: Invalid amount format")
                except ValueError:
                    payment_valid = False
                    validation_results["errors"].append(f"Payment {i}: Cannot convert amount to number")
            
            # Update validation counts
            if payment_valid:
                validation_results["valid_payments"] += 1
            else:
                validation_results["invalid_payments"] += 1
                validation_results["missing_fields"][f"payment_{i}"] = missing_fields
        
        return validation_results
    
    def _save_parsed_data(self, parsed_payments: List[Dict[str, Any]], email_source: str) -> str:
        """Save parsed payment data to file"""
        data_dir = os.path.join(project_root, "ai_agent", "data", "parsed_payments")
        os.makedirs(data_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"parsed_payments_{email_source}_{timestamp}.json"
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(parsed_payments, f, indent=2, default=str)
        
        logger.info(f"Saved parsed payments to: {filepath}")
        return filepath
    
    def _calculate_summary(self, parsed_payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for parsed payments"""
        if not parsed_payments:
            return {
                "total_payments": 0,
                "total_amount": 0.0,
                "properties": [],
                "payment_methods": []
            }
        
        total_amount = 0.0
        properties = set()
        payment_methods = set()
        
        for payment in parsed_payments:
            # Calculate total amount
            if 'amount' in payment:
                try:
                    if isinstance(payment['amount'], str):
                        amount_str = payment['amount'].replace('$', '').replace(',', '')
                        total_amount += float(amount_str)
                    elif isinstance(payment['amount'], (int, float)):
                        total_amount += float(payment['amount'])
                except (ValueError, TypeError):
                    pass
            
            # Collect properties
            if 'property' in payment:
                properties.add(payment['property'])
            
            # Collect payment methods
            if 'method' in payment:
                payment_methods.add(payment['method'])
        
        return {
            "total_payments": len(parsed_payments),
            "total_amount": round(total_amount, 2),
            "properties": list(properties),
            "payment_methods": list(payment_methods)
        }
