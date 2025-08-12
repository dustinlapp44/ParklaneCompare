"""
Notification Tools for AI Agent
Comprehensive system for notifying humans about items requiring review
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

class NotificationInput(BaseModel):
    """Input schema for notifications"""
    notification_type: str = Field(description="Type of notification (review_required, error, summary, etc.)")
    items: List[Dict[str, Any]] = Field(description="Items requiring attention")
    priority: str = Field(description="Priority level (high, medium, low)")
    recipients: List[str] = Field(description="Email recipients")
    subject: str = Field(description="Email subject line")
    message: str = Field(description="Additional message content")

class NotificationTool(BaseTool):
    """Tool for sending comprehensive notifications"""
    
    name: str = "send_notification"
    description: str = """
    Send notifications about items requiring human review or attention.
    
    This tool:
    1. Creates detailed email reports with structured data
    2. Saves notification logs for tracking
    3. Categorizes items by priority and type
    4. Provides actionable recommendations
    5. Tracks notification history
    
    Use this tool when items need human review or when errors occur.
    """
    args_schema: type[NotificationInput] = NotificationInput
    
    def __init__(self):
        super().__init__()
        # Initialize notification log path
        self._notification_log_path = os.path.join(project_root, "ai_agent", "data", "notifications")
        os.makedirs(self._notification_log_path, exist_ok=True)
    
    @property
    def notification_log_path(self):
        return self._notification_log_path
    
    def _run(self, notification_type: str, items: List[Dict[str, Any]], 
             priority: str, recipients: List[str], subject: str, message: str) -> Dict[str, Any]:
        """
        Send comprehensive notification
        
        Args:
            notification_type: Type of notification
            items: Items requiring attention
            priority: Priority level
            recipients: Email recipients
            subject: Email subject
            message: Additional message
            
        Returns:
            Dictionary with notification results
        """
        logger.info(f"Sending {notification_type} notification to {len(recipients)} recipients")
        
        try:
            # Step 1: Create notification content
            notification_content = self._create_notification_content(
                notification_type, items, priority, subject, message
            )
            
            # Step 2: Save notification log
            log_file = self._save_notification_log(notification_type, items, priority, recipients)
            
            # Step 3: Send email notification
            email_result = self._send_email_notification(recipients, subject, notification_content)
            
            # Step 4: Create summary report
            summary = self._create_summary_report(items, notification_type)
            
            return {
                "success": True,
                "notification_type": notification_type,
                "items_count": len(items),
                "priority": priority,
                "recipients": recipients,
                "log_file": log_file,
                "email_sent": email_result.get("success", False),
                "summary": summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "notification_type": notification_type,
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_notification_content(self, notification_type: str, items: List[Dict[str, Any]], 
                                   priority: str, subject: str, message: str) -> str:
        """Create comprehensive notification content"""
        
        # Create HTML email content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
                .priority-high {{ background-color: #ffebee; border-left: 4px solid #f44336; }}
                .priority-medium {{ background-color: #fff3e0; border-left: 4px solid #ff9800; }}
                .priority-low {{ background-color: #e8f5e8; border-left: 4px solid #4caf50; }}
                .item {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
                .item-header {{ font-weight: bold; margin-bottom: 5px; }}
                .item-details {{ margin-left: 20px; }}
                .recommendations {{ background-color: #e3f2fd; padding: 10px; border-radius: 3px; margin-top: 10px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Payment Processing Review Required</h2>
                <p><strong>Type:</strong> {notification_type}</p>
                <p><strong>Priority:</strong> {priority.upper()}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="priority-{priority}">
                <h3>Summary</h3>
                <p>{message}</p>
                <p><strong>Total Items:</strong> {len(items)}</p>
            </div>
            
            <h3>Items Requiring Review</h3>
        """
        
        # Add items table
        if items:
            html_content += """
            <table>
                <tr>
                    <th>Item</th>
                    <th>Type</th>
                    <th>Confidence</th>
                    <th>Issue</th>
                    <th>Recommendation</th>
                </tr>
            """
            
            for i, item in enumerate(items, 1):
                item_type = item.get('type', 'Unknown')
                confidence = item.get('confidence_score', 0)
                issue = item.get('reasoning', 'No issue specified')
                recommendation = item.get('recommendations', ['Manual review'])[0] if item.get('recommendations') else 'Manual review'
                
                html_content += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item_type}</td>
                    <td>{confidence:.2f}</td>
                    <td>{issue}</td>
                    <td>{recommendation}</td>
                </tr>
                """
            
            html_content += "</table>"
        
        # Add detailed items
        for i, item in enumerate(items, 1):
            html_content += f"""
            <div class="item">
                <div class="item-header">Item {i}: {item.get('type', 'Unknown')}</div>
                <div class="item-details">
                    <p><strong>Payment:</strong> {item.get('payment_data', {}).get('person', 'N/A')} - ${item.get('payment_data', {}).get('amount', 'N/A')}</p>
                    <p><strong>Issue:</strong> {item.get('reasoning', 'No issue specified')}</p>
                    <p><strong>Confidence:</strong> {item.get('confidence_score', 0):.2f}</p>
                </div>
                <div class="recommendations">
                    <strong>Recommendations:</strong>
                    <ul>
            """
            
            for rec in item.get('recommendations', ['Manual review']):
                html_content += f"<li>{rec}</li>"
            
            html_content += """
                    </ul>
                </div>
            </div>
            """
        
        html_content += """
            <div style="margin-top: 20px; padding: 10px; background-color: #f9f9f9; border-radius: 3px;">
                <p><strong>Next Steps:</strong></p>
                <ol>
                    <li>Review each item above</li>
                    <li>Take appropriate action based on recommendations</li>
                    <li>Update the system with your decisions</li>
                    <li>Contact support if you need assistance</li>
                </ol>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _save_notification_log(self, notification_type: str, items: List[Dict[str, Any]], 
                             priority: str, recipients: List[str]) -> str:
        """Save notification to log file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"notification_{notification_type}_{timestamp}.json"
        filepath = os.path.join(self.notification_log_path, filename)
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "notification_type": notification_type,
            "priority": priority,
            "recipients": recipients,
            "items_count": len(items),
            "items": items
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Notification log saved to: {filepath}")
        return filepath
    
    def _send_email_notification(self, recipients: List[str], subject: str, content: str) -> Dict[str, Any]:
        """Send email notification using existing Gmail tools"""
        
        try:
            # Import and use existing Gmail sender
            from Google.GmailClient.gmail_sender import send_email
            
            # Send email
            result = send_email(
                subject=subject,
                message_text=content,
                recipients=recipients
            )
            
            return {"success": True, "recipients": recipients}
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_summary_report(self, items: List[Dict[str, Any]], notification_type: str) -> Dict[str, Any]:
        """Create summary report of notification items"""
        
        summary = {
            "total_items": len(items),
            "notification_type": notification_type,
            "item_types": {},
            "confidence_ranges": {
                "high": 0,    # 0.8+
                "medium": 0,  # 0.5-0.8
                "low": 0      # <0.5
            },
            "common_issues": {},
            "recommendations": []
        }
        
        for item in items:
            # Count item types
            item_type = item.get('type', 'unknown')
            summary["item_types"][item_type] = summary["item_types"].get(item_type, 0) + 1
            
            # Count confidence ranges
            confidence = item.get('confidence_score', 0)
            if confidence >= 0.8:
                summary["confidence_ranges"]["high"] += 1
            elif confidence >= 0.5:
                summary["confidence_ranges"]["medium"] += 1
            else:
                summary["confidence_ranges"]["low"] += 1
            
            # Collect recommendations
            for rec in item.get('recommendations', []):
                if rec not in summary["recommendations"]:
                    summary["recommendations"].append(rec)
        
        return summary
