# AI Agent Setup Guide

## Overview
This AI agent automates property management workflows, specifically payment reconciliation between Aptexx, Xero, and Tradify systems.

## Prerequisites
- Python 3.8+
- Ollama with llama3 model
- Virtual environment (recommended)

## Installation

1. **Clone the repository**
   ```bash
   cd /path/to/ParklaneCompare
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv ~/.venv
   source ~/.venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   cd ai_agent
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python scripts/init_database.py
   ```

5. **Set up Ollama**
   ```bash
   # Install llama3 model
   ollama pull llama3
   
   # Start Ollama server
   ollama serve
   ```

## Quick Start

1. **Start the web dashboard**
   ```bash
   cd web_dashboard
   python app.py
   ```
   Visit: http://localhost:5000

2. **Run tests**
   ```bash
   python run_tests.py
   ```

3. **Start sync manager**
   ```bash
   python -c "from sync_manager import start_sync_manager; start_sync_manager()"
   ```

## Project Structure

```
ai_agent/
├── agent/                    # Core AI agent code
│   ├── core_agent.py        # Main agent class
│   ├── tools/               # Custom tools
│   └── llm_setup.py         # LLM configuration
├── web_dashboard/           # Web interface
├── sync_manager.py          # Database sync system
├── tests/                   # Test files
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── data/               # Test data
├── scripts/                # Utility scripts
└── docs/                   # Documentation
```

## Configuration

### Environment Variables
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `XERO_CLIENT_ID`: Xero API client ID
- `XERO_CLIENT_SECRET`: Xero API client secret

### Database
- Location: `/tmp/payments.db`
- Tables: `invoices`, `payments`, `payment_tracking`, `sync_log`

## Troubleshooting

### Common Issues

1. **Ollama connection failed**
   - Ensure Ollama is running: `ollama serve`
   - Check model is installed: `ollama list`

2. **Database errors**
   - Reinitialize database: `python scripts/init_database.py`

3. **Import errors**
   - Ensure you're in the correct directory
   - Check virtual environment is activated

### Getting Help
- Check logs in the web dashboard
- Run tests: `python run_tests.py`
- Review sync status in dashboard

