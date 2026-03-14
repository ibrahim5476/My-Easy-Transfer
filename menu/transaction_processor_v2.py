"""
Transaction Processor V2 - Integration layer between Django views and the AI Agent.

This module provides functions to interact with the TransactionAIAgent, managing
the lifecycle of transactions and integrating with Django session management.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from .ai_agent import TransactionAIAgent

logger = logging.getLogger(__name__)

# Global dictionary to store active agents per user session
_active_agents: Dict[str, TransactionAIAgent] = {}


def get_or_create_agent(
    request,
    transaction_type: str = 'transfer',
    force_new: bool = False
) -> TransactionAIAgent:
    """
    Get or create an AI agent for the current user session.
    
    Args:
        request: Django request object
        transaction_type (str): Type of transaction ('transfer' or 'recharge')
        force_new (bool): Force creation of a new agent
    
    Returns:
        TransactionAIAgent instance
    """
    user_id = request.user.username
    session_key = f"{user_id}_{transaction_type}"
    
    # Check if agent already exists and is not forced to be new
    if not force_new and session_key in _active_agents:
        logger.debug(f"Using existing agent for {session_key}")
        return _active_agents[session_key]
    
    # Create new agent
    try:
        agent = TransactionAIAgent(transaction_type=transaction_type, user_id=user_id)
        _active_agents[session_key] = agent
        logger.info(f"Created new agent for {session_key}")
        
        # Store agent info in session
        if 'ai_agent_info' not in request.session:
            request.session['ai_agent_info'] = {}
        request.session['ai_agent_info'][transaction_type] = {
            'user_id': user_id,
            'transaction_type': transaction_type,
            'created_at': str(os.times())
        }
        request.session.modified = True
        
        return agent
    except Exception as e:
        logger.error(f"Error creating AI agent: {str(e)}")
        raise


def process_user_message(
    request,
    user_message: str,
    transaction_type: str = 'transfer'
) -> Tuple[str, Dict[str, Any], bool]:
    """
    Process a user message through the AI agent.
    
    Args:
        request: Django request object
        user_message (str): The user's message
        transaction_type (str): Type of transaction
    
    Returns:
        Tuple of (agent_response, transaction_data, is_confirmed)
    """
    try:
        # Get or create agent
        agent = get_or_create_agent(request, transaction_type)
        
        # Process the message
        response, transaction_data = agent.process_user_input(user_message)
        
        # Check if transaction is confirmed
        is_confirmed = transaction_data.get('confirmed', False)
        
        # Update session with current transaction data
        request.session['transfer_data'] = transaction_data
        request.session.modified = True
        
        logger.info(f"Processed message for {request.user.username}: confirmed={is_confirmed}")
        
        return response, transaction_data, is_confirmed
    
    except Exception as e:
        logger.error(f"Error processing user message: {str(e)}")
        return f"An error occurred: {str(e)}", {}, False


def generate_transaction_json(
    request,
    transaction_type: str = 'transfer'
) -> Optional[str]:
    """
    Generate the final transaction JSON file.
    
    Args:
        request: Django request object
        transaction_type (str): Type of transaction
    
    Returns:
        Path to the generated JSON file, or None if generation failed
    """
    try:
        agent = get_or_create_agent(request, transaction_type)
        
        # Verify transaction is confirmed
        transaction_data = agent.get_transaction_data()
        if not transaction_data.get('confirmed', False):
            logger.warning(f"Cannot generate JSON for unconfirmed transaction")
            return None
        
        # Generate JSON
        json_path = agent._generate_transaction_json()
        
        # Mark transaction as completed
        transaction_data['completed'] = True
        request.session['transfer_data'] = transaction_data
        request.session.modified = True
        
        logger.info(f"Generated transaction JSON at {json_path}")
        return json_path
    
    except Exception as e:
        logger.error(f"Error generating transaction JSON: {str(e)}")
        return None


def get_conversation_history(
    request,
    transaction_type: str = 'transfer'
) -> list:
    """
    Get the conversation history for the current transaction.
    
    Args:
        request: Django request object
        transaction_type (str): Type of transaction
    
    Returns:
        List of conversation turns
    """
    try:
        agent = get_or_create_agent(request, transaction_type)
        return agent.get_conversation_history()
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}")
        return []


def get_transaction_data(
    request,
    transaction_type: str = 'transfer'
) -> Dict[str, Any]:
    """
    Get the current transaction data.
    
    Args:
        request: Django request object
        transaction_type (str): Type of transaction
    
    Returns:
        Dictionary containing transaction data
    """
    try:
        agent = get_or_create_agent(request, transaction_type)
        return agent.get_transaction_data()
    except Exception as e:
        logger.error(f"Error retrieving transaction data: {str(e)}")
        return {}


def reset_transaction(
    request,
    transaction_type: str = 'transfer'
) -> bool:
    """
    Reset the transaction state.
    
    Args:
        request: Django request object
        transaction_type (str): Type of transaction
    
    Returns:
        True if successful, False otherwise
    """
    try:
        user_id = request.user.username
        session_key = f"{user_id}_{transaction_type}"
        
        # Remove agent from active agents
        if session_key in _active_agents:
            del _active_agents[session_key]
        
        # Clear session data
        if 'transfer_data' in request.session:
            del request.session['transfer_data']
        if 'ai_agent_info' in request.session:
            if transaction_type in request.session['ai_agent_info']:
                del request.session['ai_agent_info'][transaction_type]
        
        request.session.modified = True
        
        logger.info(f"Reset transaction for {session_key}")
        return True
    
    except Exception as e:
        logger.error(f"Error resetting transaction: {str(e)}")
        return False


def cleanup_old_agents(max_age_seconds: int = 3600) -> None:
    """
    Clean up old agents that have been idle for too long.
    
    Args:
        max_age_seconds (int): Maximum age of an agent in seconds
    """
    try:
        import time
        current_time = time.time()
        agents_to_remove = []
        
        for session_key, agent in _active_agents.items():
            # Check if agent is old (this is a simple implementation)
            # In production, you might want to track last activity time
            if hasattr(agent, '_created_at'):
                age = current_time - agent._created_at
                if age > max_age_seconds:
                    agents_to_remove.append(session_key)
        
        for session_key in agents_to_remove:
            del _active_agents[session_key]
            logger.info(f"Removed old agent: {session_key}")
    
    except Exception as e:
        logger.error(f"Error cleaning up old agents: {str(e)}")


def validate_transaction_details(
    transaction_data: Dict[str, Any],
    transaction_type: str = 'transfer'
) -> Tuple[bool, str]:
    """
    Validate transaction details before confirmation.
    
    Args:
        transaction_data (dict): Transaction data to validate
        transaction_type (str): Type of transaction
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if transaction_type == 'transfer':
            # Validate required fields
            required_fields = ['recipient_name', 'address', 'phone_number', 'amount']
            for field in required_fields:
                if not transaction_data.get(field):
                    return False, f"Missing required field: {field}"
            
            # Validate address is in Tunisia or Morocco
            address = transaction_data.get('address', '').lower()
            valid_countries = ['tunis', 'sfax', 'sousse', 'hammamet', 'djerba', 'gafsa',
                             'casablanca', 'marrakech', 'fez', 'rabat', 'tangier', 'agadir']
            if not any(country in address for country in valid_countries):
                return False, "Address must be in Tunisia or Morocco"
            
            # Validate amount is positive
            try:
                amount = float(transaction_data.get('amount', 0))
                if amount <= 0:
                    return False, "Amount must be greater than 0"
            except ValueError:
                return False, "Invalid amount format"
        
        elif transaction_type == 'recharge':
            # Validate required fields
            required_fields = ['phone_number', 'operator', 'amount']
            for field in required_fields:
                if not transaction_data.get(field):
                    return False, f"Missing required field: {field}"
            
            # Validate operator
            valid_operators = ['tunisie telecom', 'orange tunisie', 'ooredoo tunisie',
                             'maroc telecom', 'orange maroc']
            operator = transaction_data.get('operator', '').lower()
            if not any(op in operator for op in valid_operators):
                return False, "Invalid operator"
            
            # Validate amount is positive
            try:
                amount = float(transaction_data.get('amount', 0))
                if amount <= 0:
                    return False, "Amount must be greater than 0"
            except ValueError:
                return False, "Invalid amount format"
        
        return True, "All validations passed"
    
    except Exception as e:
        logger.error(f"Error validating transaction details: {str(e)}")
        return False, f"Validation error: {str(e)}"


def export_conversation_to_json(
    request,
    transaction_type: str = 'transfer'
) -> Optional[str]:
    """
    Export the conversation history to a JSON file.
    
    Args:
        request: Django request object
        transaction_type (str): Type of transaction
    
    Returns:
        Path to the exported JSON file, or None if export failed
    """
    try:
        agent = get_or_create_agent(request, transaction_type)
        
        # Get conversation history
        history = agent.get_conversation_history()
        
        # Create output directory
        output_dir = os.path.join(settings.MEDIA_ROOT, 'output', request.user.username)
        os.makedirs(output_dir, exist_ok=True)
        
        # Write conversation to file
        from datetime import datetime
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'user_id': request.user.username,
                'transaction_type': transaction_type,
                'conversation': history
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported conversation to {filepath}")
        return filepath
    
    except Exception as e:
        logger.error(f"Error exporting conversation: {str(e)}")
        return None
