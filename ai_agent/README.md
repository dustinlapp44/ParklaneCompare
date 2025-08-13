# AI Agent for Property Management

An intelligent AI agent that automates payment reconciliation workflows for property management companies, handling data across Xero (accounting), Tradify (job management), and Aptexx (payments) systems.

## 🚀 Features

### Core Capabilities
- **Automated Payment Processing**: Parse Aptexx emails and match payments to Xero invoices
- **Hybrid Matching Logic**: Combines algorithmic and AI reasoning for accuracy
- **Database Synchronization**: Automated background sync with Xero data
- **Human-in-the-Loop**: Web dashboard for review and approval workflows
- **Duplicate Prevention**: Tracks processed payments to avoid re-application

### Key Workflows
1. **Email Parsing**: Extract payment data from Aptexx emails
2. **Payment Matching**: Match payments to invoices using hybrid logic
3. **Name Matching**: Fuzzy matching for tenant names with AI validation
4. **Database Sync**: Automated synchronization with Xero
5. **Review System**: Human approval for complex cases

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Aptexx Emails │    │   Xero API      │    │   Tradify API   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      AI Agent Core        │
                    │  (LangChain + Ollama)     │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│  Local Database   │  │  Web Dashboard    │  │  Sync Manager     │
│  (SQLite)         │  │  (Flask + Socket) │  │  (Background)     │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

## 📁 Project Structure

```
ai_agent/
├── agent/                    # Core AI agent
│   ├── core_agent.py        # Main agent orchestration
│   ├── tools/               # Custom tools for external APIs
│   │   ├── email_tools.py   # Aptexx email parsing
│   │   ├── xero_tools.py    # Xero API integration
│   │   ├── payment_matching_tools.py  # Payment matching logic
│   │   ├── name_matching_tools.py     # Name matching logic
│   │   ├── ai_reasoning_tools.py      # AI reasoning for edge cases
│   │   ├── notification_tools.py      # Email notifications
│   │   ├── dashboard_tools.py         # Dashboard reporting
│   │   └── database_sync_tools.py     # Database synchronization
│   └── llm_setup.py         # Ollama LLM configuration
├── web_dashboard/           # Human-in-the-loop interface
│   ├── app.py              # Flask web application
│   └── templates/          # HTML templates
├── sync_manager.py          # Automated database sync
├── tests/                   # Comprehensive test suite
│   ├── unit/               # Unit tests for individual components
│   ├── integration/        # Integration tests for workflows
│   └── data/               # Test data and scenarios
├── scripts/                # Utility scripts
│   ├── init_database.py    # Database initialization
│   ├── create_test_data.py # Test data generation
│   └── create_sample_jobs.py # Sample jobs for dashboard
├── docs/                   # Documentation
└── run_tests.py            # Test runner
```

## 🛠️ Installation

See [docs/setup.md](docs/setup.md) for detailed installation instructions.

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_database.py

# Start web dashboard
cd web_dashboard && python app.py

# Run tests
python run_tests.py
```

## 🎯 Key Features Explained

### Hybrid Matching System
- **Algorithmic Matching**: Fast exact and fuzzy matching for 80% of cases
- **AI Reasoning**: LLM-powered analysis for complex edge cases
- **Confidence Scoring**: Automatic flagging for human review

### Database Synchronization
- **Background Sync**: Automated every 6 hours (configurable)
- **Smart Detection**: Handles "payment before invoice" scenarios correctly
- **Comprehensive Logging**: Full audit trail of sync operations

### Human-in-the-Loop
- **Web Dashboard**: Real-time job management and approval
- **AI Chat**: Interactive Q&A about flagged items
- **Notifications**: Email alerts for review items

## 🔧 Configuration

### Environment Variables
```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export XERO_CLIENT_ID="your_xero_client_id"
export XERO_CLIENT_SECRET="your_xero_client_secret"
```

### Database Configuration
- **Location**: `/tmp/payments.db`
- **Tables**: `invoices`, `payments`, `payment_tracking`, `sync_log`
- **Sync Interval**: 6 hours (configurable)

## 🧪 Testing

### Run All Tests
```bash
python run_tests.py
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Speed and efficiency validation
- **Scripts**: Utility script validation

## 📊 Performance

### Benchmarks
- **Email Parsing**: ~0.1 seconds per email
- **Payment Matching**: ~0.01 seconds per payment (algorithmic)
- **AI Reasoning**: ~0.7 seconds per complex case (GPU accelerated)
- **Database Sync**: ~30 seconds for 1000 records

### Scalability
- **Batch Processing**: 20x faster than individual processing
- **GPU Acceleration**: Dramatically improved LLM response times
- **Database Caching**: Reduces API calls by 90%

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Run the test suite before submitting

## 📝 License

This project is proprietary software for property management automation.

## 🆘 Support

- **Documentation**: See [docs/](docs/) directory
- **Issues**: Check web dashboard logs
- **Testing**: Run `python run_tests.py` for diagnostics

