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
from ai_agent.agent.core_agent import PropertyManagementAgent
from ai_agent.agent.llm_setup import setup_llm_for_agent
from ai_agent.sync_manager import get_sync_manager, start_sync_manager, stop_sync_manager

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
        self.status = "pending"  # pending, approved, rejected, in_progress
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
load_sample_jobs()

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

@app.route('/api/jobs/<job_id>/approve', methods=['POST'])
def approve_job(job_id):
    """Approve a job"""
    job = next((j for j in pending_jobs if j.job_id == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    job.status = "approved"
    job.reviewed_at = datetime.now()
    job.reviewed_by = data.get('reviewer', 'Unknown')
    job.notes = data.get('notes', '')
    
    # Move to history
    pending_jobs.remove(job)
    job_history.append(job)
    
    # Notify AI agent of approval
    notify_agent_approval(job)
    
    # Emit to all clients
    socketio.emit('job_updated', job.to_dict())
    
    return jsonify({'success': True, 'job': job.to_dict()})

@app.route('/api/jobs/<job_id>/reject', methods=['POST'])
def reject_job(job_id):
    """Reject a job"""
    job = next((j for j in pending_jobs if j.job_id == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    job.status = "rejected"
    job.reviewed_at = datetime.now()
    job.reviewed_by = data.get('reviewer', 'Unknown')
    job.notes = data.get('notes', '')
    
    # Move to history
    pending_jobs.remove(job)
    job_history.append(job)
    
    # Notify AI agent of rejection
    notify_agent_rejection(job)
    
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
    """Force immediate sync"""
    try:
        sync_manager = get_sync_manager()
        sync_manager.force_sync_now()
        return jsonify({'status': 'success', 'message': 'Force sync initiated'})
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

def get_ai_response(job: Job, human_message: str) -> Optional[str]:
    """Get AI response to human chat message"""
    if agent and agent.agent_executor:
        try:
            # Create context for AI
            context = f"""
            Job Type: {job.job_type}
            Job Data: {json.dumps(job.data, indent=2)}
            Confidence: {job.confidence}
            Reasoning: {job.reasoning}
            Recommendations: {', '.join(job.recommendations)}
            
            Human Question: {human_message}
            
            Please provide a helpful response to the human's question about this job.
            """
            
            response = agent.agent_executor.invoke({
                "input": context
            })
            
            return response.get('output', 'I understand your question. Let me help you with this.')
            
        except Exception as e:
            logging.error(f"Error getting AI response: {e}")
            return "I'm having trouble processing your question right now. Please try again."
    else:
        # Smart fallback responses based on job type and question
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
                return f"Payment details: {payment.get('person', 'Unknown')} paid ${payment.get('amount', 0)} for {payment.get('property', 'Unknown')}. Reference: {payment.get('ref', 'N/A')}"
            elif job.job_type == "name_matching":
                return f"Payment name: {job.data.get('payment_name', 'Unknown')}. Available tenants: {', '.join(job.data.get('available_tenants', []))}"
            else:
                return f"Job data: {json.dumps(job.data, indent=2)}"
        else:
            return f"I can help you with this {job.job_type} job. The confidence level is {job.confidence:.0%}. What specific information would you like to know about the reasoning, recommendations, or data?"

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
