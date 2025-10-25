"""
Core AI Agent for Property Management
Handles workflow orchestration and tool management
"""

import os
import sys
import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import time

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain.agents import AgentExecutor, create_react_agent
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
from .tools.investigation_tools import (
    TenantPaymentHistoryTool,
    InvoiceRelationshipTool, 
    BusinessScenarioValidatorTool,
    ComprehensivePaymentInvestigatorTool
)

# Import logging utilities
from utils.logger import get_agent_logger
from utils.logging_decorators import log_agent_action

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
        self.agent_logger = get_agent_logger()
    
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
            # New investigation tools for intelligent analysis
            TenantPaymentHistoryTool(),
            InvoiceRelationshipTool(),
            BusinessScenarioValidatorTool(),
            ComprehensivePaymentInvestigatorTool()
        ]

        if self.verbose:
            logger.info(f"Initialized {len(tools)} tools")
        return tools
    
    def set_llm(self, llm):
        """Set the language model and initialize the agent executor"""
        self.llm = llm
        
        # Create the agent prompt (ReAct format)
        from langchain.prompts import PromptTemplate
        
        prompt = PromptTemplate.from_template("""
{system_prompt}

TOOLS:
------
You have access to the following tools:

{tools}

To use a tool, please use the following format:

```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}""")
        
        # Create the agent with system prompt
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt.partial(system_prompt=self._get_system_prompt())
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
        return """You are an expert AI payment reconciliation agent for property management. You are highly intelligent and thorough, like a skilled accountant with investigative capabilities.

**YOUR CORE MISSION:**
Investigate payments and determine the best invoice matches with detailed reasoning. You NEVER automatically apply payments - you create detailed analysis for human review.

**INTELLIGENT INVESTIGATION APPROACH:**
When given a payment to analyze, you should think like a detective:

1. **Initial Assessment**: Start with the comprehensive payment investigator tool to get a full picture
2. **Deep Dive**: If initial results are unclear, investigate further:
   - Analyze tenant payment history for patterns
   - Find invoice relationships and combinations
   - Check for business scenarios (overpayments, prepayments, roommate situations)
3. **Multi-Angle Analysis**: Always consider multiple possibilities:
   - Exact matches vs combination matches
   - Overpayment scenarios vs prepayment scenarios
   - Roommate mix-ups vs tenant name variations
4. **Evidence-Based Reasoning**: Provide detailed explanations of your findings

**AVAILABLE INVESTIGATION TOOLS:**
- `investigate_payment_comprehensively`: Your primary investigation tool - use this first
  Example: payment_data="tenant_name=John Smith, amount=1200.0, property_name=Oak Street, reference=133786352"
- `analyze_tenant_payment_history`: Understand tenant payment patterns and history
  Example: tenant_name="John Smith", months_back=6
- `find_invoice_relationships`: Find related invoices, roommate scenarios, combinations
  Example: tenant_name="John Smith", property_name="Oak Street", amount=1200.0
- `validate_business_scenario`: Confirm overpayments, prepayments, partial payments
- `match_payment_to_invoice`: Basic algorithmic matching (use after investigation)
- `get_xero_invoices`: Search for specific invoices
- Plus email parsing, notification, and other support tools

**INVESTIGATION WORKFLOW:**
1. **Comprehensive Investigation**: Always start with `investigate_payment_comprehensively` using simple text format
2. **Deep Analysis**: If confidence < 80%, dig deeper with specific investigation tools
3. **Scenario Validation**: Test specific business scenarios that emerge
4. **Final Assessment**: Provide overall confidence score and primary recommendation

**TOOL INPUT FORMAT:**
For investigate_payment_comprehensively, use text format:
payment_data="tenant_name=NAME, amount=AMOUNT, property_name=PROPERTY, reference=REF, payment_date=DATE"

**CONFIDENCE SCORING:**
- 90-100%: Clear match with strong evidence
- 70-89%: Good match with minor concerns  
- 50-69%: Possible match requiring human judgment
- <50%: Unclear situation needing manual review

**REASONING EXAMPLES:**
"Payment of $1,200 from John Smith. Investigation shows:
- John has 3 unpaid invoices: $800, $400, and $1,200
- His payment history shows consistent $1,200 monthly payments
- $1,200 invoice matches exactly in amount and timing
- Confidence: 95% - Strong evidence for exact match"

"Payment of $1,500 from Jane Doe. Investigation reveals:
- Jane has one $1,200 invoice unpaid
- $300 overpayment detected
- Her history shows occasional overpayments for advance rent
- Confidence: 80% - Likely overpayment scenario"

**CRITICAL RULES:**
- NEVER make payment applications automatically
- ALWAYS provide detailed reasoning for your conclusions
- Use multiple investigation tools to build a complete picture
- If confidence is low, recommend human review with specific investigation points
- Consider business context and tenant behavior patterns
- Be thorough but efficient in your analysis

Your goal is to be the intelligent investigator that does all the detective work a human would do, then presents clear findings for human decision-making."""
    
    @log_agent_action("workflow_execution")
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
        
        # Log workflow start
        self.agent_logger.log_agent_action(
            action="workflow_start",
            tool="core_agent",
            input_data={"workflow_name": workflow_name, "kwargs": kwargs},
            output_data={},
            reasoning=f"Starting {workflow_name} workflow"
        )
        
        logger.info(f"Starting workflow: {workflow_name}")
        
        # Create workflow-specific prompt
        workflow_prompts = {
            "payment_processing": self._get_payment_workflow_prompt(),
            "invoice_reconciliation": self._get_reconciliation_workflow_prompt(),
        }
        
        if workflow_name not in workflow_prompts:
            error_msg = f"Unknown workflow: {workflow_name}"
            self.agent_logger.log_error(
                error_type="unknown_workflow",
                error_message=error_msg,
                context={"workflow_name": workflow_name, "available_workflows": list(workflow_prompts.keys())}
            )
            raise ValueError(error_msg)
        
        # Prepare the input for the agent
        input_text = workflow_prompts[workflow_name].format(**kwargs)
        
        try:
            start_time = time.time()
            result = self.agent_executor.invoke({"input": input_text})
            duration_ms = (time.time() - start_time) * 1000
            
            # Log workflow completion
            self.agent_logger.log_agent_action(
                action="workflow_complete",
                tool="core_agent",
                input_data={"workflow_name": workflow_name, "kwargs": kwargs},
                output_data={"result": str(result), "duration_ms": duration_ms},
                reasoning=f"Completed {workflow_name} workflow successfully"
            )
            
            # Log performance metric
            self.agent_logger.log_performance_metric(
                metric_name=f"{workflow_name}_workflow_duration",
                value=duration_ms,
                unit="milliseconds",
                context={"workflow_name": workflow_name}
            )
            
            logger.info(f"Workflow {workflow_name} completed successfully")
            return {
                "success": True,
                "workflow_name": workflow_name,
                "result": result,
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            # Log workflow error
            self.agent_logger.log_error(
                error_type=f"{workflow_name}_workflow_error",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                context={"workflow_name": workflow_name, "kwargs": kwargs}
            )
            
            logger.error(f"Workflow {workflow_name} failed: {str(e)}")
            return {
                "success": False,
                "workflow_name": workflow_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
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
