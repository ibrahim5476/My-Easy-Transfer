"""
AI Agent for Transaction Processing using LangChain, Hugging Face, and ChromaDB.

This module provides an intelligent conversational agent for guiding users through
money transfer and mobile recharge transactions. It replaces the previous Groq-based
chatbot and transaction_processor.py with a more sophisticated agent-based system.
"""

import os
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool, tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain_community.vectorstores import Chroma
from langchain.schema import HumanMessage, AIMessage, SystemMessage

# Additional imports
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TransactionAIAgent:
    """
    Main AI Agent class for handling transaction conversations and processing.
    
    This agent uses LangChain to orchestrate conversation flow, Hugging Face for
    language understanding, and ChromaDB for contextual memory and knowledge retrieval.
    """
    
    def __init__(self, transaction_type: str = 'transfer', user_id: Optional[str] = None):
        """
        Initialize the AI Agent.
        
        Args:
            transaction_type (str): Type of transaction ('transfer' or 'recharge')
            user_id (str, optional): Unique identifier for the user
        """
        self.transaction_type = transaction_type
        self.user_id = user_id or str(uuid.uuid4())
        self.conversation_history = []
        self.transaction_data = self._initialize_transaction_data()
        
        # Initialize components
        self.embeddings = self._initialize_embeddings()
        self.vector_store = self._initialize_vector_store()
        self.llm = self._initialize_llm()
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()
        
        logger.info(f"TransactionAIAgent initialized for {transaction_type} with user_id: {self.user_id}")
    
    def _initialize_transaction_data(self) -> Dict[str, Any]:
        """Initialize empty transaction data structure."""
        if self.transaction_type == 'transfer':
            return {
                'step': 'initial',
                'recipient_name': None,
                'address': None,
                'phone_number': None,
                'amount': None,
                'confirmed': False,
                'completed': False,
                'currency': 'TND'  # Default to Tunisian Dinar
            }
        elif self.transaction_type == 'recharge':
            return {
                'step': 'initial',
                'phone_number': None,
                'operator': None,
                'amount': None,
                'confirmed': False,
                'completed': False,
                'currency': 'TND'
            }
        else:
            raise ValueError(f"Unknown transaction type: {self.transaction_type}")
    
    def _initialize_embeddings(self) -> HuggingFaceEmbeddings:
        """Initialize Hugging Face embeddings model."""
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},  # Use CPU for compatibility
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("HuggingFace embeddings initialized successfully")
            return embeddings
        except Exception as e:
            logger.error(f"Error initializing embeddings: {str(e)}")
            raise
    
    def _initialize_vector_store(self) -> Chroma:
        """Initialize ChromaDB vector store for contextual memory."""
        try:
            # Determine persist directory
            persist_dir = os.path.join(
                settings.MEDIA_ROOT,
                'chromadb',
                f'transaction_{self.transaction_type}'
            )
            os.makedirs(persist_dir, exist_ok=True)
            
            # Initialize Chroma with persistence
            vector_store = Chroma(
                collection_name=f"transaction_{self.transaction_type}_{self.user_id}",
                embedding_function=self.embeddings,
                persist_directory=persist_dir
            )
            logger.info(f"ChromaDB vector store initialized at {persist_dir}")
            return vector_store
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    def _initialize_llm(self) -> HuggingFacePipeline:
        """Initialize Hugging Face LLM for the agent."""
        try:
            # Use a lightweight model suitable for transaction guidance
            llm = HuggingFacePipeline(
                model_id="gpt2",  # Can be replaced with a more capable model
                task="text-generation",
                model_kwargs={
                    "temperature": 0.7,
                    "max_length": 512,
                    "do_sample": True,
                    "top_p": 0.95
                }
            )
            logger.info("HuggingFace LLM initialized successfully")
            return llm
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            # Fallback to a simpler approach if HuggingFacePipeline fails
            logger.warning("Falling back to basic LLM initialization")
            raise
    
    def _create_tools(self) -> List[Tool]:
        """Create custom tools for the agent."""
        tools = [
            self._create_validation_tool(),
            self._create_extraction_tool(),
            self._create_confirmation_tool(),
            self._create_json_generation_tool(),
            self._create_knowledge_retrieval_tool()
        ]
        return tools
    
    def _create_validation_tool(self) -> Tool:
        """Create a tool for validating transaction details."""
        @tool
        def validate_transaction_details(field: str, value: str) -> str:
            """
            Validate a specific transaction detail.
            
            Args:
                field: The field to validate (e.g., 'address', 'phone_number', 'amount')
                value: The value to validate
            
            Returns:
                Validation result as a string
            """
            try:
                if field == 'address':
                    return self._validate_address(value)
                elif field == 'phone_number':
                    return self._validate_phone_number(value)
                elif field == 'amount':
                    return self._validate_amount(value)
                elif field == 'operator':
                    return self._validate_operator(value)
                else:
                    return f"Unknown field: {field}"
            except Exception as e:
                logger.error(f"Validation error for {field}: {str(e)}")
                return f"Error validating {field}: {str(e)}"
        
        return Tool(
            name="validate_transaction_details",
            func=validate_transaction_details,
            description="Validate a specific transaction detail (address, phone_number, amount, operator)"
        )
    
    def _create_extraction_tool(self) -> Tool:
        """Create a tool for extracting transaction details from user input."""
        @tool
        def extract_transaction_details(user_input: str) -> str:
            """
            Extract transaction details from user input.
            
            Args:
                user_input: The user's message
            
            Returns:
                Extracted details as JSON string
            """
            try:
                extracted = self._extract_details_from_input(user_input)
                return json.dumps(extracted)
            except Exception as e:
                logger.error(f"Extraction error: {str(e)}")
                return json.dumps({"error": str(e)})
        
        return Tool(
            name="extract_transaction_details",
            func=extract_transaction_details,
            description="Extract transaction details (name, address, phone, amount, operator) from user input"
        )
    
    def _create_confirmation_tool(self) -> Tool:
        """Create a tool for detecting and processing confirmations."""
        @tool
        def process_confirmation(user_input: str) -> str:
            """
            Detect if the user is confirming transaction details.
            
            Args:
                user_input: The user's message
            
            Returns:
                Confirmation status as JSON string
            """
            try:
                is_confirmed = self._detect_confirmation(user_input)
                return json.dumps({
                    "confirmed": is_confirmed,
                    "message": "Transaction confirmed" if is_confirmed else "Confirmation not detected"
                })
            except Exception as e:
                logger.error(f"Confirmation detection error: {str(e)}")
                return json.dumps({"error": str(e)})
        
        return Tool(
            name="process_confirmation",
            func=process_confirmation,
            description="Detect if the user is confirming the transaction details"
        )
    
    def _create_json_generation_tool(self) -> Tool:
        """Create a tool for generating the final transaction JSON."""
        @tool
        def generate_transaction_json() -> str:
            """
            Generate the final transaction JSON file.
            
            Returns:
                Path to the generated JSON file
            """
            try:
                json_path = self._generate_transaction_json()
                return json.dumps({
                    "success": True,
                    "json_path": json_path,
                    "transaction_data": self.transaction_data
                })
            except Exception as e:
                logger.error(f"JSON generation error: {str(e)}")
                return json.dumps({"success": False, "error": str(e)})
        
        return Tool(
            name="generate_transaction_json",
            func=generate_transaction_json,
            description="Generate the final transaction JSON file with all confirmed details"
        )
    
    def _create_knowledge_retrieval_tool(self) -> Tool:
        """Create a tool for retrieving relevant knowledge from ChromaDB."""
        @tool
        def retrieve_knowledge(query: str, top_k: int = 3) -> str:
            """
            Retrieve relevant knowledge from ChromaDB.
            
            Args:
                query: The query to search for
                top_k: Number of top results to retrieve
            
            Returns:
                Retrieved knowledge as JSON string
            """
            try:
                results = self.vector_store.similarity_search(query, k=top_k)
                knowledge = [doc.page_content for doc in results]
                return json.dumps({
                    "query": query,
                    "results": knowledge,
                    "count": len(knowledge)
                })
            except Exception as e:
                logger.error(f"Knowledge retrieval error: {str(e)}")
                return json.dumps({"error": str(e)})
        
        return Tool(
            name="retrieve_knowledge",
            func=retrieve_knowledge,
            description="Retrieve relevant knowledge from the vector store based on a query"
        )
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent executor."""
        try:
            # Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Create agent
            agent = create_react_agent(self.llm, self.tools, prompt)
            
            # Create agent executor with memory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=memory,
                verbose=True,
                max_iterations=10,
                early_stopping_method="generate"
            )
            
            logger.info("LangChain agent executor created successfully")
            return executor
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            raise
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        if self.transaction_type == 'transfer':
            return """You are a professional virtual assistant for My Easy Transfer, specialized in money transfers and mobile recharges.

DESTINATION COUNTRIES:
- Only Tunisia and Morocco
- Refuse any requests to other countries

TRANSFER PROCESS:
1. Recipient name
2. Address (only in Tunisia or Morocco)
3. Phone number
4. Amount

MANDATORY CONFIRMATION:
At the end of each transaction, you MUST ALWAYS repeat all information in this exact order:
"Please confirm these details:
- Recipient name: [name]
- Address: [address]
- Phone number: [phone]
- Amount: [amount]
Is this correct?"

IMPORTANT RULES:
1. Verify that the address is in Tunisia or Morocco
2. Wait for user confirmation before finalizing
3. Allow corrections if there are errors in the information
4. Never proceed without repeating and confirming all information

Use the available tools to validate information and extract details from user input.
Always be polite, professional, and patient with the user."""
        
        elif self.transaction_type == 'recharge':
            return """You are a professional virtual assistant for My Easy Transfer, specialized in money transfers and mobile recharges.

DESTINATION COUNTRIES:
- Only Tunisia and Morocco
- Refuse any requests to other countries

MOBILE RECHARGE PROCESS:
1. Phone number (Tunisia or Morocco)
2. Operator
3. Amount

MANDATORY CONFIRMATION:
At the end of each transaction, you MUST ALWAYS repeat all information in this exact order:
"Please confirm these details:
- Phone number: [phone]
- Operator: [operator]
- Amount: [amount]
Is this correct?"

IMPORTANT RULES:
1. Verify that the phone number is from Tunisia or Morocco
2. Verify that the operator is valid (Tunisie Telecom, Orange Tunisie, Ooredoo Tunisie, Maroc Telecom, Orange Maroc)
3. Wait for user confirmation before finalizing
4. Allow corrections if there are errors in the information
5. Never proceed without repeating and confirming all information

Use the available tools to validate information and extract details from user input.
Always be polite, professional, and patient with the user."""
        
        else:
            return "You are a helpful assistant for My Easy Transfer."
    
    def process_user_input(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process user input and generate a response.
        
        Args:
            user_input (str): The user's message
        
        Returns:
            Tuple of (agent_response, updated_transaction_data)
        """
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Store conversation in vector store for context retrieval
            self._store_conversation_turn(user_input, "user")
            
            # Process input with agent
            response = self.agent_executor.invoke({
                "input": user_input,
                "chat_history": self.conversation_history
            })
            
            agent_response = response.get("output", "I'm sorry, I couldn't process your request.")
            
            # Add agent response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": agent_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Store conversation in vector store
            self._store_conversation_turn(agent_response, "assistant")
            
            # Check for confirmation
            if self._detect_confirmation(user_input):
                self.transaction_data['confirmed'] = True
                logger.info(f"Transaction confirmed for user {self.user_id}")
            
            # Extract any new transaction details
            extracted = self._extract_details_from_input(user_input)
            self._update_transaction_data(extracted)
            
            logger.info(f"Processed user input for {self.user_id}: {user_input[:50]}...")
            
            return agent_response, self.transaction_data
        
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            return f"An error occurred: {str(e)}", self.transaction_data
    
    def _store_conversation_turn(self, text: str, role: str) -> None:
        """Store a conversation turn in ChromaDB for context retrieval."""
        try:
            metadata = {
                "role": role,
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id,
                "transaction_type": self.transaction_type
            }
            self.vector_store.add_texts([text], metadatas=[metadata])
        except Exception as e:
            logger.warning(f"Could not store conversation turn in vector store: {str(e)}")
    
    def _extract_details_from_input(self, user_input: str) -> Dict[str, Any]:
        """Extract transaction details from user input using regex patterns."""
        extracted = {}
        
        if self.transaction_type == 'transfer':
            # Extract recipient name
            name_patterns = [
                r"à\s+([A-Za-zÀ-ÿ\s]+?)\s+(?:situé|qui|au|en|dont|avec|sur)",
                r"pour\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+(?:situé|qui|au|en|dont|avec|sur)|\s+\d)",
                r"(?:nom|bénéficiaire)\s+(?:est|:|s'appelle)?\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$)"
            ]
            for pattern in name_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    extracted['recipient_name'] = match.group(1).strip()
                    break
            
            # Extract address
            address_patterns = [
                r"(?:situé|habite|habite à|demeure|vit)(?:\s+(?:à|en|au))?\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+(?:et|dont|avec|au numéro|ayant|qui a)|\.|$)",
                r"adresse\s+(?:est|:)?\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+(?:et|dont|avec|au numéro|ayant|qui a)|\.|$)",
                r"destination\s+(?:est|:)?\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+|\.|\,|$)"
            ]
            for pattern in address_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    extracted['address'] = match.group(1).strip()
                    break
        
        # Extract phone number (common to both types)
        phone_patterns = [
            r"(?:téléphone|portable|numéro|contact|joignable)(?:\s+(?:est|au|:))?\s+(\+?[0-9]{1,4}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,})",
            r"(?<!\w)(\+?[0-9]{1,4}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,})(?!\w)"
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                phone = re.sub(r'[\s\-\.]', '', match.group(1))
                extracted['phone_number'] = phone
                break
        
        # Extract amount
        amount_patterns = [
            r"(\d+(?:[,.]\d+)?)\s*(?:euro|€|EUR)",
            r"(\d+(?:[,.]\d+)?)\s*(?:dinar|dinars|DT|TND)",
            r"montant\s+(?:de|est|:|s'élève à)?\s*(\d+(?:[,.]\d+)?)",
            r"(?:transférer|envoyer|recharger)(?:\s+(?:de|un montant de))?\s*(\d+(?:[,.]\d+)?)"
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '.')
                try:
                    if float(amount) > 0:
                        extracted['amount'] = amount
                        break
                except ValueError:
                    continue
        
        # Extract operator for recharges
        if self.transaction_type == 'recharge':
            operator_patterns = [
                r"(?:opérateur|fournisseur)\s+(?:est|:|s'appelle)?\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$|\.)",
                r"(?:chez|avec)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$|\.|,)"
            ]
            known_operators = [
                "tunisie telecom", "orange tunisie", "ooredoo tunisie",
                "orange", "ooredoo", "telecom", "maroc telecom", "orange maroc"
            ]
            for pattern in operator_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    potential_operator = match.group(1).strip().lower()
                    for known_op in known_operators:
                        if known_op in potential_operator or potential_operator in known_op:
                            extracted['operator'] = potential_operator.title()
                            break
                    if 'operator' in extracted:
                        break
        
        return extracted
    
    def _update_transaction_data(self, extracted: Dict[str, Any]) -> None:
        """Update transaction data with newly extracted information."""
        for key, value in extracted.items():
            if key in self.transaction_data and value is not None:
                self.transaction_data[key] = value
    
    def _validate_address(self, address: str) -> str:
        """Validate that the address is in Tunisia or Morocco."""
        tunisia_keywords = ["tunis", "sfax", "sousse", "hammamet", "djerba", "gafsa", "kairouan", "monastir"]
        morocco_keywords = ["casablanca", "marrakech", "fez", "rabat", "tangier", "agadir", "meknes", "oujda"]
        
        address_lower = address.lower()
        
        if any(keyword in address_lower for keyword in tunisia_keywords):
            return "Address validated for Tunisia"
        elif any(keyword in address_lower for keyword in morocco_keywords):
            return "Address validated for Morocco"
        else:
            return "Address not validated. Please ensure the address is in Tunisia or Morocco."
    
    def _validate_phone_number(self, phone: str) -> str:
        """Validate phone number format."""
        # Remove non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check length (typically 10-15 digits including country code)
        if 10 <= len(cleaned) <= 15:
            return f"Phone number validated: {cleaned}"
        else:
            return f"Invalid phone number format. Expected 10-15 digits, got {len(cleaned)}"
    
    def _validate_amount(self, amount: str) -> str:
        """Validate transaction amount."""
        try:
            amount_float = float(amount.replace(',', '.'))
            if amount_float > 0:
                return f"Amount validated: {amount_float} {self.transaction_data.get('currency', 'TND')}"
            else:
                return "Amount must be greater than 0"
        except ValueError:
            return f"Invalid amount format: {amount}"
    
    def _validate_operator(self, operator: str) -> str:
        """Validate mobile operator."""
        known_operators = [
            "tunisie telecom", "orange tunisie", "ooredoo tunisie",
            "maroc telecom", "orange maroc", "maroc", "orange", "ooredoo", "telecom"
        ]
        
        operator_lower = operator.lower()
        
        for known_op in known_operators:
            if known_op in operator_lower or operator_lower in known_op:
                return f"Operator validated: {operator}"
        
        return f"Unknown operator: {operator}. Please choose from: Tunisie Telecom, Orange, Ooredoo, Maroc Telecom"
    
    def _detect_confirmation(self, user_input: str) -> bool:
        """Detect if the user is confirming the transaction."""
        confirmation_keywords = [
            "confirme", "je confirme", "c'est correct",
            "valider", "accepte", "approuve", "exact", "tout à fait",
            "validé", "correct", "c'est bon", "parfait", "procéder", "ça me va", "go",
            "allez-y", "vas-y", "confirmons", "bien sûr", "certainement", "yes", "oui"
        ]
        
        user_input_lower = user_input.lower()
        user_input_clean = re.sub(r'[^\w\s]', '', user_input_lower)
        
        # Check for confirmation keywords
        for keyword in confirmation_keywords:
            if keyword in user_input_clean:
                # Avoid false positives with negations
                negation_patterns = [
                    r"ne\s+\w+\s+pas\s+" + keyword,
                    r"pas\s+" + keyword,
                    r"non\s+\w*\s*" + keyword
                ]
                if not any(re.search(pattern, user_input_lower) for pattern in negation_patterns):
                    return True
        
        return False
    
    def _generate_transaction_json(self) -> str:
        """Generate the final transaction JSON file."""
        try:
            # Prepare transaction data
            transaction_json = {
                "transaction_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id,
                "transaction_type": self.transaction_type,
                "status": "confirmed" if self.transaction_data['confirmed'] else "pending",
                "details": {k: v for k, v in self.transaction_data.items() if k not in ['step', 'confirmed', 'completed']}
            }
            
            # Create output directory
            output_dir = os.path.join(settings.MEDIA_ROOT, 'output', self.user_id)
            os.makedirs(output_dir, exist_ok=True)
            
            # Write JSON file
            json_filename = f"transaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            json_path = os.path.join(output_dir, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(transaction_json, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Transaction JSON generated at {json_path}")
            return json_path
        
        except Exception as e:
            logger.error(f"Error generating transaction JSON: {str(e)}")
            raise
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        return self.conversation_history
    
    def get_transaction_data(self) -> Dict[str, Any]:
        """Get the current transaction data."""
        return self.transaction_data
    
    def reset(self) -> None:
        """Reset the agent state."""
        self.conversation_history = []
        self.transaction_data = self._initialize_transaction_data()
        logger.info(f"Agent reset for user {self.user_id}")
