"""
Web Dashboard for AI Agent Human-in-the-Loop Review
Provides job management, chat interface, and approval workflow
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Literal

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

# Response template system
class ResponseTemplate:
    """Standardized response templates for consistent AI communication"""
    
    @staticmethod
    def format_payment_summary(payment_data: Dict[str, Any]) -> str:
        """Format payment information consistently"""
        amount = payment_data.get('amount', 0)
        person = payment_data.get('person', 'Unknown')
        property_name = payment_data.get('property', 'Unknown')
        ref = payment_data.get('ref', 'N/A')
        
        return f"**${amount:,.2f}** from **{person}** ({property_name}) - Ref: {ref}"
    
    @staticmethod
    def format_invoice_summary(invoice_data: Dict[str, Any]) -> str:
        """Format invoice information consistently"""
        invoice_id = invoice_data.get('InvoiceID', 'N/A')
        amount_due = invoice_data.get('AmountDue', 0)
        contact_name = invoice_data.get('ContactName', 'Unknown')
        
        return f"**Invoice {invoice_id}** - **${amount_due:,.2f}** ({contact_name})"
    
    @staticmethod
    def format_job_summary(job: 'Job') -> str:
        """Format job summary consistently"""
        payment = job.data.get('payment', {})
        payment_summary = ResponseTemplate.format_payment_summary(payment)
        
        confidence = f"{job.confidence:.0%}"
        issue_type = job.job_type.replace('_', ' ').title()
        
        return f"{payment_summary} - {issue_type} ({confidence} confidence)"
    
    @staticmethod
    def create_simple_response(summary: str, action: str, details: str = "") -> str:
        """Create a simple, standardized response"""
        response = f"**{summary}**\n\n"
        response += f"**Action:** {action}"
        if details:
            response += f"\n\n{details}"
        return response
    
    @staticmethod
    def create_complex_response(summary: str, issue: str, action: str, confidence: float, details: str = "") -> str:
        """Create a complex response with more context"""
        confidence_text = "High" if confidence >= 0.8 else "Medium" if confidence >= 0.6 else "Low"
        response = f"**{summary}**\n\n"
        response += f"**Issue:** {issue}\n"
        response += f"**Action:** {action}\n"
        response += f"**Confidence:** {confidence_text} ({confidence:.0%})"
        if details:
            response += f"\n\n{details}"
        return response

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
        
        # Update email status
        update_email_status(len(emails), processed_payments, emails)
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Global email status tracking
email_status_data = {
    'status': 'ready',
    'last_check': None,
    'emails_processed': 0,
    'payments_processed': 0,
    'last_check_time': None
}

# Global email processing history
email_history = []

@app.route('/api/email/status', methods=['GET'])
def email_status():
    """Get email automation status"""
    try:
        return jsonify({
            'status': email_status_data['status'],
            'last_check': email_status_data['last_check'],
            'emails_processed': email_status_data['emails_processed'],
            'payments_processed': email_status_data['payments_processed'],
            'message': 'Email automation ready'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_email_status(emails_processed: int, payments_processed: int, processed_emails: List[Dict] = None):
    """Update email status after processing"""
    global email_status_data, email_history
    email_status_data.update({
        'status': 'completed',
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'emails_processed': emails_processed,
        'payments_processed': payments_processed,
        'last_check_time': datetime.now().isoformat()
    })
    
    # Add to email history
    if processed_emails:
        for email in processed_emails:
            email_history.append({
                'subject': email.get('subject', 'Unknown'),
                'date': email.get('date', 'Unknown'),
                'processed_at': datetime.now().isoformat(),
                'status': 'processed'
            })
        
        # Keep only last 100 entries
        if len(email_history) > 100:
            email_history[:] = email_history[-100:]

@app.route('/api/email/history', methods=['GET'])
def email_history_endpoint():
    """Get email processing history from processed emails file"""
    try:
        # Load from the processed emails JSON file
        processed_emails_path = os.path.join(project_root, "ai_agent", "data", "processed_emails.json")
        
        if os.path.exists(processed_emails_path):
            with open(processed_emails_path, 'r') as f:
                data = json.load(f)
                processed_emails = data.get("processed_emails", [])
            
            # Convert to history format
            history = []
            for email_id in processed_emails:
                # Parse email_id format: "subject_date"
                if '_' in email_id:
                    parts = email_id.rsplit('_', 1)  # Split on last underscore
                    if len(parts) == 2:
                        subject, date = parts
                        history.append({
                            'subject': subject,
                            'date': date,
                            'processed_at': 'Unknown',  # We don't store this in the file
                            'status': 'processed'
                        })
            
            return jsonify({
                'status': 'success',
                'history': history
            })
        else:
            return jsonify({
                'status': 'success',
                'history': []
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-payments', methods=['POST'])
def process_payments():
    """Unified endpoint to sync database, fetch emails, and process payments"""
    try:
        data = request.get_json() or {}
        date_range_days = data.get('date_range_days', 7)  # Default to 7 days
        
        emit_email_log(f"🚀 Starting unified payment processing for last {date_range_days} days", "info")
        
        # Step 1: Sync database
        emit_email_log("📊 Step 1: Syncing database...", "info")
        sync_manager = get_sync_manager()
        sync_manager.force_sync_now(date_range_days=date_range_days)
        emit_email_log("✅ Database sync completed", "success")
        
        # Step 2: Fetch and process emails
        emit_email_log("📧 Step 2: Fetching and processing emails...", "info")
        
        # Set date range for email check
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=date_range_days)).strftime('%Y-%m-%d')
        
        # Import tools
        from agent.tools.google_tools import GmailFetchTool
        from agent.tools.email_tools import EmailParsingTool
        from agent.tools.payment_matching_tools import PaymentMatchingTool
        
        # Initialize tools
        gmail_tool = GmailFetchTool()
        email_parser = EmailParsingTool()
        payment_matcher = PaymentMatchingTool()
        
        # Fetch emails (without check_unprocessed_only to get all emails)
        emit_email_log(f"🔍 Fetching emails from {start_date} to {end_date}...", "info")
        email_result = gmail_tool._run(
            start_date=start_date,
            end_date=end_date,
            sender="aptexx",
            check_unprocessed_only=False  # Get all emails, we'll check duplicates later
        )
        
        if not email_result.get("success", False):
            emit_email_log(f"❌ Error fetching emails: {email_result.get('error', 'Unknown error')}", "error")
            return jsonify({'error': email_result.get('error', 'Unknown error')}), 500
        
        emails = email_result.get("emails", [])
        emit_email_log(f"📨 Found {len(emails)} emails from Aptexx", "info")
        
        if not emails:
            emit_email_log("ℹ️ No emails found in date range", "info")
            return jsonify({
                'status': 'success',
                'result': {
                    'emails_processed': 0,
                    'payments_processed': 0,
                    'jobs_created': 0,
                    'message': 'No emails found in date range'
                }
            })
        
        # Step 3: Process each email and check for duplicates
        emit_email_log("🔍 Step 3: Processing emails and checking for duplicates...", "info")
        
        total_payments = 0
        processed_payments = 0
        jobs_created = 0
        duplicate_payments = 0
        
        for i, email in enumerate(emails, 1):
            emit_email_log(f"📧 Processing email {i}/{len(emails)}: {email.get('subject', 'Unknown')}", "info")
            
            try:
                # Parse email to extract payment data
                parse_result = email_parser._run(
                    email_content=email.get('html', email.get('plain', '')),
                    email_source=f"{email.get('subject', '')}_{email.get('date', '')}",
                    save_raw_data=True,
                    validate_parsing=True
                )
                
                if not parse_result.get("success", False):
                    emit_email_log(f"⚠️ Failed to parse email {i}: {parse_result.get('error', 'Unknown error')}", "warning")
                    continue
                
                payments = parse_result.get("parsed_payments", [])
                total_payments += len(payments)
                
                # Process each payment
                for payment in payments:
                    try:
                        # Check if payment is already processed using existing duplicate checking
                        if payment_matcher._is_duplicate_payment(
                            reference=payment.get('ref', ''),
                            amount=payment.get('amount', 0),
                            tenant_name=payment.get('person', '')
                        ):
                            emit_email_log(f"🔄 Duplicate payment detected: {payment.get('ref', 'Unknown')} - ${payment.get('amount', 0)}", "warning")
                            duplicate_payments += 1
                            continue
                        
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
                            emit_email_log(f"✅ Payment matched: {payment.get('ref', 'Unknown')} - ${payment.get('amount', 0)}", "success")
                        else:
                            emit_email_log(f"⚠️ Payment needs review: {payment.get('ref', 'Unknown')} - {match_result.get('reasoning', 'Unknown reason')}", "warning")
                        
                        # Create job for human review
                        job = create_job(
                            job_type="payment_matching",
                            data={
                                "payment": payment,
                                "match_result": match_result,
                                "available_invoices": match_result.get("available_invoices", [])
                            },
                            confidence=match_result.get("confidence_score", 0.0),
                            reasoning=match_result.get("reasoning", "Payment requires review"),
                            recommendations=match_result.get("recommendations", [])
                        )
                        jobs_created += 1
                        
                    except Exception as e:
                        emit_email_log(f"❌ Error processing payment: {e}", "error")
                
            except Exception as e:
                emit_email_log(f"❌ Error processing email {i}: {e}", "error")
        
        # Update email status
        update_email_status(len(emails), processed_payments, emails)
        
        # Final summary
        emit_email_log(f"🎉 Payment processing completed!", "success")
        emit_email_log(f"📊 Summary: {len(emails)} emails, {total_payments} payments found, {processed_payments} processed, {duplicate_payments} duplicates, {jobs_created} jobs created", "info")
        
        result = {
            'emails_processed': len(emails),
            'payments_processed': processed_payments,
            'total_payments_found': total_payments,
            'duplicate_payments': duplicate_payments,
            'jobs_created': jobs_created,
            'message': f'Processed {len(emails)} emails, created {jobs_created} jobs for review'
        }
        
        return jsonify({
            'status': 'success',
            'result': result
        })
        
    except Exception as e:
        emit_email_log(f"💥 Error in unified payment processing: {e}", "error")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/clear', methods=['POST'])
def clear_jobs():
    """Clear all pending jobs (useful for testing)"""
    try:
        global pending_jobs, job_history
        pending_jobs.clear()
        job_history.clear()
        return jsonify({'status': 'success', 'message': 'All jobs cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/repair', methods=['POST'])
def repair_database():
    """Repair database tables if they're missing"""
    try:
        sync_manager = get_sync_manager()
        sync_manager._init_database()
        return jsonify({'status': 'success', 'message': 'Database repaired successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/status')
def get_agent_status():
    """Get AI agent status"""
    try:
        status = {
            'agent_initialized': agent is not None,
            'llm_initialized': llm is not None,
            'agent_executor_ready': agent.agent_executor is not None if agent else False,
            'status': 'ready' if agent and agent.agent_executor else 'not_ready'
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/initialize', methods=['POST'])
def initialize_agent_endpoint():
    """Manually initialize the AI agent"""
    try:
        initialize_agent()
        return jsonify({
            'status': 'success', 
            'message': 'Agent initialization completed',
            'agent_ready': agent is not None and agent.agent_executor is not None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_job(job_type: str, data: Dict[str, Any], confidence: float, 
               reasoning: str, recommendations: List[str]) -> Job:
    """Create a new job for human review"""
    
    # Check for duplicate jobs based on payment reference
    if job_type == "payment_matching" and "payment" in data:
        payment_ref = data["payment"].get("ref", "")
        payment_amount = data["payment"].get("amount", 0)
        payment_person = data["payment"].get("person", "")
        
        # Check if a job already exists for this payment
        for existing_job in pending_jobs + job_history:
            if (existing_job.job_type == "payment_matching" and 
                "payment" in existing_job.data and
                existing_job.data["payment"].get("ref", "") == payment_ref and
                existing_job.data["payment"].get("amount", 0) == payment_amount and
                existing_job.data["payment"].get("person", "") == payment_person):
                
                # Job already exists, return the existing one
                return existing_job
    
    # Create new job if no duplicate found
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

def emit_email_log(message: str, log_type: str = "info"):
    """Emit email processing log message to all connected clients"""
    try:
        # Use Flask app context to ensure SocketIO works properly
        with app.app_context():
            socketio.emit('email_log', {
                'message': message,
                'type': log_type,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        logging.error(f"Error emitting email log: {e}")
        # Fallback to console logging
        print(f"[EMAIL {log_type.upper()}] {message}")

def get_ai_response(job: Optional[Job], human_message: str) -> Optional[str]:
    """Get AI response to human chat message using LLM with formatted templates"""
    try:
        # Check if LLM is available
        llm_available = agent and agent.agent_executor and llm
        logging.info(f"LLM available: {llm_available}, Agent: {agent is not None}, Executor: {agent.agent_executor is not None if agent else False}, LLM: {llm is not None}")
        
        # First, try to use the LLM if available
        if llm_available:
            logging.info("Using LLM for response generation")
            return _get_llm_response(job, human_message)
        else:
            # Fall back to template responses if LLM not available
            logging.info("Using template fallback responses")
            if job:
                return _get_job_specific_response(job, human_message)
            else:
                return _get_general_response(human_message)
    except Exception as e:
        logging.error(f"Error getting AI response: {e}")
        return "I'm having trouble processing your question right now. Please try again."

def _get_llm_response(job: Optional[Job], human_message: str) -> str:
    """Get response from LLM with proper formatting"""
    try:
        if job:
            # Job-specific context
            payment = job.data.get('payment', {})
            payment_summary = ResponseTemplate.format_payment_summary(payment)
            
            context = f"""
            You are an AI assistant helping with a property management job review.
            
            Job Summary: {payment_summary}
            Job Type: {job.job_type}
            Confidence: {job.confidence:.0%}
            Reasoning: {job.reasoning}
            Recommendations: {', '.join(job.recommendations)}
            
            Human Question: {human_message}
            
            Provide a helpful, concise response. Use the payment summary format: **$amount** from **person** (property).
            Keep responses focused and actionable.
            """
        else:
            # General context
            pending_count = len([j for j in pending_jobs if j.status == "pending"])
            in_progress_count = len([j for j in pending_jobs if j.status == "in_progress"])
            
            context = f"""
            You are an AI assistant for a property management system that handles payment reconciliation.
            
            Current Status:
            - Pending jobs: {pending_count}
            - In progress jobs: {in_progress_count}
            
            Human Question: {human_message}
            
            Provide a helpful, concise response about the system, jobs, or payment processing.
            """
        
        # Use LLM to generate response
        response = llm.invoke(context)
        llm_response = str(response) if response else "I understand your question. Let me help you with this."
        
        # Format the response using templates for consistency
        if job:
            payment = job.data.get('payment', {})
            return ResponseTemplate.create_simple_response(
                summary=ResponseTemplate.format_payment_summary(payment),
                action="AI Analysis",
                details=llm_response
            )
        else:
            return ResponseTemplate.create_simple_response(
                summary="AI Assistant",
                action="Response",
                details=llm_response
            )
            
    except Exception as e:
        logging.error(f"Error getting LLM response: {e}")
        # Fall back to template response
        if job:
            return _get_job_specific_response(job, human_message)
        else:
            return _get_general_response(human_message)

def _get_job_specific_response(job: Job, human_message: str) -> str:
    """Get job-specific response using templates"""
    question_lower = human_message.lower()
    payment = job.data.get('payment', {})
    
    # Use templates for consistent formatting
    if "why" in question_lower or "reason" in question_lower:
        return ResponseTemplate.create_simple_response(
            summary=ResponseTemplate.format_job_summary(job),
            action="Review Required",
            details=job.reasoning
        )
    
    elif "confidence" in question_lower or "sure" in question_lower:
        confidence_text = "High" if job.confidence >= 0.8 else "Medium" if job.confidence >= 0.6 else "Low"
        return ResponseTemplate.create_simple_response(
            summary=ResponseTemplate.format_payment_summary(payment),
            action=f"Confidence: {confidence_text} ({job.confidence:.0%})",
            details="Lower confidence jobs need human review to ensure accuracy."
        )
    
    elif "recommend" in question_lower or "suggest" in question_lower:
        recommendations = '; '.join(job.recommendations)
        return ResponseTemplate.create_simple_response(
            summary=ResponseTemplate.format_payment_summary(payment),
            action="Recommendations",
            details=recommendations
        )
    
    elif "data" in question_lower or "info" in question_lower:
        return _format_job_details(job)
    
    elif "what" in question_lower and "payment" in question_lower:
        return ResponseTemplate.create_simple_response(
            summary=ResponseTemplate.format_payment_summary(payment),
            action="Payment Details",
            details=f"Job Type: {job.job_type.replace('_', ' ').title()}"
        )
    
    else:
        # Default job response
        return ResponseTemplate.create_complex_response(
            summary=ResponseTemplate.format_payment_summary(payment),
            issue=job.job_type.replace('_', ' ').title(),
            action="Review Required",
            confidence=job.confidence,
            details=job.reasoning
        )

def _get_general_response(human_message: str) -> str:
    """Get general response using templates"""
    question_lower = human_message.lower()
    pending_count = len([j for j in pending_jobs if j.status == "pending"])
    in_progress_count = len([j for j in pending_jobs if j.status == "in_progress"])
    
    if "job" in question_lower or "pending" in question_lower:
        return ResponseTemplate.create_simple_response(
            summary="Current Job Status",
            action=f"Pending: {pending_count}, In Progress: {in_progress_count}",
            details="Jobs are created when payments need human review."
        )
    
    elif "help" in question_lower:
        return ResponseTemplate.create_simple_response(
            summary="AI Assistant Help",
            action="Available Commands",
            details="Ask about jobs, payments, confidence levels, or recommendations. I can explain any job details or system status."
        )
    
    elif "system" in question_lower or "status" in question_lower:
        return ResponseTemplate.create_simple_response(
            summary="System Status",
            action="Active",
            details=f"Processing {pending_count + in_progress_count} jobs. System is ready for payment reconciliation."
        )
    
    else:
        return ResponseTemplate.create_simple_response(
            summary="AI Assistant",
            action="Ready to Help",
            details="I can help with job reviews, payment matching, and system questions. What would you like to know?"
        )

def _format_job_details(job: Job) -> str:
    """Format detailed job information"""
    payment = job.data.get('payment', {})
    result = ResponseTemplate.create_simple_response(
        summary=ResponseTemplate.format_payment_summary(payment),
        action="Job Details",
        details=f"Type: {job.job_type.replace('_', ' ').title()}"
    )
    
    # Add available invoices if present
    if "available_invoices" in job.data:
        invoices = job.data["available_invoices"]
        result += "\n\n**Available Invoices:**\n"
        for i, inv in enumerate(invoices, 1):
            result += f"{i}. {ResponseTemplate.format_invoice_summary(inv)}\n"
    
    # Add applied invoice if present
    if "applied_invoice" in job.data:
        applied = job.data["applied_invoice"]
        result += f"\n**Applied to:** {ResponseTemplate.format_invoice_summary(applied)}"
    
    return result

def initialize_agent():
    """Initialize the AI agent"""
    global agent, llm
    
    try:
        print("🤖 Initializing AI Agent...")
        
        # Setup LLM with better error handling
        print("📡 Connecting to Ollama server...")
        llm = setup_llm_for_agent(
            base_url="http://192.168.86.53:11434",
            model_name="llama3:latest",
            temperature=0.1
        )
        
        if llm:
            print("✅ LLM initialized successfully")
            
            # Initialize agent
            print("🤖 Creating PropertyManagementAgent...")
            agent = PropertyManagementAgent(verbose=False)
            agent.set_llm(llm)
            print("✅ AI Agent initialized successfully")
            
            # Test the agent
            print("🧪 Testing agent with simple query...")
            try:
                test_response = agent.agent_executor.invoke({"input": "Hello, are you working?"})
                print(f"✅ Agent test successful: {str(test_response)[:100]}...")
            except Exception as test_error:
                print(f"⚠️ Agent test failed: {test_error}")
                
        else:
            print("❌ Failed to initialize LLM - check Ollama server")
            
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        import traceback
        traceback.print_exc()

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
