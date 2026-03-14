# Testing and Deployment Guide for AI Agent

This document provides comprehensive testing procedures and deployment guidelines for the new LangChain AI agent system.

## 1. Pre-Deployment Checklist

Before deploying the new AI agent system, ensure the following:

- [ ] All dependencies installed from `requirements_updated.txt`
- [ ] Django settings updated with AI agent configuration
- [ ] Database migrations completed
- [ ] Static files collected
- [ ] Logging configured properly
- [ ] ChromaDB directory created and permissions set
- [ ] Hugging Face models pre-downloaded (optional but recommended)
- [ ] Environment variables configured
- [ ] Tests passing (unit and integration)
- [ ] Code reviewed and approved

## 2. Local Testing

### 2.1 Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_updated.txt

# Create necessary directories
mkdir -p media/chromadb
mkdir -p logs
```

### 2.2 Unit Tests

Create and run unit tests for the AI agent:

```bash
# Run all tests
python manage.py test menu.tests

# Run specific test class
python manage.py test menu.tests.test_ai_agent.TransactionAIAgentTestCase

# Run with verbose output
python manage.py test menu.tests -v 2

# Run with coverage
pip install coverage
coverage run --source='menu' manage.py test menu.tests
coverage report
coverage html  # Generate HTML report
```

### 2.3 Integration Tests

Test the integration between Django views and AI agent:

```bash
# Create test user
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user('testuser', 'test@example.com', 'password123')

# Run integration tests
python manage.py test menu.tests.test_integration -v 2
```

### 2.4 Manual Testing

Test the chatbot manually:

```bash
# Start development server
python manage.py runserver

# Access the application
# 1. Navigate to http://localhost:8000
# 2. Login with test user
# 3. Go to transfer/recharge page
# 4. Complete biometric verification
# 5. Test chatbot interactions
```

### 2.5 Test Scenarios

#### Scenario 1: Transfer Transaction

1. User initiates transfer
2. Completes biometric verification
3. Chatbot asks for recipient name
4. User provides: "Ahmed Ben Ali"
5. Chatbot asks for address
6. User provides: "Tunis, Ben Arous"
7. Chatbot asks for phone number
8. User provides: "+216 98 123 456"
9. Chatbot asks for amount
10. User provides: "100 dinars"
11. Chatbot confirms all details
12. User confirms: "Yes, I confirm"
13. Transaction JSON generated
14. User receives confirmation

#### Scenario 2: Recharge Transaction

1. User initiates recharge
2. Completes biometric verification
3. Chatbot asks for phone number
4. User provides: "+216 50 123 456"
5. Chatbot asks for operator
6. User provides: "Orange Tunisie"
7. Chatbot asks for amount
8. User provides: "20 dinars"
9. Chatbot confirms all details
10. User confirms: "Confirmed"
11. Transaction JSON generated
12. User receives confirmation

#### Scenario 3: Error Handling

1. User provides invalid address (not in Tunisia/Morocco)
2. Chatbot rejects and asks for correction
3. User provides valid address
4. Transaction continues normally

#### Scenario 4: Correction Flow

1. User provides incorrect amount
2. Chatbot repeats details for confirmation
3. User says: "No, the amount is wrong"
4. Chatbot asks for correction
5. User provides correct amount
6. Transaction continues

## 3. Performance Testing

### 3.1 Load Testing

Use Apache Bench or similar tools:

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test chatbot endpoint
ab -n 100 -c 10 -p data.json -T application/json http://localhost:8000/menu/chatbot/
```

### 3.2 Response Time Monitoring

Monitor response times:

```python
# In settings.py
MIDDLEWARE = [
    # ... existing middleware ...
    'menu.middleware.ResponseTimeMiddleware',  # Add custom middleware
]

# Create menu/middleware.py
import time
import logging

logger = logging.getLogger(__name__)

class ResponseTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        if 'chatbot' in request.path:
            logger.info(f"Chatbot response time: {duration:.2f}s")
        
        return response
```

### 3.3 Memory Usage Monitoring

Monitor memory consumption:

```python
import psutil
import logging

logger = logging.getLogger(__name__)

def log_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
```

## 4. Staging Deployment

### 4.1 Staging Environment Setup

```bash
# Clone repository to staging server
git clone <repository-url> /var/www/my-easy-transfer-staging

# Install dependencies
cd /var/www/my-easy-transfer-staging
pip install -r requirements_updated.txt

# Configure Django settings for staging
export DJANGO_SETTINGS_MODULE=my_easy_transfer.settings_staging

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser for testing
python manage.py createsuperuser
```

### 4.2 Staging Testing

1. Run full test suite
2. Test with real-like data volume
3. Monitor system resources
4. Test backup and recovery procedures
5. Verify logging and monitoring

### 4.3 Staging Validation

```bash
# Check Django health
python manage.py check

# Verify database connectivity
python manage.py dbshell

# Test email configuration (if applicable)
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])

# Verify ChromaDB
python manage.py shell
>>> from menu.ai_agent import TransactionAIAgent
>>> agent = TransactionAIAgent('transfer', 'test_user')
>>> print("Agent initialized successfully")
```

## 5. Production Deployment

### 5.1 Production Environment Setup

```bash
# Clone repository to production server
git clone <repository-url> /var/www/my-easy-transfer

# Install dependencies
cd /var/www/my-easy-transfer
pip install -r requirements_updated.txt

# Configure Django settings for production
export DJANGO_SETTINGS_MODULE=my_easy_transfer.settings_production

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create necessary directories
mkdir -p media/chromadb
mkdir -p logs
chmod -R 755 media/chromadb
chmod -R 755 logs
```

### 5.2 Web Server Configuration

#### Using Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Create systemd service file
sudo nano /etc/systemd/system/my-easy-transfer.service

[Unit]
Description=My Easy Transfer Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/my-easy-transfer
ExecStart=/var/www/my-easy-transfer/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    my_easy_transfer.wsgi:application

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl enable my-easy-transfer
sudo systemctl start my-easy-transfer
```

#### Using Nginx

```bash
# Install Nginx
sudo apt-get install nginx

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/my-easy-transfer

upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /var/www/my-easy-transfer/static/;
    }
    
    location /media/ {
        alias /var/www/my-easy-transfer/media/;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/my-easy-transfer /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### 5.3 SSL/TLS Configuration

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot certonly --nginx -d your-domain.com

# Update Nginx configuration for HTTPS
sudo nano /etc/nginx/sites-available/my-easy-transfer

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # ... rest of configuration ...
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 5.4 Database Backup

```bash
# Create backup script
sudo nano /usr/local/bin/backup-my-easy-transfer.sh

#!/bin/bash
BACKUP_DIR="/backups/my-easy-transfer"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
python /var/www/my-easy-transfer/manage.py dumpdata > $BACKUP_DIR/db_$DATE.json

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/www/my-easy-transfer/media/

# Backup ChromaDB
tar -czf $BACKUP_DIR/chromadb_$DATE.tar.gz /var/www/my-easy-transfer/media/chromadb/

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

# Make script executable
chmod +x /usr/local/bin/backup-my-easy-transfer.sh

# Add to crontab for daily backups
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-my-easy-transfer.sh
```

## 6. Monitoring and Maintenance

### 6.1 Application Monitoring

```bash
# Install monitoring tools
pip install django-health-check
pip install sentry-sdk

# Configure Sentry for error tracking
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)
```

### 6.2 Log Monitoring

```bash
# Install log aggregation tool
sudo apt-get install logrotate

# Configure log rotation
sudo nano /etc/logrotate.d/my-easy-transfer

/var/www/my-easy-transfer/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload my-easy-transfer > /dev/null 2>&1 || true
    endscript
}
```

### 6.3 Health Checks

```python
# Create health check endpoint
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring."""
    import os
    import json
    from django.db import connection
    
    try:
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check ChromaDB
        chromadb_dir = os.path.join(settings.MEDIA_ROOT, 'chromadb')
        chromadb_ok = os.path.exists(chromadb_dir)
        
        # Check media directory
        media_ok = os.path.exists(settings.MEDIA_ROOT)
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'ok',
            'chromadb': 'ok' if chromadb_ok else 'error',
            'media': 'ok' if media_ok else 'error'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
```

## 7. Rollback Procedure

If issues occur after deployment:

```bash
# Stop application
sudo systemctl stop my-easy-transfer

# Restore from backup
cd /var/www/my-easy-transfer
git checkout <previous-commit-hash>

# Restore database
python manage.py loaddata /backups/my-easy-transfer/db_<date>.json

# Restore media files
tar -xzf /backups/my-easy-transfer/media_<date>.tar.gz -C /

# Restart application
sudo systemctl start my-easy-transfer

# Verify
curl http://localhost:8000/health/
```

## 8. Post-Deployment Validation

After deployment, verify:

1. Application starts without errors
2. All pages load correctly
3. Chatbot responds to user input
4. Transactions complete successfully
5. JSON files are generated
6. Logs are being written
7. Database is accessible
8. ChromaDB is functioning
9. Email notifications work (if applicable)
10. SSL certificate is valid

---

**Author**: Manus AI
**Date**: March 14, 2026
