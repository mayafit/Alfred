# AI-Powered DevOps Automation Service

An automated DevOps service that leverages AI agents to streamline Jira ticket processing, continuous integration, and deployment workflows.

## Overview

This service automates DevOps tasks by:
1. Processing task descriptions using AI to extract actionable tasks
2. Routing tasks to specialized AI agents (CI, Helm, Deploy) for execution
3. Providing feedback on task execution results

## Prerequisites

- Docker and Docker Compose (for deployment)
- Llama server running (default: http://localhost:11434)
- Jira account with API access (optional)

## Environment Variables

Create a `.env` file with the following variables:

```env
# Jira Configuration (Optional)
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# Llama Server Configuration
LLAMA_SERVER_URL=http://localhost:11434

# Agent Configuration
CI_AGENT_URL=http://ci-agent-url
HELM_AGENT_URL=http://helm-agent-url
DEPLOY_AGENT_URL=http://deploy-agent-url

# Flask Configuration
SECRET_KEY=your-secret-key
DEBUG=False
```

## Testing the Service

You can test the AI task analysis without Jira integration using the `/test/analyze` endpoint:

```bash
# Example: Testing CI pipeline task
curl -X POST http://localhost:5000/test/analyze \
-H "Content-Type: application/json" \
-d '{
  "description": "Build CI pipeline for user-service repository\n\nTasks:\n1. Set up CI pipeline for git@github.com:org/user-service.git\n2. Configure build steps: test, lint, build\n3. Use main branch as default"
}'

# Example: Testing Helm deployment task
curl -X POST http://localhost:5000/test/analyze \
-H "Content-Type: application/json" \
-d '{
  "description": "Create Helm chart for payment service\n\nTasks:\n1. Create Helm chart for git@github.com:org/payment-service.git\n2. Configure service ports and environment variables\n3. Set up ingress rules"
}'

# Example: Testing cluster deployment task
curl -X POST http://localhost:5000/test/analyze \
-H "Content-Type: application/json" \
-d '{
  "description": "Deploy authentication service to production\n\nTasks:\n1. Deploy from git@github.com:org/auth-service.git\n2. Use production namespace\n3. Configure horizontal pod autoscaling"
}'
```

The service will analyze the description and return a structured JSON response with the parsed tasks.

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

System errors are logged for administrator review while user-friendly messages are posted to Jira.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details