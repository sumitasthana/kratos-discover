# Deployment Guide

Comprehensive guide for deploying Kratos-Discover in various environments.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Cloud Deployment](#cloud-deployment)
- [CI/CD Integration](#cicd-integration)
- [Security Best Practices](#security-best-practices)

## Deployment Overview

Kratos-Discover is primarily a CLI application designed for document processing. This guide covers various deployment scenarios.

### Deployment Options

1. **Local Development**: Direct Python execution
2. **Docker**: Containerized deployment
3. **Production Server**: Systemd service or cron jobs
4. **Cloud Platforms**: AWS, GCP, Azure
5. **CI/CD Pipeline**: Automated processing

## Docker Deployment

### Using the Provided Dockerfile

Kratos-Discover includes a Dockerfile for containerized deployment.

#### Build Docker Image

```bash
# Build the image
docker build -t kratos-discover:latest .

# Verify the image
docker images | grep kratos-discover
```

#### Run Container

**Basic Run**:
```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/outputs:/app/outputs \
  kratos-discover:latest \
  --provider openai --input data/document.docx
```

**Interactive Mode**:
```bash
docker run -it --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/outputs:/app/outputs \
  kratos-discover:latest \
  bash
```

#### Using Docker Compose

**Start Services**:
```bash
docker-compose up
```

**Run Extraction**:
```bash
docker-compose run kratos-discover \
  --provider openai --input data/document.docx
```

**Stop Services**:
```bash
docker-compose down
```

### Docker Environment Variables

Pass environment variables via `.env` file:

```bash
# Create .env for Docker
cat > .env << EOF
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
RULE_AGENT_MODE=rules
RULE_AGENT_OUTPUT_DIR=outputs
RULE_AGENT_LOG_LEVEL=INFO
EOF
```

Or pass directly:
```bash
docker run --rm \
  -e OPENAI_API_KEY=sk-your-key \
  -e OPENAI_MODEL=gpt-4o-mini \
  kratos-discover:latest \
  --provider openai --input data/document.docx
```

### Volume Mounting

Mount directories for data persistence:

```bash
docker run --rm \
  -v /host/data:/app/data \        # Input documents
  -v /host/outputs:/app/outputs \   # Output results
  -v /host/config:/app/config \     # Configuration files
  kratos-discover:latest
```

## Production Deployment

### Systemd Service (Linux)

Create a systemd service for automated processing.

**1. Create Service File**:

```bash
sudo nano /etc/systemd/system/kratos-discover.service
```

```ini
[Unit]
Description=Kratos-Discover Document Processing
After=network.target

[Service]
Type=oneshot
User=kratos
Group=kratos
WorkingDirectory=/opt/kratos-discover
Environment="PATH=/opt/kratos-discover/.venv/bin"
EnvironmentFile=/opt/kratos-discover/.env
ExecStart=/opt/kratos-discover/.venv/bin/python cli.py \
  --provider openai \
  --input ${INPUT_PATH} \
  --output-dir ${OUTPUT_DIR}

[Install]
WantedBy=multi-user.target
```

**2. Create Timer for Scheduled Processing**:

```bash
sudo nano /etc/systemd/system/kratos-discover.timer
```

```ini
[Unit]
Description=Kratos-Discover Processing Timer
Requires=kratos-discover.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

**3. Enable and Start**:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer
sudo systemctl enable kratos-discover.timer

# Start timer
sudo systemctl start kratos-discover.timer

# Check status
sudo systemctl status kratos-discover.timer
```

### Cron Job (Alternative)

**Edit crontab**:
```bash
crontab -e
```

**Add cron job**:
```cron
# Run daily at 2 AM
0 2 * * * cd /opt/kratos-discover && .venv/bin/python cli.py --provider openai --input data/document.docx >> /var/log/kratos-discover.log 2>&1

# Run every hour
0 * * * * cd /opt/kratos-discover && .venv/bin/python cli.py --provider openai --input data/document.docx

# Process all documents in directory
0 3 * * * cd /opt/kratos-discover && for f in data/*.docx; do .venv/bin/python cli.py --input "$f" --output-dir outputs/; done
```

### Process Monitoring

**Using Supervisor**:

```bash
# Install supervisor
sudo apt-get install supervisor

# Create config
sudo nano /etc/supervisor/conf.d/kratos-discover.conf
```

```ini
[program:kratos-discover]
command=/opt/kratos-discover/.venv/bin/python cli.py --provider openai --input data/document.docx
directory=/opt/kratos-discover
user=kratos
autostart=true
autorestart=true
stderr_logfile=/var/log/kratos-discover.err.log
stdout_logfile=/var/log/kratos-discover.out.log
```

**Start with supervisor**:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start kratos-discover
```

## Cloud Deployment

### AWS Deployment

#### AWS Lambda

**1. Create Lambda Function**:

```python
# lambda_function.py
import os
import json
from rule_agent import RuleAgent
from prompt_registry import PromptRegistry
from langchain_openai import ChatOpenAI
from pathlib import Path

def lambda_handler(event, context):
    """AWS Lambda handler for document processing"""
    
    # Get S3 bucket and key from event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Download document from S3
    s3 = boto3.client('s3')
    local_path = f'/tmp/{key}'
    s3.download_file(bucket, key, local_path)
    
    # Initialize agent
    registry = PromptRegistry(base_dir=Path('.'))
    llm = ChatOpenAI(
        model=os.getenv('OPENAI_MODEL'),
        api_key=os.getenv('OPENAI_API_KEY')
    )
    agent = RuleAgent(registry=registry, llm=llm)
    
    # Extract rules
    rules = agent.extract_rules(local_path)
    
    # Upload results to S3
    output_key = key.replace('.docx', '_results.json')
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps([r.model_dump() for r in rules])
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Processed {len(rules)} rules')
    }
```

**2. Package and Deploy**:

```bash
# Create deployment package
pip install -t package -r requirements.txt
cd package
zip -r ../deployment.zip .
cd ..
zip -g deployment.zip lambda_function.py rule_agent.py prompt_registry.py

# Upload to Lambda
aws lambda create-function \
  --function-name kratos-discover \
  --runtime python3.9 \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://deployment.zip \
  --environment Variables={OPENAI_API_KEY=sk-your-key}
```

#### AWS Batch

For longer-running jobs:

```yaml
# batch-job-definition.json
{
  "jobDefinitionName": "kratos-discover-job",
  "type": "container",
  "containerProperties": {
    "image": "your-account.dkr.ecr.region.amazonaws.com/kratos-discover:latest",
    "vcpus": 2,
    "memory": 4096,
    "environment": [
      {"name": "OPENAI_API_KEY", "value": "sk-your-key"}
    ]
  }
}
```

### Google Cloud Platform

#### Cloud Run

**1. Build and Push Image**:

```bash
# Build for Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/kratos-discover

# Or use local Docker
docker build -t gcr.io/PROJECT_ID/kratos-discover .
docker push gcr.io/PROJECT_ID/kratos-discover
```

**2. Deploy**:

```bash
gcloud run deploy kratos-discover \
  --image gcr.io/PROJECT_ID/kratos-discover \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=sk-your-key \
  --memory 4Gi \
  --timeout 3600
```

#### Cloud Functions

```python
# main.py for Cloud Functions
def process_document(request):
    """Cloud Function entry point"""
    from rule_agent import RuleAgent
    
    # Process document
    rules = agent.extract_rules(document_path)
    
    return {'rules': len(rules)}, 200
```

### Azure Deployment

#### Azure Container Instances

```bash
az container create \
  --resource-group kratos-rg \
  --name kratos-discover \
  --image your-registry.azurecr.io/kratos-discover:latest \
  --environment-variables \
    OPENAI_API_KEY=sk-your-key \
    OPENAI_MODEL=gpt-4o-mini \
  --cpu 2 \
  --memory 4
```

#### Azure Functions

Similar to AWS Lambda, package and deploy as Azure Function.

## CI/CD Integration

### GitHub Actions

**.github/workflows/process-documents.yml**:

```yaml
name: Process Documents

on:
  push:
    paths:
      - 'data/**'
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  process:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Process documents
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL: gpt-4o-mini
        run: |
          python cli.py --provider openai --input data/document.docx
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: extraction-results
          path: outputs/
```

### GitLab CI

**.gitlab-ci.yml**:

```yaml
stages:
  - process

process_documents:
  stage: process
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - python cli.py --provider openai --input data/document.docx
  artifacts:
    paths:
      - outputs/
    expire_in: 1 week
  only:
    - schedules
  variables:
    OPENAI_API_KEY: $OPENAI_API_KEY
```

### Jenkins

**Jenkinsfile**:

```groovy
pipeline {
    agent {
        docker {
            image 'python:3.9'
        }
    }
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        
        stage('Process') {
            steps {
                sh 'python cli.py --provider openai --input data/document.docx'
            }
        }
        
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: 'outputs/*.json'
            }
        }
    }
}
```

## Security Best Practices

### API Key Management

**1. Use Secret Managers**:

```python
# AWS Secrets Manager
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

secrets = get_secret('kratos-discover/api-keys')
os.environ['OPENAI_API_KEY'] = secrets['openai_key']
```

**2. Environment-Specific Keys**:

```bash
# Development
export OPENAI_API_KEY=sk-dev-key

# Production
export OPENAI_API_KEY=sk-prod-key
```

**3. Rotate Keys Regularly**:
- Rotate API keys every 90 days
- Use different keys for dev/staging/prod
- Monitor key usage for anomalies

### Network Security

**1. Restrict Outbound Traffic**:
- Allow only necessary API endpoints
- Use firewall rules to limit connections

**2. Use VPC/Private Networks**:
```bash
# AWS VPC endpoint for S3
# No internet gateway required
```

**3. Enable SSL/TLS**:
- Always use HTTPS for API calls
- Verify SSL certificates

### Data Security

**1. Encrypt Data at Rest**:

```bash
# Encrypt outputs directory
gpg --encrypt --recipient user@example.com outputs/results.json
```

**2. Encrypt Data in Transit**:
- Use HTTPS/TLS for all API calls
- Verify SSL certificates

**3. Secure File Permissions**:

```bash
# Restrict access to sensitive files
chmod 600 .env
chmod 600 config/*.yaml
chmod 700 data/
```

### Access Control

**1. Use IAM Roles** (AWS):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::kratos-bucket/*"
    }
  ]
}
```

**2. Principle of Least Privilege**:
- Grant minimum necessary permissions
- Use separate service accounts

**3. Audit Logging**:

```python
import logging

# Configure audit logging
logging.basicConfig(
    filename='/var/log/kratos-discover-audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(user)s - %(action)s - %(status)s'
)
```

## Monitoring and Logging

### Application Monitoring

```python
# Add monitoring
from prometheus_client import Counter, Histogram
import time

extraction_counter = Counter('rules_extracted_total', 'Total rules extracted')
extraction_duration = Histogram('extraction_duration_seconds', 'Time spent extracting')

@extraction_duration.time()
def extract_with_monitoring(document_path):
    rules = agent.extract_rules(document_path)
    extraction_counter.inc(len(rules))
    return rules
```

### Log Aggregation

**Using ELK Stack**:

```python
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

## Next Steps

- Review [Configuration](Configuration.md) for environment setup
- Check [Security Best Practices](#security-best-practices)
- Explore [Cloud Deployment](#cloud-deployment) options

---

**Need deployment help?** [Open an issue](https://github.com/sumitasthana/kratos-discover/issues) with your deployment scenario.
