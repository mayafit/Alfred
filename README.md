# AI-Powered DevOps Automation Service

An automated DevOps service that leverages AI agents to streamline Jira ticket processing, continuous integration, and deployment workflows.

## Overview

This service automates DevOps tasks by:
1. Monitoring Jira tickets assigned to the DevOps team
2. Processing ticket descriptions using AI to extract actionable tasks
3. Routing tasks to specialized AI agents (CI, Helm, Deploy) for execution
4. Updating Jira tickets with execution results

## Prerequisites

- Python 3.11+
- Jira account with API access
- AI service endpoint
- Docker and Docker Compose (for containerized deployment)

## Environment Variables

Create a `.env` file with the following variables:

```env
# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# AI Service Configuration
AI_SERVICE_URL=http://ai-service-url
AI_SERVICE_TOKEN=your-ai-service-token

# Agent Configuration
CI_AGENT_URL=http://ci-agent-url
HELM_AGENT_URL=http://helm-agent-url
DEPLOY_AGENT_URL=http://deploy-agent-url

# Flask Configuration
SECRET_KEY=your-secret-key
DEBUG=False
```

## Installation

### Local Development

1. Install dependencies:
```bash
pip install flask flask-sqlalchemy gunicorn jira requests
```

2. Run the application:
```bash
python main.py
```

### Docker Deployment

1. Build and run using Docker Compose:
```bash
docker-compose up -d
```

## API Endpoints

### Health Check
- **GET** `/health`
- Returns service health status

### Jira Webhook
- **POST** `/webhook/jira`
- Receives Jira webhook events
- Processes tickets with team field set to "DevOps"

## Jira Integration Setup

1. Create a Jira webhook:
   - Go to Jira Settings > System > WebHooks
   - Add webhook pointing to `http://your-service/webhook/jira`
   - Select "Issue" events

2. Configure custom field requirements:
   - Ensure "team" field exists
   - Set "DevOps" as a valid team value

## Task Description Format

The AI service expects ticket descriptions to follow specific formatting rules for successful parsing. The description should:

1. Clearly state the DevOps objective
2. List specific tasks to be performed
3. Include any relevant configuration details

Example:
```
Deploy new microservice to production

Tasks:
1. Build Docker image from main branch
2. Run security scan
3. Deploy to staging using Helm chart
4. Run integration tests
5. Deploy to production if tests pass
```

## Error Handling

The service provides detailed feedback through Jira comments when:
- Description format is invalid
- AI parsing fails
- Task execution encounters errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details
