"""
Logging Decorators for AI Agent
Automatically log agent actions, tool usage, and performance metrics
"""

import time
import functools
import traceback
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from .logger import get_agent_logger

def log_agent_action(action_name: str = None):
    """
    Decorator to log AI agent actions with timing and context
    
    Usage:
        @log_agent_action("payment_matching")
        def match_payment(payment_data):
            # function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            action = action_name or func.__name__
            
            start_time = time.time()
            
            try:
                # Log the action start
                logger.log_agent_action(
                    action=action,
                    tool=func.__module__,
                    input_data={"args": str(args), "kwargs": kwargs},
                    output_data={},
                    reasoning=f"Starting {action}"
                )
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the successful completion
                logger.log_agent_action(
                    action=action,
                    tool=func.__module__,
                    input_data={"args": str(args), "kwargs": kwargs},
                    output_data={"result": str(result)},
                    reasoning=f"Completed {action} successfully"
                )
                
                # Log performance metric
                logger.log_performance_metric(
                    metric_name=f"{action}_duration",
                    value=duration_ms,
                    unit="milliseconds",
                    context={"function": func.__name__, "module": func.__module__}
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the error
                logger.log_error(
                    error_type=f"{action}_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={
                        "function": func.__name__,
                        "module": func.__module__,
                        "args": str(args),
                        "kwargs": kwargs,
                        "duration_ms": duration_ms
                    }
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

def log_tool_usage(tool_name: str = None):
    """
    Decorator to log tool usage with input/output and performance
    
    Usage:
        @log_tool_usage("xero_invoice_tool")
        def get_invoices(tenant_id):
            # tool implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            tool = tool_name or func.__name__
            
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the tool usage
                logger.log_agent_action(
                    action="tool_usage",
                    tool=tool,
                    input_data={"args": str(args), "kwargs": kwargs},
                    output_data={"result": str(result)},
                    reasoning=f"Tool {tool} executed successfully"
                )
                
                # Log performance metric
                logger.log_performance_metric(
                    metric_name=f"{tool}_duration",
                    value=duration_ms,
                    unit="milliseconds",
                    context={"tool": tool, "function": func.__name__}
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the error
                logger.log_error(
                    error_type=f"{tool}_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={
                        "tool": tool,
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs,
                        "duration_ms": duration_ms
                    }
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

def log_financial_operation(operation_type: str):
    """
    Decorator to log financial operations for audit trail
    
    Usage:
        @log_financial_operation("payment_application")
        def apply_payment(payment_id, invoice_id):
            # financial operation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract financial details from result if possible
                amount = None
                currency = "USD"
                reference = None
                
                if isinstance(result, dict):
                    amount = result.get('amount')
                    currency = result.get('currency', 'USD')
                    reference = result.get('reference') or result.get('id')
                
                # Log the financial operation
                logger.log_financial_operation(
                    operation_type=operation_type,
                    amount=amount or 0.0,
                    currency=currency,
                    reference=reference or f"{func.__name__}_{int(time.time())}",
                    status="success",
                    details={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs,
                        "result": str(result),
                        "duration_ms": duration_ms
                    }
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the failed financial operation
                logger.log_financial_operation(
                    operation_type=operation_type,
                    amount=0.0,
                    currency="USD",
                    reference=f"{func.__name__}_{int(time.time())}",
                    status="failed",
                    details={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs,
                        "error": str(e),
                        "duration_ms": duration_ms
                    }
                )
                
                # Log the error
                logger.log_error(
                    error_type=f"{operation_type}_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={
                        "operation_type": operation_type,
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs
                    }
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

def log_human_interaction(interaction_type: str):
    """
    Decorator to log human interactions with the system
    
    Usage:
        @log_human_interaction("job_approval")
        def approve_job(job_id, user_id):
            # approval logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract user and job info from args/kwargs
                user_id = kwargs.get('user_id') or 'unknown'
                job_id = kwargs.get('job_id') or 'unknown'
                
                # Log the human interaction
                logger.log_human_interaction(
                    interaction_type=interaction_type,
                    user_id=user_id,
                    job_id=job_id,
                    action=func.__name__,
                    details={
                        "args": str(args),
                        "kwargs": kwargs,
                        "result": str(result),
                        "duration_ms": duration_ms
                    }
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the error
                logger.log_error(
                    error_type=f"{interaction_type}_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={
                        "interaction_type": interaction_type,
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs
                    }
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

def log_api_call(api_name: str):
    """
    Decorator to log API calls with timing and response details
    
    Usage:
        @log_api_call("xero_api")
        def get_xero_invoices(tenant_id):
            # API call implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the API call
                logger.log_api_call(
                    api_name=api_name,
                    endpoint=func.__name__,
                    method="GET",  # Could be extracted from function or args
                    request_data={"args": str(args), "kwargs": kwargs},
                    response_data={"result": str(result)},
                    status_code=200,  # Could be extracted from result
                    duration_ms=duration_ms
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the failed API call
                logger.log_api_call(
                    api_name=api_name,
                    endpoint=func.__name__,
                    method="GET",
                    request_data={"args": str(args), "kwargs": kwargs},
                    response_data={"error": str(e)},
                    status_code=500,
                    duration_ms=duration_ms
                )
                
                # Log the error
                logger.log_error(
                    error_type=f"{api_name}_api_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={
                        "api_name": api_name,
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs
                    }
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

def log_database_operation(table_name: str = None):
    """
    Decorator to log database operations
    
    Usage:
        @log_database_operation("invoices")
        def update_invoice(invoice_id, data):
            # database operation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            table = table_name or "unknown"
            
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the database operation
                logger.log_database_operation(
                    operation=func.__name__,
                    table=table,
                    records_affected=1,  # Could be extracted from result
                    duration_ms=duration_ms,
                    details={
                        "args": str(args),
                        "kwargs": kwargs,
                        "result": str(result)
                    }
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log the error
                logger.log_error(
                    error_type=f"database_{table}_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    context={
                        "table": table,
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": kwargs
                    }
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator
