"""
Google tools for the AI agent
Wraps Google services (Gmail, Drive) functionality
"""

import os
import sys
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

class GmailFetchInput(BaseModel):
    """Input schema for Gmail operations"""
    start_date: Optional[str] = Field(default=None, description="Start date for email search (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date for email search (YYYY-MM-DD)")
    sender: Optional[str] = Field(default="aptexx", description="Email sender to filter by")
    check_unprocessed_only: Optional[bool] = Field(default=True, description="Only check for unprocessed emails")

class GmailFetchTool(BaseTool):
    """Tool for fetching emails from Gmail"""
    
    name: str = "fetch_gmail_emails"
    description: str = """
    Fetch Aptexx payment emails from Gmail.
    
    This tool:
    1. Connects to Gmail API
    2. Searches for Aptexx payment emails
    3. Downloads email content (HTML and text)
    4. Tracks processed emails to avoid duplicates
    5. Returns email data for processing
    
    Use this tool when you need to get the latest Aptexx payment emails.
    """
    args_schema: type[GmailFetchInput] = GmailFetchInput
    
    def __init__(self):
        super().__init__()
        self._processed_emails_path = os.path.join(project_root, "ai_agent", "data", "processed_emails.json")
        self._ensure_processed_emails_file()
    
    def _ensure_processed_emails_file(self):
        """Ensure the processed emails tracking file exists"""
        os.makedirs(os.path.dirname(self._processed_emails_path), exist_ok=True)
        if not os.path.exists(self._processed_emails_path):
            with open(self._processed_emails_path, 'w') as f:
                import json
                json.dump({"processed_emails": []}, f)
    
    def _load_processed_emails(self) -> List[str]:
        """Load list of processed email IDs"""
        try:
            with open(self._processed_emails_path, 'r') as f:
                import json
                data = json.load(f)
                return data.get("processed_emails", [])
        except Exception as e:
            logger.warning(f"Error loading processed emails: {e}")
            return []
    
    def _save_processed_emails(self, email_ids: List[str]):
        """Save list of processed email IDs"""
        try:
            with open(self._processed_emails_path, 'w') as f:
                import json
                json.dump({"processed_emails": email_ids}, f)
        except Exception as e:
            logger.error(f"Error saving processed emails: {e}")
    
    def _run(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
             sender: str = "aptexx", check_unprocessed_only: bool = True) -> Dict[str, Any]:
        """
        Fetch emails from Gmail
        
        Args:
            start_date: Start date for search
            end_date: End date for search
            sender: Email sender to filter by
            check_unprocessed_only: Only return unprocessed emails
            
        Returns:
            Dictionary with email data
        """
        logger.info(f"Fetching emails from {sender} from {start_date} to {end_date}")
        
        try:
            # Import Gmail functionality
            from Google.GmailClient.gmail_watcher import fetch_aptexx_emails
            
            # Set default date range (last 7 days if not specified)
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Fetch emails from Gmail
            emails = fetch_aptexx_emails(start_date=start_date, end_date=end_date)
            
            # Filter out already processed emails if requested
            if check_unprocessed_only:
                processed_ids = self._load_processed_emails()
                unprocessed_emails = []
                new_processed_ids = processed_ids.copy()
                
                for email in emails:
                    # Use email subject + date as unique identifier
                    email_id = f"{email.get('subject', '')}_{email.get('date', '')}"
                    if email_id not in processed_ids:
                        unprocessed_emails.append(email)
                        new_processed_ids.append(email_id)
                
                # Save updated processed emails list
                self._save_processed_emails(new_processed_ids)
                emails = unprocessed_emails
            
            logger.info(f"Found {len(emails)} emails from Aptexx")
            
            return {
                "success": True,
                "emails": emails,
                "count": len(emails),
                "date_range": f"{start_date} to {end_date}",
                "processed_only": check_unprocessed_only,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return {
                "success": False,
                "error": str(e),
                "emails": [],
                "count": 0,
                "timestamp": datetime.now().isoformat()
            }
