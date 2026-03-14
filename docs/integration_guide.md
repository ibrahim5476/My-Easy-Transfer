# Integration Guide: Replacing Chatbot with AI Agent

This guide explains how to integrate the new LangChain AI agent into the existing Django application, replacing the Groq-based chatbot and `transaction_processor.py`.

## 1. Installation

First, install the required dependencies:

```bash
pip install langchain langchain-community langchain-huggingface chromadb sentence-transformers
```

Update your `requirements.txt`:

```
langchain>=0.1.0
langchain-community>=0.0.1
langchain-huggingface>=0.0.1
chromadb>=0.3.21
sentence-transformers>=2.2.2
```

## 2. Module Structure

The new system consists of three main modules:

| Module | Purpose |
|--------|---------|
| `ai_agent.py` | Core AI agent implementation with LangChain, Hugging Face, and ChromaDB |
| `transaction_processor_v2.py` | Integration layer providing high-level functions for Django views |
| `views.py` | Updated Django views that use the new agent (modifications needed) |

## 3. Updating Django Views

### 3.1 Replace Chatbot View

Replace the existing `chatbot_view` in `menu/views.py` with:

```python
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .transaction_processor_v2 import (
    process_user_message,
    get_transaction_data,
    generate_transaction_json,
    get_conversation_history
)

@login_required
def chatbot_view(request):
    """Handle chatbot interactions using the new AI agent."""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            user_message = data.get('message', '')
            transaction_type = request.session.get('transaction_type', 'transfer')
            
            # Process message through AI agent
            response, transaction_data, is_confirmed = process_user_message(
                request,
                user_message,
                transaction_type
            )
            
            # If confirmed, generate JSON
            json_path = None
            if is_confirmed and transaction_data.get('completed'):
                json_path = generate_transaction_json(request, transaction_type)
            
            return JsonResponse({
                'success': True,
                'response': response,
                'transaction_data': transaction_data,
                'is_confirmed': is_confirmed,
                'json_path': json_path
            })
        
        except Exception as e:
            logger.error(f"Error in chatbot_view: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # GET request - return chat interface
    transaction_type = request.session.get('transaction_type', 'transfer')
    conversation_history = get_conversation_history(request, transaction_type)
    transaction_data = get_transaction_data(request, transaction_type)
    
    context = {
        'transaction_type': transaction_type,
        'conversation_history': conversation_history,
        'transaction_data': transaction_data
    }
    return render(request, 'menu/chatbot.html', context)
```

### 3.2 Update Verification View

After biometric verification, initialize the AI agent:

```python
@login_required
def verify_identity(request):
    """Verify identity and initialize AI agent for transaction."""
    # ... existing verification code ...
    
    if verification_successful:
        # Initialize AI agent for the transaction
        transaction_type = request.session.get('transaction_type', 'transfer')
        from .transaction_processor_v2 import get_or_create_agent
        agent = get_or_create_agent(request, transaction_type)
        
        # Store verified user info in session
        request.session['verified_user'] = {
            'name': user_data.get('NOM', '') + ' ' + user_data.get('PRENOM', ''),
            'cin': user_data.get('CIN', ''),
            'passport': user_data.get('NUM_PASSPORT', '')
        }
        request.session.modified = True
        
        # Redirect to chatbot
        return redirect('menu:chatbot')
```

### 3.3 Update Transfer/Recharge Handlers

Ensure transaction type is properly set:

```python
@login_required
def handle_transfer(request):
    """Handle transfer transaction initialization."""
    # ... existing code ...
    
    if request.method == 'POST':
        # ... file upload handling ...
        
        request.session['transaction_type'] = 'transfer'
        request.session.modified = True
        
        # Initialize AI agent
        from .transaction_processor_v2 import get_or_create_agent
        agent = get_or_create_agent(request, 'transfer')
        
        return redirect('menu:verify_identity')
    
    return render(request, 'menu/transfer.html')

@login_required
def handle_recharge(request):
    """Handle recharge transaction initialization."""
    # ... existing code ...
    
    if request.method == 'POST':
        # ... file upload handling ...
        
        request.session['transaction_type'] = 'recharge'
        request.session.modified = True
        
        # Initialize AI agent
        from .transaction_processor_v2 import get_or_create_agent
        agent = get_or_create_agent(request, 'recharge')
        
        return redirect('menu:verify_identity')
    
    return render(request, 'menu/recharge.html')
```

## 4. Frontend Integration

### 4.1 Update Chatbot HTML Template

Update `menu/templates/menu/chatbot.html` to send messages to the new endpoint:

```html
<div id="chatbot-container">
    <div id="chat-history"></div>
    <input type="text" id="user-input" placeholder="Type your message...">
    <button id="send-btn">Send</button>
</div>

<script>
document.getElementById('send-btn').addEventListener('click', async function() {
    const userMessage = document.getElementById('user-input').value;
    
    const response = await fetch('/menu/chatbot/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ message: userMessage })
    });
    
    const data = await response.json();
    
    if (data.success) {
        // Display agent response
        displayMessage('bot', data.response);
        
        // Update transaction data
        updateTransactionDisplay(data.transaction_data);
        
        // If confirmed, show completion message
        if (data.is_confirmed && data.json_path) {
            displayMessage('bot', 'Transaction confirmed and saved!');
        }
    } else {
        displayMessage('bot', 'Error: ' + data.error);
    }
    
    document.getElementById('user-input').value = '';
});

function displayMessage(sender, message) {
    const chatHistory = document.getElementById('chat-history');
    const messageEl = document.createElement('div');
    messageEl.className = 'message ' + sender;
    messageEl.textContent = message;
    chatHistory.appendChild(messageEl);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function updateTransactionDisplay(data) {
    // Update UI with current transaction data
    console.log('Transaction data:', data);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
</script>
```

## 5. Configuration

### 5.1 Django Settings

Add to `my_easy_transfer/settings.py`:

```python
# AI Agent Configuration
AI_AGENT_CONFIG = {
    'embeddings_model': 'sentence-transformers/all-MiniLM-L6-v2',
    'llm_model': 'gpt2',  # Can be replaced with a more capable model
    'chromadb_persist_dir': os.path.join(MEDIA_ROOT, 'chromadb'),
    'max_conversation_history': 50,
    'agent_timeout_seconds': 3600
}

# Hugging Face Configuration
HUGGINGFACE_DEVICE = 'cpu'  # Use 'cuda' if GPU is available
```

### 5.2 Logging Configuration

Add logging for the AI agent:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'ai_agent.log'),
        },
    },
    'loggers': {
        'menu.ai_agent': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'menu.transaction_processor_v2': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 6. Testing

### 6.1 Unit Tests

Create `menu/tests/test_ai_agent.py`:

```python
from django.test import TestCase
from menu.ai_agent import TransactionAIAgent

class TransactionAIAgentTestCase(TestCase):
    def setUp(self):
        self.agent_transfer = TransactionAIAgent('transfer', 'test_user_1')
        self.agent_recharge = TransactionAIAgent('recharge', 'test_user_2')
    
    def test_extract_transfer_details(self):
        """Test extraction of transfer details."""
        user_input = "I want to send 100 dinars to Ahmed Ben Ali in Tunis"
        extracted = self.agent_transfer._extract_details_from_input(user_input)
        
        self.assertIn('recipient_name', extracted)
        self.assertIn('amount', extracted)
        self.assertIn('address', extracted)
    
    def test_validate_address(self):
        """Test address validation."""
        result = self.agent_transfer._validate_address("Tunis")
        self.assertIn("validated", result.lower())
    
    def test_detect_confirmation(self):
        """Test confirmation detection."""
        self.assertTrue(self.agent_transfer._detect_confirmation("Yes, I confirm"))
        self.assertFalse(self.agent_transfer._detect_confirmation("No, that's wrong"))
```

### 6.2 Integration Tests

Create `menu/tests/test_integration.py`:

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User

class ChatbotIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_chatbot_message_processing(self):
        """Test chatbot message processing."""
        self.client.login(username='testuser', password='password')
        
        response = self.client.post('/menu/chatbot/', {
            'message': 'I want to send 100 dinars'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('response', data)
```

## 7. Migration from Old System

### 7.1 Backup Old Data

Before deploying, backup existing transaction data:

```bash
cp -r media/output media/output.backup
```

### 7.2 Gradual Rollout

1. Deploy new code with both old and new systems running in parallel
2. Route new transactions to the AI agent
3. Keep old system available for fallback
4. Monitor performance and user feedback
5. Gradually increase traffic to new system
6. Deprecate old system once stable

## 8. Troubleshooting

### Issue: ChromaDB Connection Error

**Solution**: Ensure the `chromadb` directory has proper permissions:

```bash
chmod -R 755 media/chromadb
```

### Issue: Hugging Face Model Download Fails

**Solution**: Pre-download models or configure offline mode:

```python
from transformers import AutoTokenizer, AutoModel

# Pre-download models
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
```

### Issue: Agent Timeout

**Solution**: Increase timeout or optimize prompts:

```python
# In ai_agent.py
executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    memory=memory,
    verbose=True,
    max_iterations=10,
    early_stopping_method="generate",
    timeout=300  # Increase timeout in seconds
)
```

## 9. Performance Optimization

### 9.1 Caching

Implement caching for embeddings:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(text):
    return embeddings.embed_query(text)
```

### 9.2 Batch Processing

Process multiple messages in batch:

```python
def process_batch_messages(request, messages, transaction_type='transfer'):
    """Process multiple messages efficiently."""
    agent = get_or_create_agent(request, transaction_type)
    results = []
    
    for message in messages:
        response, data, confirmed = agent.process_user_input(message)
        results.append({
            'response': response,
            'data': data,
            'confirmed': confirmed
        })
    
    return results
```

## 10. Monitoring and Logging

### 10.1 Enable Detailed Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_agent.log'),
        logging.StreamHandler()
    ]
)
```

### 10.2 Metrics Collection

Track agent performance:

```python
def log_transaction_metrics(agent, transaction_type):
    """Log transaction metrics for monitoring."""
    history = agent.get_conversation_history()
    data = agent.get_transaction_data()
    
    metrics = {
        'conversation_turns': len(history),
        'transaction_type': transaction_type,
        'confirmed': data.get('confirmed', False),
        'completed': data.get('completed', False)
    }
    
    logger.info(f"Transaction metrics: {metrics}")
    return metrics
```

---

**Author**: Manus AI
**Date**: March 14, 2026
