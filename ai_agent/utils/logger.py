"""
Comprehensive Logging System for AI Agent
Provides structured logging for all agent actions, decisions, and system operations
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class AgentLogger:
    """
    Comprehensive logging system for AI agent operations
    Provides separate log files for different types of operations
    """
    
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize different loggers
        self.system_logger = self._setup_system_logger()
        self.agent_logger = self._setup_agent_logger()
        self.audit_logger = self._setup_audit_logger()
        self.security_logger = self._setup_security_logger()
        self.performance_logger = self._setup_performance_logger()
        
    def _setup_system_logger(self) -> logging.Logger:
        """Setup system operations logger"""
        logger = logging.getLogger("ai_agent.system")
        logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
            
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "system.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_agent_logger(self) -> logging.Logger:
        """Setup AI agent actions logger"""
        logger = logging.getLogger("ai_agent.actions")
        logger.setLevel(logging.INFO)
        
        if logger.handlers:
            return logger
            
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "agent_actions.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Setup audit trail logger for financial operations"""
        logger = logging.getLogger("ai_agent.audit")
        logger.setLevel(logging.INFO)
        
        if logger.handlers:
            return logger
            
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "audit_trail.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10  # Keep more audit logs
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_security_logger(self) -> logging.Logger:
        """Setup security events logger"""
        logger = logging.getLogger("ai_agent.security")
        logger.setLevel(logging.INFO)
        
        if logger.handlers:
            return logger
            
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "security.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_performance_logger(self) -> logging.Logger:
        """Setup performance metrics logger"""
        logger = logging.getLogger("ai_agent.performance")
        logger.setLevel(logging.INFO)
        
        if logger.handlers:
            return logger
            
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "performance.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - PERFORMANCE - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None):
        """Log system-level events"""
        message = f"SYSTEM_EVENT: {event}"
        if details:
            message += f" - {json.dumps(details, default=str)}"
        self.system_logger.info(message)
    
    def log_agent_action(self, action: str, tool: str, input_data: Dict[str, Any], 
                        output_data: Dict[str, Any], confidence: Optional[float] = None,
                        reasoning: Optional[str] = None):
        """Log AI agent actions with full context"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "tool": tool,
            "input": input_data,
            "output": output_data,
            "confidence": confidence,
            "reasoning": reasoning
        }
        
        self.agent_logger.info(f"AGENT_ACTION: {json.dumps(log_entry, default=str)}")
    
    def log_agent_decision(self, decision_type: str, context: Dict[str, Any], 
                          decision: Dict[str, Any], confidence: float):
        """Log AI agent decisions"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "decision_type": decision_type,
            "context": context,
            "decision": decision,
            "confidence": confidence
        }
        
        self.agent_logger.info(f"AGENT_DECISION: {json.dumps(log_entry, default=str)}")
    
    def log_financial_operation(self, operation_type: str, amount: float, 
                               currency: str, reference: str, status: str,
                               details: Dict[str, Any]):
        """Log financial operations for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "amount": amount,
            "currency": currency,
            "reference": reference,
            "status": status,
            "details": details
        }
        
        self.audit_logger.info(f"FINANCIAL_OPERATION: {json.dumps(log_entry, default=str)}")
    
    def log_payment_matching(self, payment_data: Dict[str, Any], 
                           matched_invoices: list, confidence: float,
                           decision: str, human_approved: bool = False):
        """Log payment matching operations"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "payment_data": payment_data,
            "matched_invoices": matched_invoices,
            "confidence": confidence,
            "decision": decision,
            "human_approved": human_approved
        }
        
        self.audit_logger.info(f"PAYMENT_MATCHING: {json.dumps(log_entry, default=str)}")
    
    def log_human_interaction(self, interaction_type: str, user_id: str,
                            job_id: str, action: str, details: Dict[str, Any]):
        """Log human interactions with the system"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "interaction_type": interaction_type,
            "user_id": user_id,
            "job_id": job_id,
            "action": action,
            "details": details
        }
        
        self.audit_logger.info(f"HUMAN_INTERACTION: {json.dumps(log_entry, default=str)}")
    
    def log_security_event(self, event_type: str, severity: str, 
                          user_id: Optional[str] = None, ip_address: Optional[str] = None,
                          details: Dict[str, Any] = None):
        """Log security-related events"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {}
        }
        
        self.security_logger.warning(f"SECURITY_EVENT: {json.dumps(log_entry, default=str)}")
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              unit: str, context: Dict[str, Any] = None):
        """Log performance metrics"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "context": context or {}
        }
        
        self.performance_logger.info(f"PERFORMANCE_METRIC: {json.dumps(log_entry, default=str)}")
    
    def log_error(self, error_type: str, error_message: str, 
                  stack_trace: Optional[str] = None, context: Dict[str, Any] = None):
        """Log errors with full context"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "context": context or {}
        }
        
        self.system_logger.error(f"ERROR: {json.dumps(log_entry, default=str)}")
    
    def log_api_call(self, api_name: str, endpoint: str, method: str,
                     request_data: Dict[str, Any], response_data: Dict[str, Any],
                     status_code: int, duration_ms: float):
        """Log API calls for monitoring"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "api_name": api_name,
            "endpoint": endpoint,
            "method": method,
            "request_data": request_data,
            "response_data": response_data,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        
        self.system_logger.info(f"API_CALL: {json.dumps(log_entry, default=str)}")
    
    def log_database_operation(self, operation: str, table: str, 
                              records_affected: int, duration_ms: float,
                              details: Dict[str, Any] = None):
        """Log database operations"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "table": table,
            "records_affected": records_affected,
            "duration_ms": duration_ms,
            "details": details or {}
        }
        
        self.system_logger.info(f"DATABASE_OPERATION: {json.dumps(log_entry, default=str)}")
    
    def log_sync_operation(self, sync_type: str, start_time: datetime,
                          end_time: datetime, records_processed: int,
                          success: bool, error_message: Optional[str] = None):
        """Log database synchronization operations"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "sync_type": sync_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "records_processed": records_processed,
            "success": success,
            "error_message": error_message
        }
        
        self.system_logger.info(f"SYNC_OPERATION: {json.dumps(log_entry, default=str)}")

# Global logger instance
_agent_logger = None

def get_agent_logger() -> AgentLogger:
    """Get the global agent logger instance"""
    global _agent_logger
    if _agent_logger is None:
        _agent_logger = AgentLogger()
    return _agent_logger

def setup_logging():
    """Setup the logging system"""
    return get_agent_logger()
