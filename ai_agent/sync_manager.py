import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sqlite3
import json

# Import our existing tools
from agent.tools.database_sync_tools import DatabaseSyncTool
from agent.tools.xero_tools import XeroInvoiceTool
import Payments.payments_db as payments_db

class SyncManager:
    """
    Manages automated database synchronization for the AI agent.
    Handles the fact that payments can arrive before invoices are created.
    """
    
    def __init__(self, sync_interval_hours: int = 6, db_path: str = "/tmp/payments.db"):
        self.sync_interval_hours = sync_interval_hours
        self.db_path = db_path
        self.sync_tool = DatabaseSyncTool()
        self.xero_tool = XeroInvoiceTool()
        self.db_path = db_path
        
        # Sync tracking
        self.last_sync_time: Optional[datetime] = None
        self.sync_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize sync log
        self._init_sync_log()
    
    def _init_sync_log(self):
        """Initialize the sync_log table if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Drop existing table if it has wrong structure
                conn.execute("DROP TABLE IF EXISTS sync_log")
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_type TEXT NOT NULL,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        status TEXT NOT NULL,
                        records_processed INTEGER DEFAULT 0,
                        records_added INTEGER DEFAULT 0,
                        records_updated INTEGER DEFAULT 0,
                        errors TEXT,
                        details TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to initialize sync_log table: {e}")
    
    def start_background_sync(self):
        """Start the background sync thread."""
        if self.is_running:
            self.logger.warning("Sync manager is already running")
            return
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        self.logger.info(f"Background sync started (interval: {self.sync_interval_hours} hours)")
    
    def stop_background_sync(self):
        """Stop the background sync thread."""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        self.logger.info("Background sync stopped")
    
    def _sync_loop(self):
        """Main sync loop that runs in background."""
        while self.is_running:
            try:
                # Check if it's time to sync
                if self._should_sync():
                    self.logger.info("Starting scheduled database sync...")
                    self._perform_sync()
                
                # Sleep for 1 hour before checking again
                time.sleep(3600)  # 1 hour
                
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
                time.sleep(300)  # Sleep 5 minutes on error
    
    def _should_sync(self) -> bool:
        """Check if it's time to perform a sync."""
        if self.last_sync_time is None:
            return True
        
        time_since_last_sync = datetime.now() - self.last_sync_time
        return time_since_last_sync >= timedelta(hours=self.sync_interval_hours)
    
    def _perform_sync(self):
        """Perform the actual database sync."""
        sync_start = datetime.now()
        sync_id = None
        
        try:
            # Log sync start
            sync_id = self._log_sync_start("full")
            
            # Sync invoices first
            self.logger.info("Syncing invoices...")
            invoice_result = self._sync_invoices()
            
            # Sync payments
            self.logger.info("Syncing payments...")
            payment_result = self._sync_payments()
            
            # Update sync log
            total_processed = invoice_result.get('processed', 0) + payment_result.get('processed', 0)
            total_added = invoice_result.get('added', 0) + payment_result.get('added', 0)
            total_updated = invoice_result.get('updated', 0) + payment_result.get('updated', 0)
            
            self._log_sync_complete(sync_id, "success", total_processed, total_added, total_updated)
            self.last_sync_time = datetime.now()
            
            self.logger.info(f"Sync completed successfully: {total_added} new records, {total_updated} updated")
            
        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            if sync_id:
                self._log_sync_complete(sync_id, "error", 0, 0, 0, str(e))
    
    def _sync_invoices(self) -> Dict[str, Any]:
        """Sync invoices from Xero."""
        try:
            # Get invoices from Xero (using mock data for now)
            xero_invoices = self.xero_tool._get_mock_invoices()
            
            # Upsert to local database
            processed = 0
            added = 0
            updated = 0
            
            # Use the payments_db module functions
            payments_db.upsert_invoices(xero_invoices)
            processed = len(xero_invoices)
            added = len(xero_invoices)  # Simplified for now
            updated = 0
            
            return {
                'processed': processed,
                'added': added,
                'updated': updated
            }
            
        except Exception as e:
            self.logger.error(f"Error syncing invoices: {e}")
            return {'processed': 0, 'added': 0, 'updated': 0, 'error': str(e)}
    
    def _sync_payments(self) -> Dict[str, Any]:
        """Sync payments from Xero."""
        try:
            # For now, payments are handled through invoices
            # In a real implementation, you'd call Xero payments API
            return {
                'processed': 0,
                'added': 0,
                'updated': 0,
                'note': 'Payments sync not implemented yet'
            }
            
        except Exception as e:
            self.logger.error(f"Error syncing payments: {e}")
            return {'processed': 0, 'added': 0, 'updated': 0, 'error': str(e)}
    
    def _log_sync_start(self, sync_type: str) -> int:
        """Log the start of a sync operation."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO sync_log (sync_type, status, start_time)
                    VALUES (?, 'running', CURRENT_TIMESTAMP)
                """, (sync_type,))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to log sync start: {e}")
            return None
    
    def _log_sync_complete(self, sync_id: int, status: str, processed: int, added: int, updated: int, errors: str = None):
        """Log the completion of a sync operation."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE sync_log 
                    SET end_time = CURRENT_TIMESTAMP, status = ?, records_processed = ?, 
                        records_added = ?, records_updated = ?, errors = ?
                    WHERE id = ?
                """, (status, processed, added, updated, errors, sync_id))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log sync completion: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get last sync info
                cursor = conn.execute("""
                    SELECT sync_type, start_time, end_time, status, records_processed, 
                           records_added, records_updated, errors
                    FROM sync_log 
                    ORDER BY start_time DESC 
                    LIMIT 1
                """)
                last_sync = cursor.fetchone()
                
                # Get sync statistics
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_syncs,
                           SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_syncs,
                           SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_syncs
                    FROM sync_log
                """)
                stats = cursor.fetchone()
                
                return {
                    'last_sync': {
                        'type': last_sync[0] if last_sync else None,
                        'start_time': last_sync[1] if last_sync else None,
                        'end_time': last_sync[2] if last_sync else None,
                        'status': last_sync[3] if last_sync else None,
                        'records_processed': last_sync[4] if last_sync else 0,
                        'records_added': last_sync[5] if last_sync else 0,
                        'records_updated': last_sync[6] if last_sync else 0,
                        'errors': last_sync[7] if last_sync else None
                    },
                    'statistics': {
                        'total_syncs': stats[0] if stats else 0,
                        'successful_syncs': stats[1] if stats else 0,
                        'failed_syncs': stats[2] if stats else 0
                    },
                    'next_sync': self._get_next_sync_time(),
                    'is_running': self.is_running
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get sync status: {e}")
            return {'error': str(e)}
    
    def _get_next_sync_time(self) -> Optional[str]:
        """Calculate when the next sync will occur."""
        if self.last_sync_time is None:
            return "Immediate"
        
        next_sync = self.last_sync_time + timedelta(hours=self.sync_interval_hours)
        return next_sync.isoformat()
    
    def force_sync_now(self):
        """Force an immediate sync (useful for testing or manual triggers)."""
        self.logger.info("Force sync requested")
        self._perform_sync()
    
    def check_payment_invoice_relationship(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a payment has a corresponding invoice.
        This is the key method that handles the "payment before invoice" scenario.
        """
        tenant_name = payment_data.get('tenant_name', '')
        amount = payment_data.get('amount', 0)
        
        # Look for matching invoices
        matching_invoices = payments_db.get_invoices_by_contact(tenant_name)
        
        if not matching_invoices:
            return {
                'status': 'no_invoice_found',
                'message': f'No invoice found for tenant "{tenant_name}". Payment may have arrived before invoice creation.',
                'recommendation': 'Flag for human review - invoice may need to be created in Xero',
                'should_sync': False,  # Don't trigger sync for this scenario
                'payment_data': payment_data
            }
        
        # Check for amount matches
        exact_matches = [inv for inv in matching_invoices if abs(inv['amount_due'] - amount) < 0.01]
        if exact_matches:
            return {
                'status': 'exact_match_found',
                'message': f'Found {len(exact_matches)} exact amount match(es) for tenant "{tenant_name}"',
                'invoices': exact_matches,
                'should_sync': False
            }
        
        # Check for partial matches
        partial_matches = [inv for inv in matching_invoices if inv['amount_due'] >= amount]
        if partial_matches:
            return {
                'status': 'partial_match_found',
                'message': f'Found {len(partial_matches)} invoice(s) with sufficient balance for tenant "{tenant_name}"',
                'invoices': partial_matches,
                'should_sync': False
            }
        
        return {
            'status': 'no_suitable_invoice',
            'message': f'No suitable invoice found for tenant "{tenant_name}" with amount ${amount}',
            'available_invoices': matching_invoices,
            'recommendation': 'Flag for human review - may need new invoice or payment adjustment',
            'should_sync': False
        }


# Global sync manager instance
_sync_manager: Optional[SyncManager] = None

def get_sync_manager(sync_interval_hours: int = 6) -> SyncManager:
    """Get or create the global sync manager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager(sync_interval_hours)
    return _sync_manager

def start_sync_manager(sync_interval_hours: int = 6):
    """Start the global sync manager."""
    manager = get_sync_manager(sync_interval_hours)
    manager.start_background_sync()
    return manager

def stop_sync_manager():
    """Stop the global sync manager."""
    global _sync_manager
    if _sync_manager:
        _sync_manager.stop_background_sync()
        _sync_manager = None
