"""
LLM Setup and Configuration for AI Agent
Handles Ollama integration and LLM initialization
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_ollama import OllamaLLM as Ollama
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

logger = logging.getLogger(__name__)

class LLMSetup:
    """Setup and manage LLM connections"""
    
    def __init__(self, base_url: str = "http://192.168.86.53:11434", model_name: str = "llama3:latest"):
        """
        Initialize LLM setup
        
        Args:
            base_url: Ollama server URL (default: 192.168.86.53:11434)
            model_name: Model name to use (default: llama3:latest)
        """
        self.base_url = base_url
        self.model_name = model_name
        self.llm = None
        self.is_connected = False
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for LLM operations"""
        log_dir = os.path.join(project_root, "ai_agent", "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, f"llm_{datetime.now().strftime('%Y%m%d')}.log")),
                logging.StreamHandler()
            ]
        )
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server"""
        try:
            logger.info(f"Testing connection to Ollama at {self.base_url}")
            
            # Create a simple LLM instance to test connection
            test_llm = Ollama(
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.1
            )
            
            # Test with a simple prompt
            response = test_llm.invoke("Hello, this is a connection test. Please respond with 'Connection successful' if you can see this message.")
            
            logger.info("✅ Ollama connection successful")
            return {
                "success": True,
                "base_url": self.base_url,
                "model_name": self.model_name,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ollama connection failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "base_url": self.base_url,
                "model_name": self.model_name,
                "timestamp": datetime.now().isoformat()
            }
    
    def initialize_llm(self, temperature: float = 0.1, streaming: bool = True) -> Optional[Ollama]:
        """
        Initialize the LLM instance
        
        Args:
            temperature: Model temperature (0.0 = deterministic, 1.0 = creative)
            streaming: Whether to enable streaming responses
            
        Returns:
            Initialized Ollama LLM instance or None if failed
        """
        try:
            logger.info(f"Initializing LLM: {self.model_name} at {self.base_url}")
            
            # Setup callbacks for streaming
            callbacks = None
            if streaming:
                callbacks = CallbackManager([StreamingStdOutCallbackHandler()])
            
            # Create LLM instance
            self.llm = Ollama(
                base_url=self.base_url,
                model=self.model_name,
                temperature=temperature,
                callback_manager=callbacks
            )
            
            # Test the LLM
            test_result = self.test_connection()
            if test_result["success"]:
                self.is_connected = True
                logger.info("✅ LLM initialized successfully")
                return self.llm
            else:
                logger.error("❌ LLM initialization failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error initializing LLM: {str(e)}")
            return None
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models from Ollama"""
        try:
            import requests
            
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                logger.info(f"Found {len(models.get('models', []))} available models")
                return {
                    "success": True,
                    "models": models.get('models', []),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"Failed to get models: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_reasoning_capabilities(self) -> Dict[str, Any]:
        """Test LLM reasoning capabilities with a complex scenario"""
        if not self.llm:
            return {
                "success": False,
                "error": "LLM not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Test scenario: Multiple invoice matching
            test_prompt = """
            Analyze this payment matching scenario:
            
            Payment: $1,200 from "Anna Camacho" for "Barcelona Property"
            Available invoices:
            1. Invoice A: $1,200 due (Anna Camacho, Barcelona)
            2. Invoice B: $800 due (Anna Camacho, Barcelona)
            3. Invoice C: $1,500 due (Anna Smith, Barcelona)
            
            Which invoice should this payment be applied to and why?
            Consider:
            - Exact name matching
            - Amount matching
            - Property matching
            - Business logic (oldest first, etc.)
            
            Provide your reasoning step by step.
            """
            
            logger.info("Testing LLM reasoning capabilities...")
            response = self.llm.invoke(test_prompt)
            
            return {
                "success": True,
                "test_prompt": test_prompt,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error testing reasoning capabilities: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_llm_info(self) -> Dict[str, Any]:
        """Get information about the current LLM setup"""
        return {
            "base_url": self.base_url,
            "model_name": self.model_name,
            "is_connected": self.is_connected,
            "llm_initialized": self.llm is not None,
            "timestamp": datetime.now().isoformat()
        }

def setup_llm_for_agent(base_url: str = "http://192.168.86.53:11434", 
                       model_name: str = "llama3:latest",
                       temperature: float = 0.1) -> Optional[Ollama]:
    """
    Setup LLM for the AI agent
    
    Args:
        base_url: Ollama server URL
        model_name: Model name to use
        temperature: Model temperature
        
    Returns:
        Initialized LLM instance or None if failed
    """
    logger.info("Setting up LLM for AI agent...")
    
    # Create LLM setup
    llm_setup = LLMSetup(base_url=base_url, model_name=model_name)
    
    # Test connection first
    connection_test = llm_setup.test_connection()
    if not connection_test["success"]:
        logger.error(f"LLM connection failed: {connection_test['error']}")
        return None
    
    # Initialize LLM
    llm = llm_setup.initialize_llm(temperature=temperature)
    if not llm:
        logger.error("LLM initialization failed")
        return None
    
    # Test reasoning capabilities
    reasoning_test = llm_setup.test_reasoning_capabilities()
    if reasoning_test["success"]:
        logger.info("✅ LLM reasoning test passed")
    else:
        logger.warning(f"⚠️ LLM reasoning test failed: {reasoning_test['error']}")
    
    logger.info("✅ LLM setup completed successfully")
    return llm

if __name__ == "__main__":
    # Test LLM setup
    print("Testing LLM Setup...")
    print("=" * 50)
    
    # Test with default settings
    llm_setup = LLMSetup()
    
    # Test connection
    print("\n1. Testing connection...")
    connection_result = llm_setup.test_connection()
    print(f"Connection: {'✅ Success' if connection_result['success'] else '❌ Failed'}")
    
    if connection_result['success']:
        # Get available models
        print("\n2. Getting available models...")
        models_result = llm_setup.get_available_models()
        if models_result['success']:
            print(f"Available models: {len(models_result['models'])}")
            for model in models_result['models'][:3]:  # Show first 3
                print(f"  - {model.get('name', 'Unknown')}")
        else:
            print(f"Failed to get models: {models_result['error']}")
        
        # Initialize LLM
        print("\n3. Initializing LLM...")
        llm = llm_setup.initialize_llm(temperature=0.1)
        if llm:
            print("✅ LLM initialized successfully")
            
            # Test reasoning
            print("\n4. Testing reasoning capabilities...")
            reasoning_result = llm_setup.test_reasoning_capabilities()
            if reasoning_result['success']:
                print("✅ Reasoning test passed")
                print("Response preview:", reasoning_result['response'][:100] + "...")
            else:
                print(f"❌ Reasoning test failed: {reasoning_result['error']}")
        else:
            print("❌ LLM initialization failed")
    
    print("\n" + "=" * 50)
    print("LLM Setup Test Complete")
    print("=" * 50)
