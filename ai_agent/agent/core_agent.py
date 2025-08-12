"""
Core AI Agent for Property Management
Handles workflow orchestration and tool management
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory

# Import our custom tools
from .tools.email_tools import EmailParsingTool
from .tools.xero_tools import XeroInvoiceTool, XeroPaymentTool
from .tools.google_tools import GmailFetchTool
from .tools.notification_tools import NotificationTool
from .tools.dashboard_tools import DashboardTool
from .tools.payment_matching_tools import PaymentMatchingTool
from .tools.name_matching_tools import NameMatchingTool
from .tools.ai_reasoning_tools import AIReasoningTool

logger = logging.getLogger(__name__)

class PropertyManagementAgent:
    """
    Main AI agent for property management tasks
    """
    
    def __init__(self, llm=None, verbose: bool = False):
        """
        Initialize the property management agent
        
        Args:
            llm: Language model instance (will be set up later with Ollama)
            verbose: Whether to enable verbose logging
        """
        self.llm = llm
        self.verbose = verbose
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # LLM will be set later
        self.llm = None
        
        # Initialize agent (will be set up when LLM is available)
        self.agent_executor = None
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = os.path.join(project_root, "ai_agent", "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO if self.verbose else logging.WARNING,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, f"agent_{datetime.now().strftime('%Y%m%d')}.log")),
                logging.StreamHandler()
            ]
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize all available tools"""
        tools = [
            EmailParsingTool(),
            GmailFetchTool(),
            XeroInvoiceTool(),
            XeroPaymentTool(),
            NotificationTool(),
            DashboardTool(),
            PaymentMatchingTool(),
            NameMatchingTool(),
            AIReasoningTool(),
        ]

        if self.verbose:
            logger.info(f"Initialized {len(tools)} tools")
        return tools
    
    def set_llm(self, llm):
        """Set the language model and initialize the agent executor"""
        self.llm = llm
        
        # Create the agent prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.verbose,
            handle_parsing_errors=True,
            max_iterations=10
        )
        
        logger.info("Agent executor initialized with LLM")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """You are an AI agent specialized in property management tasks. Your primary responsibilities include:

1. **Payment Processing**: Parse Aptexx payment emails and apply payments to Xero invoices
2. **Invoice Reconciliation**: Match payments to invoices and handle discrepancies
3. **Data Validation**: Ensure all financial data is accurate and complete
4. **Error Handling**: Gracefully handle failures and flag issues for human review

**IMPORTANT RULES:**
- Always save raw data (emails, parsed data) for audit trails
- Never make assumptions about financial data - if uncertain, flag for review
- Use the available tools to perform tasks - don't make up information
- Provide clear explanations of your reasoning and actions
- If a task cannot be completed with high confidence, stop and report the issue

**Available Tools:**
- Email parsing tools for Aptexx payment emails
- Xero tools for invoice and payment management
- Google tools for email fetching and file operations

When processing payments, follow this workflow:
1. Fetch and parse Aptexx payment emails
2. Extract payment details (tenant, property, amount, date)
3. Find matching invoices in Xero
4. Apply payments with proper validation
5. Report any unmatched or failed payments

Always maintain data integrity and provide clear audit trails."""
    
    def run_workflow(self, workflow_name: str, **kwargs) -> Dict[str, Any]:
        """
        Run a specific workflow
        
        Args:
            workflow_name: Name of the workflow to run
            **kwargs: Workflow-specific parameters
            
        Returns:
            Dictionary with workflow results
        """
        if not self.agent_executor:
            raise ValueError("LLM not set. Call set_llm() first.")
        
        logger.info(f"Starting workflow: {workflow_name}")
        
        # Create workflow-specific prompt
        workflow_prompts = {
            "payment_processing": self._get_payment_workflow_prompt(),
            "invoice_reconciliation": self._get_reconciliation_workflow_prompt(),
        }
        
        if workflow_name not in workflow_prompts:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        # Prepare the input for the agent
        input_text = workflow_prompts[workflow_name].format(**kwargs)
        
        try:
            result = self.agent_executor.invoke({"input": input_text})
            logger.info(f"Workflow {workflow_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Workflow {workflow_name} failed: {str(e)}")
            raise
    
    def _get_payment_workflow_prompt(self) -> str:
        """Get the prompt for payment processing workflow"""
        return """Process today's Aptexx payments:

1. Fetch the latest Aptexx payment email from Gmail
2. Parse the email to extract payment details
3. For each payment:
   - Find the corresponding tenant invoice in Xero
   - Apply the payment to the invoice
   - Validate the payment was applied correctly
4. Report any unmatched payments or errors

Please execute this workflow step by step, showing your reasoning at each stage."""
    
    def _get_reconciliation_workflow_prompt(self) -> str:
        """Get the prompt for invoice reconciliation workflow"""
        return """Reconcile invoices and payments for the specified period:

1. Pull invoice data from Xero for the date range
2. Pull payment data from Xero for the date range  
3. Match payments to invoices using fuzzy matching
4. Identify unmatched items and discrepancies
5. Generate a reconciliation report

Please execute this workflow step by step, showing your reasoning at each stage."""
    
    def get_available_workflows(self) -> List[str]:
        """Get list of available workflows"""
        return ["payment_processing", "invoice_reconciliation"]
    
    def get_tool_info(self) -> List[Dict[str, str]]:
        """Get information about available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": str(tool.args_schema) if hasattr(tool, 'args_schema') else "N/A"
            }
            for tool in self.tools
        ]
    
    def process_payments_batch(self, payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process multiple payments efficiently without individual LLM calls
        
        Args:
            payments: List of payment dictionaries
            
        Returns:
            Dictionary with batch processing results
        """
        if not self.agent_executor:
            raise ValueError("LLM not set. Call set_llm() first.")
        
        logger.info(f"Processing {len(payments)} payments in batch")
        
        results = {
            "processed": 0,
            "matched": 0,
            "unmatched": 0,
            "errors": 0,
            "details": []
        }
        
        # Use algorithmic matching for efficiency
        payment_matching_tool = next((tool for tool in self.tools if tool.name == "match_payment"), None)
        
        if not payment_matching_tool:
            raise ValueError("Payment matching tool not found")
        
        for payment in payments:
            try:
                # Use direct tool call instead of LLM reasoning for each payment
                match_result = payment_matching_tool._run(
                    payment=payment,
                    tenant_name=payment.get('person', ''),
                    amount=payment.get('amount', 0),
                    payment_date=payment.get('date', ''),
                    reference=payment.get('ref', ''),
                    property_name=payment.get('property', '')
                )
                
                results["processed"] += 1
                
                if match_result.get("success", False):
                    results["matched"] += 1
                else:
                    results["unmatched"] += 1
                
                results["details"].append({
                    "payment": payment,
                    "match_result": match_result
                })
                
            except Exception as e:
                logger.error(f"Error processing payment {payment.get('ref', 'unknown')}: {e}")
                results["errors"] += 1
                results["details"].append({
                    "payment": payment,
                    "error": str(e)
                })
        
        logger.info(f"Batch processing complete: {results['matched']} matched, {results['unmatched']} unmatched, {results['errors']} errors")
        return results
