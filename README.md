# AI-Powered DevOps Automation Service

An automated DevOps service that leverages AI agents to streamline Jira ticket processing, continuous integration, and deployment workflows.

## Overview

This service automates DevOps tasks by:
1. Processing task descriptions using AI (multiple providers supported) to extract actionable tasks
2. Routing tasks to specialized AI agents (CI, Helm, Deploy) for execution
3. Providing feedback on task execution results

### Specialized AI Agents
- **CI Agent**: Analyzes repositories and creates appropriate CI/CD pipelines
- **Helm Agent**: Uses SmolHelmAgent with OpenAI to analyze repositories and generate Helm charts
- **Deploy Agent**: Handles Kubernetes deployments with intelligent command generation

### Supported AI Providers
- OpenAI (GPT-4o) - Default provider for high-quality task analysis
- Google Gemini - Alternative provider with strong performance
- Custom LLM deployments - Support for self-hosted or alternative models

## Prerequisites

- Docker and Docker Compose (for deployment)
- AI Provider credentials:
  - OpenAI API key (default), or
  - Google Gemini API key, or
  - Other LLM API endpoint access
- Jira account with API access (optional for webhook integration)

## Environment Variables

Create a `.env` file with the following variables:

```env
# Jira Configuration (Optional)
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# LLM Provider Selection
# Options: "openai", "gemini", "other"
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.2
OPENAI_MAX_TOKENS=1000

# Google Gemini Configuration
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-pro
GEMINI_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent
GEMINI_TEMPERATURE=0.2
GEMINI_MAX_TOKENS=1000

# Other LLM Configuration (e.g., local Llama)
OTHER_LLM_URL=http://localhost:11434/api/generate
OTHER_LLM_API_KEY=your-other-llm-api-key
OTHER_LLM_TEMPERATURE=0.2
OTHER_LLM_MAX_TOKENS=1000

# Legacy AI Service Configuration (for backward compatibility)
LLAMA_SERVER_URL=http://localhost:11434
AI_SERVICE_URL=http://your-ai-service-url
AI_SERVICE_TOKEN=your-ai-service-token

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

## Testing CI Pipeline Creation

You can test the CI pipeline creation functionality using the `/test/ci` endpoint. Here are examples for different project types:

### C# Library
```bash
curl -X POST http://localhost:5000/test/ci \
-H "Content-Type: application/json" \
-d '{
  "repository": "git@github.com:example/csharp-lib.git",
  "branch": "main",
  "build_steps": ["restore", "build", "test", "pack"]
}'
```

### ASP.NET Core Service
```bash
curl -X POST http://localhost:5000/test/ci \
-H "Content-Type: application/json" \
-d '{
  "repository": "git@github.com:example/aspnet-service.git",
  "branch": "main",
  "build_steps": ["restore", "build", "test", "publish", "docker-build"]
}'
```

### Node.js Service
```bash
curl -X POST http://localhost:5000/test/ci \
-H "Content-Type: application/json" \
-d '{
  "repository": "git@github.com:example/node-service.git",
  "branch": "main",
  "build_steps": ["install", "lint", "test", "build", "docker-build"]
}'
```

### Website
```bash
curl -X POST http://localhost:5000/test/ci \
-H "Content-Type: application/json" \
-d '{
  "repository": "git@github.com:example/website.git",
  "branch": "main",
  "build_steps": ["install", "lint", "test", "build", "deploy"]
}'
```

The service will:
1. Clone the repository
2. Analyze the project type using AI
3. Generate an appropriate Jenkins pipeline
4. Return detailed analysis results

Response includes:
- Project type detection with confidence score
- Generated pipeline configuration
- Build step details
- Execution status


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

## Testing the System

### Running in Test Mode

1. Start all services using the test runner:
```bash
python run_services.py
```

This will start:
- Main application on port 5000
- CI Agent on port 9001
- Helm Agent on port 9002
- Deploy Agent on port 9003

### Using Simulation Mode

The system includes a simulation mode for testing and demonstration purposes without requiring actual Jira integration or external repositories.

#### Enabling Simulation Mode

1. Set the following environment variables in your `.env` file:
```env
# Simulation Mode Configuration
SIMULATION_MODE=True
SIMULATION_INTERVAL=30          # Seconds between simulation cycles
SIMULATION_EVENT_COUNT=3        # Number of events per cycle
SIMULATION_JIRA_EVENTS=True     # Enable Jira webhook simulation
SIMULATION_JIRA_INTERVAL=60     # Seconds between Jira webhook events

# Docker Image Versions
ALFRED_DEVOPS_IMAGE_VERSION=latest
ALFRED_CI_AGENT_IMAGE_VERSION=latest
ALFRED_HELM_AGENT_IMAGE_VERSION=latest
ALFRED_DEPLOY_AGENT_IMAGE_VERSION=latest
```

2. Or enable via the dashboard controls:
   - Navigate to `http://localhost:5000/dashboard`
   - In the "Simulation Controls" section, toggle "Enable Simulation"
   - Configure simulation parameters as needed
   - Click "Apply Configuration"

#### Simulation Features

Simulation mode provides:
- Automated generation of system events (task received, AI analysis, agent triggered)
- Simulated task history records
- Simulated system metrics
- Realistic Jira webhook payloads with detailed task descriptions

#### Manual Simulation Triggers

You can manually trigger simulation events through the dashboard or API:

**Dashboard Controls:**
- Click "Trigger System Event" to generate a full workflow cycle
- Click "Trigger Jira Webhook" to send a simulated Jira webhook event

**API Endpoints:**
```bash
# Trigger system events
curl -X POST http://localhost:5000/api/simulation/trigger

# Trigger a simulated Jira webhook
curl -X POST http://localhost:5000/api/simulation/trigger/jira

# Get simulation status
curl http://localhost:5000/api/simulation/status

# Configure simulation
curl -X POST http://localhost:5000/api/simulation/config \
-H "Content-Type: application/json" \
-d '{
  "interval": 30,
  "event_count": 3,
  "jira_events_enabled": true,
  "jira_interval": 60
}'

# Toggle simulation mode
curl -X POST http://localhost:5000/api/simulation/toggle \
-H "Content-Type: application/json" \
-d '{"enabled": true}'
```

### Testing with Postman

#### Testing CI Agent
Send a POST request to `http://0.0.0.0:9001/execute` with payload:
```json
{
  "repository": {
    "url": "git@github.com:org/test-service.git",
    "branch": "main"
  }
}
```

#### Testing Helm Agent
Send a POST request to `http://0.0.0.0:9002/execute` with payload:
```json
{
  "parameters": {
    "repository": "git@github.com:org/service.git",
    "app_name": "my-service",
    "namespace": "production",
    "branch": "main"
  }
}
```

The SmolHelmAgent will:
1. Clone the repository
2. Analyze the repository content (Dockerfiles, docker-compose.yml, language-specific files)
3. Extract information like port mappings, environment variables, volumes, dependencies
4. Generate appropriate Helm chart files using OpenAI GPT-4o
5. Return the analysis results and generated Helm chart

#### Testing Deploy Agent
Send a POST request to `http://0.0.0.0:9003/execute` with payload:
```json
{
  "parameters": {
    "repository": "git@github.com:org/service.git",
    "namespace": "production"
  }
}
```

### Using the Test Script

For CI agent testing, use the provided test script:
```bash
python test_ci_agent.py --repo git@github.com:org/test-service.git --branch main
```

Additional test script options:
- `--url`: Specify agent URL (default: http://0.0.0.0:9001)
- `--health`: Run health check only
- `--branch`: Specify git branch (default: main)

### Health Checks

Each agent provides a health endpoint at `/health`. Example:
```bash
curl http://0.0.0.0:9001/health  # CI Agent
curl http://0.0.0.0:9002/health  # Helm Agent
curl http://0.0.0.0:9003/health  # Deploy Agent
```

## License

MIT License - see LICENSE file for details