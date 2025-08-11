"""
Dashboard and Reporting Tools for AI Agent
Provides visibility into items requiring human review
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

class DashboardInput(BaseModel):
    """Input schema for dashboard operations"""
    report_type: str = Field(description="Type of report (pending_review, summary, trends)")
    date_range: Optional[str] = Field(default="7d", description="Date range (1d, 7d, 30d, all)")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")

class DashboardTool(BaseTool):
    """Tool for generating dashboard reports and tracking review items"""
    
    name: str = "generate_dashboard_report"
    description: str = """
    Generate dashboard reports for tracking items requiring human review.
    
    This tool:
    1. Tracks pending review items
    2. Generates summary reports
    3. Identifies trends and patterns
    4. Provides actionable insights
    5. Creates structured reports for management
    
    Use this tool to monitor system performance and review requirements.
    """
    args_schema: type[DashboardInput] = DashboardInput
    
    def __init__(self):
        super().__init__()
        self.notification_log_path = os.path.join(project_root, "ai_agent", "data", "notifications")
        self.reports_path = os.path.join(project_root, "ai_agent", "data", "reports")
        os.makedirs(self.reports_path, exist_ok=True)
    
    def _run(self, report_type: str, date_range: str = "7d", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate dashboard report
        
        Args:
            report_type: Type of report to generate
            date_range: Date range for the report
            filters: Additional filters to apply
            
        Returns:
            Dictionary with report data
        """
        logger.info(f"Generating {report_type} report for {date_range}")
        
        try:
            if report_type == "pending_review":
                return self._generate_pending_review_report(date_range, filters)
            elif report_type == "summary":
                return self._generate_summary_report(date_range, filters)
            elif report_type == "trends":
                return self._generate_trends_report(date_range, filters)
            else:
                return self._generate_custom_report(report_type, date_range, filters)
                
        except Exception as e:
            logger.error(f"Error generating dashboard report: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "report_type": report_type,
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_pending_review_report(self, date_range: str, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate report of items pending human review"""
        
        # Load notification logs
        notification_files = self._get_notification_files(date_range)
        pending_items = []
        
        for file_path in notification_files:
            try:
                with open(file_path, 'r') as f:
                    notification_data = json.load(f)
                
                # Extract items that still need review
                for item in notification_data.get('items', []):
                    if not item.get('resolved', False):  # Assume items need review unless marked resolved
                        pending_items.append({
                            'notification_id': os.path.basename(file_path),
                            'notification_date': notification_data.get('timestamp'),
                            'notification_type': notification_data.get('notification_type'),
                            'priority': notification_data.get('priority'),
                            'item': item
                        })
            except Exception as e:
                logger.warning(f"Error reading notification file {file_path}: {e}")
        
        # Apply filters
        if filters:
            pending_items = self._apply_filters(pending_items, filters)
        
        # Group by priority
        priority_groups = {
            'high': [],
            'medium': [],
            'low': []
        }
        
        for item in pending_items:
            priority = item.get('priority', 'medium')
            priority_groups[priority].append(item)
        
        report = {
            "success": True,
            "report_type": "pending_review",
            "date_range": date_range,
            "total_pending": len(pending_items),
            "priority_breakdown": {
                'high': len(priority_groups['high']),
                'medium': len(priority_groups['medium']),
                'low': len(priority_groups['low'])
            },
            "pending_items": pending_items,
            "priority_groups": priority_groups,
            "generated_at": datetime.now().isoformat()
        }
        
        # Save report
        self._save_report(report, "pending_review")
        
        return report
    
    def _generate_summary_report(self, date_range: str, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary report of processing activity"""
        
        # Load notification logs
        notification_files = self._get_notification_files(date_range)
        
        summary = {
            "total_notifications": len(notification_files),
            "notification_types": {},
            "priority_distribution": {},
            "resolution_times": [],
            "common_issues": {},
            "success_rate": 0.0
        }
        
        total_items = 0
        resolved_items = 0
        
        for file_path in notification_files:
            try:
                with open(file_path, 'r') as f:
                    notification_data = json.load(f)
                
                # Count notification types
                notification_type = notification_data.get('notification_type', 'unknown')
                summary["notification_types"][notification_type] = summary["notification_types"].get(notification_type, 0) + 1
                
                # Count priority distribution
                priority = notification_data.get('priority', 'medium')
                summary["priority_distribution"][priority] = summary["priority_distribution"].get(priority, 0) + 1
                
                # Count items and resolutions
                items = notification_data.get('items', [])
                total_items += len(items)
                
                for item in items:
                    if item.get('resolved', False):
                        resolved_items += 1
                    
                    # Track common issues
                    issue_type = item.get('type', 'unknown')
                    summary["common_issues"][issue_type] = summary["common_issues"].get(issue_type, 0) + 1
                
            except Exception as e:
                logger.warning(f"Error reading notification file {file_path}: {e}")
        
        # Calculate success rate
        if total_items > 0:
            summary["success_rate"] = (resolved_items / total_items) * 100
        
        report = {
            "success": True,
            "report_type": "summary",
            "date_range": date_range,
            "summary": summary,
            "generated_at": datetime.now().isoformat()
        }
        
        # Save report
        self._save_report(report, "summary")
        
        return report
    
    def _generate_trends_report(self, date_range: str, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trends analysis report"""
        
        # This would analyze patterns over time
        # For now, return a basic structure
        
        trends = {
            "daily_volume": {},
            "issue_patterns": {},
            "performance_metrics": {},
            "recommendations": []
        }
        
        report = {
            "success": True,
            "report_type": "trends",
            "date_range": date_range,
            "trends": trends,
            "generated_at": datetime.now().isoformat()
        }
        
        # Save report
        self._save_report(report, "trends")
        
        return report
    
    def _generate_custom_report(self, report_type: str, date_range: str, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate custom report based on type"""
        
        return {
            "success": True,
            "report_type": report_type,
            "date_range": date_range,
            "message": f"Custom report '{report_type}' generated",
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_notification_files(self, date_range: str) -> List[str]:
        """Get notification files within date range"""
        
        if not os.path.exists(self.notification_log_path):
            return []
        
        # Calculate date cutoff
        if date_range == "1d":
            cutoff_date = datetime.now() - timedelta(days=1)
        elif date_range == "7d":
            cutoff_date = datetime.now() - timedelta(days=7)
        elif date_range == "30d":
            cutoff_date = datetime.now() - timedelta(days=30)
        else:  # "all"
            cutoff_date = datetime.min
        
        files = []
        for filename in os.listdir(self.notification_log_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.notification_log_path, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_time >= cutoff_date:
                    files.append(file_path)
        
        return files
    
    def _apply_filters(self, items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to items"""
        
        filtered_items = items
        
        if 'priority' in filters:
            filtered_items = [item for item in filtered_items if item.get('priority') == filters['priority']]
        
        if 'type' in filters:
            filtered_items = [item for item in filtered_items if item.get('item', {}).get('type') == filters['type']]
        
        if 'confidence_min' in filters:
            filtered_items = [item for item in filtered_items if item.get('item', {}).get('confidence_score', 0) >= filters['confidence_min']]
        
        return filtered_items
    
    def _save_report(self, report: Dict[str, Any], report_type: str) -> str:
        """Save report to file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_{report_type}_{timestamp}.json"
        filepath = os.path.join(self.reports_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Dashboard report saved to: {filepath}")
        return filepath
