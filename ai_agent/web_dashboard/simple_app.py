"""
Simple Web Dashboard for Invoice Reconciliation
Minimal version without AI components to avoid high CPU/GPU usage
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime
from contextlib import redirect_stdout, redirect_stderr

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OutputCapture:
    """Capture stdout/stderr and emit to web interface"""
    def __init__(self, socketio):
        self.socketio = socketio
        self.buffer = []
    
    def write(self, text):
        if text.strip():  # Only emit non-empty lines
            self.buffer.append(text)
            # Emit to web interface
            self.socketio.emit('invoice_reconciliation_progress', {
                'message': text.strip(),
                'progress': None  # No specific progress, just output
            })
    
    def flush(self):
        pass

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/invoice-reconciliation')
def invoice_reconciliation_page():
    """Invoice reconciliation page"""
    return render_template('invoice_reconciliation.html')

@app.route('/api/invoice-reconciliation/run', methods=['POST'])
def run_invoice_reconciliation():
    """Run the invoice reconciliation pipeline"""
    try:
        # Check if pipeline is already running
        if hasattr(app, 'invoice_pipeline_running') and app.invoice_pipeline_running:
            return jsonify({'error': 'Pipeline is already running'}), 400
        
        # Set pipeline as running
        app.invoice_pipeline_running = True
        
        # Start pipeline in background thread
        def run_pipeline():
            try:
                # Emit start event
                socketio.emit('invoice_reconciliation_start', {
                    'start_date': '2024-01-01',
                    'end_date': datetime.now().strftime('%Y-%m-%d')
                })
                
                # Emit progress updates
                socketio.emit('invoice_reconciliation_progress', {
                    'message': 'Starting data pull from Google Drive and Xero...',
                    'progress': 10
                })
                
                # Create output capture
                output_capture = OutputCapture(socketio)
                
                with redirect_stdout(output_capture), redirect_stderr(output_capture):
                    # Import and run the pipeline
                    from Compare.main import run_full_pipeline
                    
                    # Run the pipeline
                    run_full_pipeline()
                
                # Emit completion
                socketio.emit('invoice_reconciliation_complete', {
                    'properties_processed': 0  # We'll get this from the output if needed
                })
                
            except Exception as e:
                # Emit error
                socketio.emit('invoice_reconciliation_error', {
                    'error': str(e)
                })
                logger.error(f"Invoice reconciliation error: {e}")
            finally:
                # Mark pipeline as not running
                app.invoice_pipeline_running = False
        
        # Start the pipeline thread
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
        
        return jsonify({'status': 'success', 'message': 'Pipeline started'})
        
    except Exception as e:
        app.invoice_pipeline_running = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoice-reconciliation/stop', methods=['POST'])
def stop_invoice_reconciliation():
    """Stop the invoice reconciliation pipeline"""
    try:
        if hasattr(app, 'invoice_pipeline_running') and app.invoice_pipeline_running:
            app.invoice_pipeline_running = False
            return jsonify({'success': True, 'message': 'Pipeline stop requested'})
        else:
            return jsonify({'error': 'No pipeline is currently running'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

if __name__ == '__main__':
    print("🚀 Starting Simple Invoice Reconciliation Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔄 Invoice reconciliation will be available at: http://localhost:5000/invoice-reconciliation")
    
    # Run the web server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
