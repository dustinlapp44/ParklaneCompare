"""
Web Dashboard for AI Agent Human-in-the-Loop Review
Provides job management, chat interface, and approval workflow
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
import time

# Import AI agent components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agent.core_agent import PropertyManagementAgent
from agent.llm_setup import setup_llm_for_agent
from sync_manager import get_sync_manager, start_sync_manager, stop_sync_manager
from utils.logger import get_agent_logger
from utils.logging_decorators import log_human_interaction

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

class Job:
    """Represents a job that needs human review"""
    
    def __init__(self, job_id: str, job_type: str, data: Dict[str, Any], 
                 confidence: float, reasoning: str, recommendations: List[str]):
        self.job_id = job_id
        self.job_type = job_type
        self.data = data
        self.confidence = confidence
        self.reasoning = reasoning
        self.recommendations = recommendations
        self.status = "pending"  # pending, completed, needs_review, failed, skipped, in_progress
        self.created_at = datetime.now()
        self.reviewed_at = None
        self.reviewed_by = None
        self.notes = ""
        self.chat_messages = []
    
    def to_dict(self):
        """Convert job to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'data': self.data,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'recommendations': self.recommendations,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by,
            'notes': self.notes,
            'chat_messages': self.chat_messages
        }

# Global variables
agent = None
llm = None
pending_jobs = []
job_history = []
chat_messages = []
agent_logger = get_agent_logger()

# Load sample jobs for testing
def load_sample_jobs():
    """Load sample jobs for testing"""
    try:
        sample_jobs_file = os.path.join(project_root, "ai_agent", "data", "sample_data", "sample_jobs.json")
        if os.path.exists(sample_jobs_file):
            with open(sample_jobs_file, 'r') as f:
                sample_jobs = json.load(f)
            
            # Convert to Job objects
            for job_data in sample_jobs:
                job = Job(
                    job_id=job_data['job_id'],
                    job_type=job_data['job_type'],
                    data=job_data['data'],
                    confidence=job_data['confidence'],
                    reasoning=job_data['reasoning'],
                    recommendations=job_data['recommendations']
                )
                job.status = job_data['status']
                job.created_at = datetime.fromisoformat(job_data['created_at'])
                job.chat_messages = job_data.get('chat_messages', [])
                pending_jobs.append(job)
            
            print(f"✅ Loaded {len(sample_jobs)} sample jobs")
        else:
            print("⚠️ No sample jobs file found")
    except Exception as e:
        print(f"❌ Error loading sample jobs: {e}")

# Load sample jobs on startup
# load_sample_jobs()  # Commented out for now

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/jobs')
def get_jobs():
    """Get all pending jobs"""
    return jsonify({
        'pending': [job.to_dict() for job in pending_jobs if job.status == "pending"],
        'in_progress': [job.to_dict() for job in pending_jobs if job.status == "in_progress"],
        'completed': [job.to_dict() for job in job_history[-10:]]  # Last 10 completed jobs
    })

@app.route('/api/jobs/<job_id>')
def get_job(job_id):
    """Get specific job details"""
    job = next((j for j in pending_jobs + job_history if j.job_id == job_id), None)
    if job:
        return jsonify(job.to_dict())
    return jsonify({'error': 'Job not found'}), 404

@app.route('/api/jobs/<job_id>/apply-payment', methods=['POST'])
@log_human_interaction("payment_application")
def apply_payment(job_id):
    """Apply payment to Xero (previously 'approve')"""
    job = next((j for j in pending_jobs if j.job_id == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    job.status = "completed"
    job.reviewed_at = datetime.now()
    job.reviewed_by = data.get('reviewer', 'Unknown')
    job.notes = data.get('notes', '')
    
    # Log the human interaction
    agent_logger.log_human_interaction(
        interaction_type="payment_application",
        user_id=data.get('reviewer', 'Unknown'),
        job_id=job_id,
        action="apply_payment",
        details={
            "job_type": job.job_type,
            "confidence": job.confidence,
            "notes": job.notes,
            "ip_address": request.remote_addr
        }
    )
    
    # Actually apply the payment to Xero
    try:
        if job.job_type == "payment_matching" and "payment" in job.data and "applied_invoice" in job.data:
            payment = job.data["payment"]
            invoice = job.data["applied_invoice"]
            
            # Apply payment using XeroClient
            from XeroClient.xero_client import apply_payment
            
            payment_data = {
                "InvoiceID": invoice.get("InvoiceID"),
                "Amount": payment.get("amount"),
                "Date": payment.get("date"),
                "Reference": payment.get("ref", "Aptexx Payment"),
                "ContactName": payment.get("person")
            }
            
            result = apply_payment(payment_data)
            
            if result.get("success"):
                job.notes += f"\n✅ Payment successfully applied to Xero: {result.get('message', '')}"
                agent_logger.log_financial_operation(
                    operation_type="payment_applied",
                    amount=payment.get("amount"),
                    invoice_id=invoice.get("InvoiceID"),
                    tenant_name=payment.get("person"),
                    success=True,
                    details=result
                )
            else:
                job.notes += f"\n❌ Failed to apply payment: {result.get('error', 'Unknown error')}"
                job.status = "failed"
                agent_logger.log_financial_operation(
                    operation_type="payment_application_failed",
                    amount=payment.get("amount"),
                    invoice_id=invoice.get("InvoiceID"),
                    tenant_name=payment.get("person"),
                    success=False,
                    details=result
                )
        else:
            job.notes += "\n⚠️ Cannot apply payment - missing required data"
            job.status = "failed"
            
    except Exception as e:
        job.notes += f"\n❌ Error applying payment: {str(e)}"
        job.status = "failed"
        agent_logger.log_financial_operation(
            operation_type="payment_application_error",
            amount=job.data.get("payment", {}).get("amount", 0),
            invoice_id=job.data.get("applied_invoice", {}).get("InvoiceID", "Unknown"),
            tenant_name=job.data.get("payment", {}).get("person", "Unknown"),
            success=False,
            details={"error": str(e)}
        )
    
    # Move to history
    pending_jobs.remove(job)
    job_history.append(job)
    
    # Emit to all clients
    socketio.emit('job_updated', job.to_dict())
    
    return jsonify({'success': True, 'job': job.to_dict()})

@app.route('/api/jobs/<job_id>/flag-for-review', methods=['POST'])
@log_human_interaction("job_flagging")
def flag_for_review(job_id):
    """Flag job for manual review (previously 'reject')"""
    job = next((j for j in pending_jobs if j.job_id == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    job.status = "needs_review"
    job.reviewed_at = datetime.now()
    job.reviewed_by = data.get('reviewer', 'Unknown')
    job.notes = data.get('notes', '')
    
    # Log the human interaction
    agent_logger.log_human_interaction(
        interaction_type="job_flagging",
        user_id=data.get('reviewer', 'Unknown'),
        job_id=job_id,
        action="flag_for_review",
        details={
            "job_type": job.job_type,
            "confidence": job.confidence,
            "notes": job.notes,
            "ip_address": request.remote_addr
        }
    )
    
    # Keep job in pending list but mark as needing review
    # Emit to all clients
    socketio.emit('job_updated', job.to_dict())
    
    return jsonify({'success': True, 'job': job.to_dict()})

@app.route('/api/jobs/<job_id>/skip', methods=['POST'])
@log_human_interaction("job_skipping")
def skip_job(job_id):
    """Skip this job (for duplicate payments, etc.)"""
    job = next((j for j in pending_jobs if j.job_id == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    job.status = "skipped"
    job.reviewed_at = datetime.now()
    job.reviewed_by = data.get('reviewer', 'Unknown')
    job.notes = data.get('notes', 'Skipped by user')
    
    # Log the human interaction
    agent_logger.log_human_interaction(
        interaction_type="job_skipping",
        user_id=data.get('reviewer', 'Unknown'),
        job_id=job_id,
        action="skip",
        details={
            "job_type": job.job_type,
            "confidence": job.confidence,
            "notes": job.notes,
            "ip_address": request.remote_addr
        }
    )
    
    # Move to history
    pending_jobs.remove(job)
    job_history.append(job)
    
    # Emit to all clients
    socketio.emit('job_updated', job.to_dict())
    
    return jsonify({'success': True, 'job': job.to_dict()})

@app.route('/api/jobs/<job_id>/chat', methods=['POST'])
def add_chat_message(job_id):
    """Add a chat message to a job"""
    job = next((j for j in pending_jobs if j.job_id == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    message = {
        'id': len(job.chat_messages) + 1,
        'sender': data.get('sender', 'Human'),
        'message': data.get('message', ''),
        'timestamp': datetime.now().isoformat()
    }
    
    job.chat_messages.append(message)
    
    # Emit to all clients
    socketio.emit('chat_message', {
        'job_id': job_id,
        'message': message
    })
    
    # If human sent message, get AI response
    if message['sender'] == 'Human':
        ai_response = get_ai_response(job, message['message'])
        if ai_response:
            ai_message = {
                'id': len(job.chat_messages) + 1,
                'sender': 'AI Agent',
                'message': ai_response,
                'timestamp': datetime.now().isoformat()
            }
            job.chat_messages.append(ai_message)
            
            socketio.emit('chat_message', {
                'job_id': job_id,
                'message': ai_message
            })
    
    return jsonify({'success': True, 'message': message})

@app.route('/api/chat', methods=['POST'])
def general_chat():
    """Handle general chat messages (not job-specific)"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get AI response for general questions
        ai_response = get_ai_response(None, message)
        
        return jsonify({
            'success': True,
            'response': ai_response or "I'm here to help! You can ask me about the AI agent, jobs, or any questions about the system."
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    """Get dashboard statistics"""
    stats = {
        'pending_jobs': len([j for j in pending_jobs if j.status == "pending"]),
        'in_progress_jobs': len([j for j in pending_jobs if j.status == "in_progress"]),
        'completed_today': len([j for j in job_history if j.reviewed_at and j.reviewed_at.date() == datetime.now().date()]),
        'total_completed': len(job_history),
        'avg_confidence': sum(j.confidence for j in pending_jobs) / len(pending_jobs) if pending_jobs else 0,
        'job_types': {}
    }
    
    # Count job types
    for job in pending_jobs:
        stats['job_types'][job.job_type] = stats['job_types'].get(job.job_type, 0) + 1
    
    return jsonify(stats)

@app.route('/api/sync/status')
def get_sync_status():
    """Get database sync status"""
    try:
        sync_manager = get_sync_manager()
        status = sync_manager.get_sync_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/stats')
def get_database_stats():
    """Get database statistics"""
    try:
        import sqlite3
        import os
        
        db_path = '/tmp/payments.db'
        
        if not os.path.exists(db_path):
            return jsonify({
                'error': 'Database not found',
                'invoices': 0,
                'payments': 0,
                'payment_tracking': 0,
                'sync_log': 0
            })
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get counts for each table
        stats = {}
        
        # Check invoices table
        try:
            cursor.execute('SELECT COUNT(*) FROM invoices')
            stats['invoices'] = cursor.fetchone()[0]
        except:
            stats['invoices'] = 0
        
        # Check payments table
        try:
            cursor.execute('SELECT COUNT(*) FROM payments')
            stats['payments'] = cursor.fetchone()[0]
        except:
            stats['payments'] = 0
        
        # Check payment_tracking table
        try:
            cursor.execute('SELECT COUNT(*) FROM payment_tracking')
            stats['payment_tracking'] = cursor.fetchone()[0]
        except:
            stats['payment_tracking'] = 0
        
        # Check sync_log table
        try:
            cursor.execute('SELECT COUNT(*) FROM sync_log')
            stats['sync_log'] = cursor.fetchone()[0]
        except:
            stats['sync_log'] = 0
        
        # Get some additional stats
        try:
            # Count unpaid invoices
            cursor.execute('SELECT COUNT(*) FROM invoices WHERE status != "PAID"')
            stats['unpaid_invoices'] = cursor.fetchone()[0]
        except:
            stats['unpaid_invoices'] = 0
        
        try:
            # Count paid invoices
            cursor.execute('SELECT COUNT(*) FROM invoices WHERE status = "PAID"')
            stats['paid_invoices'] = cursor.fetchone()[0]
        except:
            stats['paid_invoices'] = 0
        
        try:
            # Get total amount of unpaid invoices
            cursor.execute('SELECT SUM(amount_due) FROM invoices WHERE status != "PAID" AND amount_due > 0')
            result = cursor.fetchone()[0]
            stats['total_unpaid_amount'] = float(result) if result else 0.0
        except:
            stats['total_unpaid_amount'] = 0.0
        
        conn.close()
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/start', methods=['POST'])
def start_sync():
    """Start background sync"""
    try:
        data = request.get_json()
        interval_hours = data.get('interval_hours', 6) if data else 6
        
        sync_manager = start_sync_manager(interval_hours)
        return jsonify({'status': 'success', 'message': f'Sync started with {interval_hours} hour interval'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/stop', methods=['POST'])
def stop_sync():
    """Stop background sync"""
    try:
        stop_sync_manager()
        return jsonify({'status': 'success', 'message': 'Sync stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/force', methods=['POST'])
def force_sync():
    """Force an immediate sync"""
    try:
        data = request.get_json() or {}
        date_range_days = data.get('date_range_days', 90)  # Default to 90 days
        
        sync_manager = get_sync_manager()
        sync_manager.force_sync_now(date_range_days=date_range_days)
        return jsonify({'status': 'success', 'message': f'Force sync initiated for last {date_range_days} days'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/config', methods=['GET'])
def get_sync_config():
    """Get current sync configuration"""
    try:
        sync_manager = get_sync_manager()
        return jsonify({
            'sync_interval_hours': sync_manager.sync_interval_hours,
            'default_date_range_days': 90,
            'is_running': sync_manager.is_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Email Automation Endpoints
@app.route('/api/email/check', methods=['POST'])
def check_emails():
    """Check for new Aptexx emails"""
    try:
        from email_automation import EmailAutomation
        from agent.tools.google_tools import GmailFetchTool
        from agent.tools.email_tools import EmailParsingTool
        from agent.tools.payment_matching_tools import PaymentMatchingTool
        
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        check_unprocessed_only = data.get('check_unprocessed_only', True)
        
        # Initialize tools
        gmail_tool = GmailFetchTool()
        email_parser = EmailParsingTool()
        payment_matcher = PaymentMatchingTool()
        
        # Fetch emails
        email_result = gmail_tool._run(
            start_date=start_date,
            end_date=end_date,
            sender="aptexx",
            check_unprocessed_only=check_unprocessed_only
        )
        
        if not email_result.get("success", False):
            return jsonify({
                'status': 'error',
                'error': email_result.get('error', 'Unknown error')
            }), 500
        
        emails = email_result.get("emails", [])
        
        if not emails:
            return jsonify({
                'status': 'success',
                'result': {
                    'success': True,
                    'emails_processed': 0,
                    'payments_processed': 0,
                    'message': 'No emails found in date range',
                    'timestamp': datetime.now().isoformat()
                }
            })
        
        # Process each email
        total_payments = 0
        processed_payments = 0
        matching_results = []
        
        for email in emails:
            try:
                # Parse email to extract payment data
                parse_result = email_parser._run(
                    email_content=email.get('html', email.get('plain', '')),
                    email_source=f"{email.get('subject', '')}_{email.get('date', '')}",
                    save_raw_data=True,
                    validate_parsing=True
                )
                
                if not parse_result.get("success", False):
                    continue
                
                payments = parse_result.get("parsed_payments", [])
                total_payments += len(payments)
                
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
                        
                        matching_results.append({
                            'payment': payment,
                            'match_result': match_result
                        })
                        
                        if match_result.get("success", False):
                            processed_payments += 1
                        
                    except Exception as e:
                        print(f"Error processing payment: {e}")
                
            except Exception as e:
                print(f"Error processing email: {e}")
        
        result = {
            'success': True,
            'emails_processed': len(emails),
            'payments_processed': processed_payments,
            'total_payments_found': total_payments,
            'matching_results': matching_results,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/status', methods=['GET'])
def email_status():
    """Get email automation status"""
    try:
        # Check if email automation is running
        # For now, just return basic status
        return jsonify({
            'status': 'available',
            'last_check': None,
            'processed_count': 0,
            'message': 'Email automation ready'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_job(job_type: str, data: Dict[str, Any], confidence: float, 
               reasoning: str, recommendations: List[str]) -> Job:
    """Create a new job for human review"""
    job_id = f"job_{int(time.time())}_{len(pending_jobs)}"
    job = Job(job_id, job_type, data, confidence, reasoning, recommendations)
    pending_jobs.append(job)
    
    # Emit to all connected clients
    socketio.emit('new_job', job.to_dict())
    
    return job

def notify_agent_approval(job: Job):
    """Notify AI agent when job is approved"""
    if agent:
        try:
            # Update agent with approval decision
            agent.agent_executor.invoke({
                "input": f"Job {job.job_id} was approved by {job.reviewed_by}. Notes: {job.notes}"
            })
        except Exception as e:
            logging.error(f"Error notifying agent of approval: {e}")

def notify_agent_rejection(job: Job):
    """Notify AI agent when job is rejected"""
    if agent:
        try:
            # Update agent with rejection decision
            agent.agent_executor.invoke({
                "input": f"Job {job.job_id} was rejected by {job.reviewed_by}. Notes: {job.notes}"
            })
        except Exception as e:
            logging.error(f"Error notifying agent of rejection: {e}")

def emit_sync_log(message: str, log_type: str = "info"):
    """Emit sync log message to all connected clients"""
    try:
        # Use Flask app context to ensure SocketIO works properly
        with app.app_context():
            socketio.emit('sync_log', {
                'message': message,
                'type': log_type,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        logging.error(f"Error emitting sync log: {e}")
        # Fallback to console logging
        print(f"[{log_type.upper()}] {message}")

def get_ai_response(job: Optional[Job], human_message: str) -> Optional[str]:
    """Get AI response to human chat message"""
    if agent and agent.agent_executor:
        try:
            if job:
                # Format job data for better readability
                formatted_data = ""
                if job.data:
                    if "payment" in job.data:
                        payment = job.data["payment"]
                        formatted_data += f"Payment: ${payment.get('amount', 'N/A')} from {payment.get('person', 'Unknown')}\n"
                        if "property" in payment:
                            formatted_data += f"Property: {payment['property']}\n"
                        if "ref" in payment:
                            formatted_data += f"Reference: {payment['ref']}\n"
                    
                    if "available_invoices" in job.data:
                        invoices = job.data["available_invoices"]
                        formatted_data += f"\nAvailable Invoices:\n"
                        for i, inv in enumerate(invoices, 1):
                            formatted_data += f"  {i}. {inv.get('InvoiceID', 'N/A')} - ${inv.get('AmountDue', 'N/A')} ({inv.get('ContactName', 'Unknown')})\n"
                    
                    if "applied_invoice" in job.data:
                        applied = job.data["applied_invoice"]
                        formatted_data += f"\nApplied to: {applied.get('InvoiceID', 'N/A')}\n"
                
                # Job-specific response context
                context = f"""
                You are an AI assistant helping with a property management job review.
                
                Job Type: {job.job_type}
                Confidence: {job.confidence:.0%}
                Reasoning: {job.reasoning}
                Recommendations: {', '.join(job.recommendations)}
                
                Job Details:
                {formatted_data}
                
                Human Question: {human_message}
                
                Provide a clear, helpful response. If showing data, format it nicely for readability.
                Keep responses concise and focused on the specific question.
                """
            else:
                # General response - include job data
                pending_count = len([j for j in pending_jobs if j.status == "pending"])
                in_progress_count = len([j for j in pending_jobs if j.status == "in_progress"])
                
                context = f"""
                You are an AI assistant for a property management system that handles payment reconciliation.
                The system processes payments from Aptexx and matches them to invoices in Xero.
                
                Current job status:
                - Pending jobs: {pending_count}
                - In progress jobs: {in_progress_count}
                
                Human Question: {human_message}
                
                Provide a concise, helpful response. If asked about jobs, use the actual numbers above.
                Keep responses brief and to the point.
                """
            
            # Use simple LLM call instead of agent_executor to avoid function calling issues
            try:
                response = llm.invoke(context)
                return str(response) if response else 'I understand your question. Let me help you with this.'
            except Exception as llm_error:
                logging.error(f"LLM call error: {llm_error}")
                # Fall back to simple text generation
                return 'I understand your question. Let me help you with this.'
            
        except Exception as e:
            logging.error(f"Error getting AI response: {e}")
            return "I'm having trouble processing your question right now. Please try again."
    else:
        # Smart fallback responses
        if job:
            # Job-specific fallback responses
            question_lower = human_message.lower()
            
            if "why" in question_lower or "reason" in question_lower:
                return f"This job was flagged for review because: {job.reasoning}"
            elif "confidence" in question_lower or "sure" in question_lower:
                return f"The confidence level is {job.confidence:.0%}. This means the AI is {job.confidence:.0%} confident about this match. Lower confidence jobs need human review to ensure accuracy."
            elif "recommend" in question_lower or "suggest" in question_lower:
                return f"Here are the recommendations: {'; '.join(job.recommendations)}"
            elif "data" in question_lower or "info" in question_lower:
                if job.job_type == "payment_matching":
                    payment = job.data.get('payment', {})
                    result = f"Payment: ${payment.get('amount', 0)} from {payment.get('person', 'Unknown')}\n"
                    result += f"Property: {payment.get('property', 'Unknown')}\n"
                    result += f"Reference: {payment.get('ref', 'N/A')}"
                    
                    if "available_invoices" in job.data:
                        invoices = job.data["available_invoices"]
                        result += f"\n\nAvailable Invoices:"
                        for i, inv in enumerate(invoices, 1):
                            result += f"\n  {i}. {inv.get('InvoiceID', 'N/A')} - ${inv.get('AmountDue', 'N/A')} ({inv.get('ContactName', 'Unknown')})"
                    
                    if "applied_invoice" in job.data:
                        applied = job.data["applied_invoice"]
                        result += f"\n\nApplied to: {applied.get('InvoiceID', 'N/A')}"
                    
                    return result
                elif job.job_type == "name_matching":
                    return f"Payment name: {job.data.get('payment_name', 'Unknown')}. Available tenants: {', '.join(job.data.get('available_tenants', []))}"
                else:
                    return f"Job data: {json.dumps(job.data, indent=2)}"
            else:
                return f"I can help you with this {job.job_type} job. The confidence level is {job.confidence:.0%}. What specific information would you like to know about the reasoning, recommendations, or data?"
        else:
            # General fallback responses - check actual data
            question_lower = human_message.lower()
            
            # Check for job-related questions
            if any(word in question_lower for word in ["job", "pending", "open", "review", "queue"]):
                pending_count = len([j for j in pending_jobs if j.status == "pending"])
                in_progress_count = len([j for j in pending_jobs if j.status == "in_progress"])
                
                if pending_count > 0 or in_progress_count > 0:
                    return f"There are {pending_count} pending jobs and {in_progress_count} in progress jobs that need review."
                else:
                    return "No jobs currently need review."
            
            elif "ai" in question_lower or "agent" in question_lower:
                return "I'm an AI agent that automates payment reconciliation between Aptexx and Xero. I flag complex cases for human review."
            elif "payment" in question_lower or "invoice" in question_lower:
                return "The system processes Aptexx payments and matches them to Xero invoices. Complex cases are flagged for review."
            elif "dashboard" in question_lower or "interface" in question_lower:
                return "This dashboard shows jobs needing review. You can approve/reject recommendations and chat with me about cases."
            elif "help" in question_lower:
                return "I can help with: job reviews, payment matching, system questions, and specific case analysis."
            else:
                return "I help with property management payment reconciliation. Ask about jobs, payments, or the system."

def initialize_agent():
    """Initialize the AI agent"""
    global agent, llm
    
    try:
        print("🤖 Initializing AI Agent...")
        # Setup LLM
        llm = setup_llm_for_agent(
            base_url="http://192.168.86.53:11434",
            model_name="llama3",
            temperature=0.1
        )
        
        if llm:
            # Initialize agent with reduced verbosity
            agent = PropertyManagementAgent(verbose=False)  # Reduced verbosity
            agent.set_llm(llm)
            print("✅ AI Agent initialized successfully")
        else:
            print("❌ Failed to initialize LLM")
            
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_job')
def handle_join_job(data):
    """Join a job room for real-time updates"""
    job_id = data.get('job_id')
    if job_id:
        join_room(f"job_{job_id}")
        emit('joined_job', {'job_id': job_id})

@socketio.on('leave_job')
def handle_leave_job(data):
    """Leave a job room"""
    job_id = data.get('job_id')
    if job_id:
        leave_room(f"job_{job_id}")
        emit('left_job', {'job_id': job_id})

if __name__ == '__main__':
    # Initialize agent in background thread with delay
    def init_agent_thread():
        time.sleep(5)  # Wait 5 seconds before initializing agent
        initialize_agent()
    
    threading.Thread(target=init_agent_thread, daemon=True).start()
    
    print("🚀 Starting AI Agent Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🤖 AI Agent will initialize in the background...")
    
    # Run the web server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # Disable debug mode for better performance
