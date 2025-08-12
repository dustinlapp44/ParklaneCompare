"""
Database Synchronization Tools for AI Agent
Automated invoice database updates and payment tracking
"""

import os
import sys
import json
import logging
import schedule
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class DatabaseSyncInput(BaseModel):
    """Input schema for database synchronization"""
    sync_type: str = Field(description="Type of sync (invoices, payments, full)")
    date_range: Optional[str] = Field(default="30d", description="Date range for sync (7d, 30d, 90d)")
    force_refresh: bool = Field(default=False, description="Force full refresh even if recent")

class DatabaseSyncTool(BaseTool):
    """Tool for automated database synchronization"""
    
    name: str = "sync_database"
    description: str = """
    Synchronize local database with Xero data.
    
    This tool:
    1. Fetches latest invoices from Xero
    2. Updates local SQLite database
    3. Tracks payment applications to prevent duplicates
    4. Logs sync operations for audit trail
    5. Can be scheduled for automatic updates
    
    Use this tool to keep local database current with Xero.
    """
    args_schema: type[DatabaseSyncInput] = DatabaseSyncInput
    
    def __init__(self):
        super().__init__()
        self._db_path = os.path.join(project_root, "Payments", "payments.db")
        self._sync_log_path = os.path.join(project_root, "ai_agent", "data", "sync_logs")
        os.makedirs(self._sync_log_path, exist_ok=True)
        
        # Track last sync time
        self._last_sync_file = os.path.join(self._sync_log_path, "last_sync.json")
    
    @property
    def db_path(self):
        return self._db_path
    
    @property
    def sync_log_path(self):
        return self._sync_log_path
    
    @property
    def last_sync_file(self):
        return self._last_sync_file
    
    def _run(self, sync_type: str, date_range: str = "30d", force_refresh: bool = False) -> Dict[str, Any]:
        """
        Synchronize database with Xero
        
        Args:
            sync_type: Type of synchronization
            date_range: Date range for sync
            force_refresh: Force refresh even if recent
            
        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting database sync: {sync_type} for {date_range}")
        
        try:
            # Check if sync is needed
            if not force_refresh and not self._needs_sync():
                return {
                    "success": True,
                    "sync_type": sync_type,
                    "status": "skipped",
                    "reason": "Recent sync exists, use force_refresh=True to override",
                    "last_sync": self._get_last_sync_time(),
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calculate date range
            end_date = datetime.now()
            if date_range == "7d":
                start_date = end_date - timedelta(days=7)
            elif date_range == "30d":
                start_date = end_date - timedelta(days=30)
            elif date_range == "90d":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)  # Default to 30 days
            
            # Perform sync based on type
            if sync_type == "invoices":
                result = self._sync_invoices(start_date, end_date)
            elif sync_type == "payments":
                result = self._sync_payments(start_date, end_date)
            elif sync_type == "full":
                result = self._sync_full(start_date, end_date)
            else:
                return {
                    "success": False,
                    "error": f"Unknown sync type: {sync_type}",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update last sync time
            self._update_last_sync_time()
            
            # Log sync operation
            self._log_sync_operation(sync_type, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error during database sync: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sync_type": sync_type,
                "timestamp": datetime.now().isoformat()
            }
    
    def _needs_sync(self) -> bool:
        """Check if database needs synchronization"""
        last_sync = self._get_last_sync_time()
        if not last_sync:
            return True
        
        # Sync if last sync was more than 1 hour ago
        time_since_sync = datetime.now() - last_sync
        return time_since_sync.total_seconds() > 3600  # 1 hour
    
    def _get_last_sync_time(self) -> Optional[datetime]:
        """Get last sync time from log"""
        if os.path.exists(self.last_sync_file):
            try:
                with open(self.last_sync_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['last_sync'])
            except Exception as e:
                logger.warning(f"Error reading last sync time: {e}")
        return None
    
    def _update_last_sync_time(self):
        """Update last sync time"""
        try:
            with open(self.last_sync_file, 'w') as f:
                json.dump({
                    'last_sync': datetime.now().isoformat(),
                    'timestamp': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Error updating last sync time: {e}")
    
    def _sync_invoices(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Sync invoices from Xero"""
        try:
            # Import Xero client
            from XeroClient.xero_client import pull_tenant_invoices
            from Payments.payments_db import init_db, upsert_invoices
            
            # Initialize database
            init_db()
            
            # Fetch invoices from Xero
            logger.info(f"Fetching invoices from {start_date.date()} to {end_date.date()}")
            invoices = pull_tenant_invoices(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            if not invoices:
                return {
                    "success": True,
                    "sync_type": "invoices",
                    "invoices_fetched": 0,
                    "invoices_updated": 0,
                    "date_range": f"{start_date.date()} to {end_date.date()}",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update database
            upsert_invoices(invoices)
            
            return {
                "success": True,
                "sync_type": "invoices",
                "invoices_fetched": len(invoices),
                "invoices_updated": len(invoices),
                "date_range": f"{start_date.date()} to {end_date.date()}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing invoices: {e}")
            return {
                "success": False,
                "error": str(e),
                "sync_type": "invoices",
                "timestamp": datetime.now().isoformat()
            }
    
    def _sync_payments(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Sync payments from Xero"""
        try:
            # Import Xero client
            from XeroClient.xero_client import get_payments
            
            # Fetch payments from Xero
            logger.info(f"Fetching payments from {start_date.date()} to {end_date.date()}")
            payments = get_payments(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            # Update local payment tracking
            self._update_payment_tracking(payments)
            
            return {
                "success": True,
                "sync_type": "payments",
                "payments_fetched": len(payments) if payments else 0,
                "date_range": f"{start_date.date()} to {end_date.date()}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing payments: {e}")
            return {
                "success": False,
                "error": str(e),
                "sync_type": "payments",
                "timestamp": datetime.now().isoformat()
            }
    
    def _sync_full(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Perform full sync (invoices + payments)"""
        invoice_result = self._sync_invoices(start_date, end_date)
        payment_result = self._sync_payments(start_date, end_date)
        
        return {
            "success": invoice_result.get("success", False) and payment_result.get("success", False),
            "sync_type": "full",
            "invoice_sync": invoice_result,
            "payment_sync": payment_result,
            "date_range": f"{start_date.date()} to {end_date.date()}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_payment_tracking(self, payments: List[Dict[str, Any]]):
        """Update local payment tracking to prevent duplicates"""
        try:
            from Payments.payments_db import init_db
            import sqlite3
            
            init_db()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create payment tracking table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_tracking (
                    payment_id TEXT PRIMARY KEY,
                    xero_payment_id TEXT,
                    amount REAL,
                    date TEXT,
                    reference TEXT,
                    status TEXT,
                    applied_to_invoice TEXT,
                    sync_timestamp TEXT
                )
            ''')
            
            # Update payment tracking
            for payment in payments:
                cursor.execute('''
                    INSERT OR REPLACE INTO payment_tracking
                    (payment_id, xero_payment_id, amount, date, reference, status, sync_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    payment.get('PaymentID'),
                    payment.get('PaymentID'),
                    payment.get('Amount'),
                    payment.get('Date'),
                    payment.get('Reference'),
                    payment.get('Status'),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating payment tracking: {e}")
    
    def _log_sync_operation(self, sync_type: str, result: Dict[str, Any]):
        """Log sync operation for audit trail"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sync_{sync_type}_{timestamp}.json"
            filepath = os.path.join(self.sync_log_path, filename)
            
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Sync log saved to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error logging sync operation: {e}")

def setup_automated_sync():
    """Setup automated database synchronization"""
    
    def sync_job():
        """Job to run database sync"""
        logger.info("Running automated database sync...")
        sync_tool = DatabaseSyncTool()
        result = sync_tool._run("full", "30d", force_refresh=False)
        logger.info(f"Automated sync completed: {result.get('success', False)}")
    
    # Schedule sync every 4 hours
    schedule.every(4).hours.do(sync_job)
    
    # Also sync at 6 AM daily
    schedule.every().day.at("06:00").do(sync_job)
    
    logger.info("Automated database sync scheduled")
    return schedule

def run_sync_scheduler():
    """Run the sync scheduler"""
    scheduler = setup_automated_sync()
    
    while True:
        scheduler.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # Test database sync
    print("Testing Database Sync...")
    print("=" * 40)
    
    sync_tool = DatabaseSyncTool()
    
    # Test invoice sync
    print("\n1. Testing invoice sync...")
    result = sync_tool._run("invoices", "7d", force_refresh=True)
    print(f"Result: {result}")
    
    # Test full sync
    print("\n2. Testing full sync...")
    result = sync_tool._run("full", "7d", force_refresh=True)
    print(f"Result: {result}")
    
    print("\n" + "=" * 40)
    print("Database Sync Test Complete")
    print("=" * 40)

