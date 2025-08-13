"""
Daily Email Automation for Aptexx Payments
Checks for new Aptexx emails once per day and processes payments
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, 'ai_agent', 'data', 'logs', 'email_automation.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailAutomation:
    """Handles daily email automation for Aptexx payments"""
    
    def __init__(self, check_time: str = "09:00", timezone: str = "America/Denver"):
        """
        Initialize email automation
        
        Args:
            check_time: Time to check for emails (HH:MM format)
            timezone: Timezone for scheduling
        """
        self.check_time = check_time
        self.timezone = timezone
        self.last_check = None
        self.processed_count = 0
        
        # Ensure log directory exists
        log_dir = os.path.join(project_root, 'ai_agent', 'data', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logger.info(f"Email automation initialized - checking daily at {check_time}")
    
    def check_for_aptexx_emails(self) -> Dict[str, Any]:
        """
        Check for new Aptexx emails and process payments
        
        Returns:
            Dictionary with processing results
        """
        logger.info("Starting daily Aptexx email check...")
        
        try:
            # Import required modules
            from agent.tools.google_tools import GmailFetchTool
            from agent.tools.email_tools import EmailParsingTool
            from agent.tools.payment_matching_tools import PaymentMatchingTool
            
            # Initialize tools
            gmail_tool = GmailFetchTool()
            email_parser = EmailParsingTool()
            payment_matcher = PaymentMatchingTool()
            
            # Check for emails from yesterday (Aptexx sends daily summary)
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Checking for Aptexx emails from {yesterday} to {today}")
            
            # Fetch unprocessed emails
            email_result = gmail_tool._run(
                start_date=yesterday,
                end_date=today,
                sender="aptexx",
                check_unprocessed_only=True
            )
            
            if not email_result.get("success", False):
                logger.error(f"Failed to fetch emails: {email_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": email_result.get("error"),
                    "emails_processed": 0,
                    "payments_processed": 0,
                    "timestamp": datetime.now().isoformat()
                }
            
            emails = email_result.get("emails", [])
            logger.info(f"Found {len(emails)} unprocessed Aptexx emails")
            
            if not emails:
                logger.info("No new Aptexx emails found")
                return {
                    "success": True,
                    "emails_processed": 0,
                    "payments_processed": 0,
                    "message": "No new emails found",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Process each email
            total_payments = 0
            processed_payments = 0
            
            for email in emails:
                try:
                    logger.info(f"Processing email: {email.get('subject', 'No subject')}")
                    
                    # Parse email to extract payment data
                    parse_result = email_parser._run(
                        email_content=email.get('html', email.get('plain', '')),
                        email_source=f"{email.get('subject', '')}_{email.get('date', '')}",
                        save_raw_data=True,
                        validate_parsing=True
                    )
                    
                    if not parse_result.get("success", False):
                        logger.warning(f"Failed to parse email: {parse_result.get('error', 'Unknown error')}")
                        continue
                    
                    payments = parse_result.get("payments", [])
                    total_payments += len(payments)
                    
                    logger.info(f"Extracted {len(payments)} payments from email")
                    
                    # Process each payment
                    for payment in payments:
                        try:
                            # Match payment to invoice
                            match_result = payment_matcher._run(
                                payment=payment,
                                tenant_name=payment.get('person', ''),
                                amount=payment.get('amount', 0),
                                payment_date=payment.get('date', ''),
                                reference=payment.get('ref', ''),
                                property_name=payment.get('property', '')
                            )
                            
                            if match_result.get("success", False):
                                processed_payments += 1
                                logger.info(f"Successfully matched payment ${payment.get('amount')} for {payment.get('person')}")
                            else:
                                logger.warning(f"Payment matching failed for {payment.get('person')}: {match_result.get('reasoning', 'Unknown error')}")
                            
                        except Exception as e:
                            logger.error(f"Error processing payment: {e}")
                    
                except Exception as e:
                    logger.error(f"Error processing email: {e}")
            
            self.last_check = datetime.now()
            self.processed_count += processed_payments
            
            result = {
                "success": True,
                "emails_processed": len(emails),
                "payments_processed": processed_payments,
                "total_payments_found": total_payments,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Daily email check completed: {processed_payments}/{total_payments} payments processed")
            return result
            
        except Exception as e:
            logger.error(f"Error in daily email check: {e}")
            return {
                "success": False,
                "error": str(e),
                "emails_processed": 0,
                "payments_processed": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    def setup_schedule(self):
        """Setup daily schedule for email checking"""
        # Schedule daily check at specified time
        schedule.every().day.at(self.check_time).do(self.check_for_aptexx_emails)
        
        logger.info(f"Scheduled daily email check for {self.check_time}")
    
    def run_scheduler(self):
        """Run the email automation scheduler"""
        logger.info("Starting email automation scheduler...")
        
        self.setup_schedule()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Email automation scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)  # Wait before retrying

def main():
    """Main function to run email automation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aptexx Email Automation")
    parser.add_argument("--check-time", default="09:00", help="Time to check for emails (HH:MM)")
    parser.add_argument("--timezone", default="America/Denver", help="Timezone for scheduling")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit (don't schedule)")
    
    args = parser.parse_args()
    
    automation = EmailAutomation(check_time=args.check_time, timezone=args.timezone)
    
    if args.run_once:
        # Run once and exit
        result = automation.check_for_aptexx_emails()
        print(f"Email check result: {result}")
    else:
        # Run scheduled automation
        automation.run_scheduler()

if __name__ == "__main__":
    main()
